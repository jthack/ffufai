#!/usr/bin/env python3

import argparse
import os
import subprocess
import requests
import json
from openai import OpenAI
import anthropic
from urllib.parse import urlparse
import tempfile
import os
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import re

def extract_json(text: str) -> dict:
    """
    Extracts the first valid JSON object from a string.
    Handles Gemini adding prose or ```json fences.
    """
    if not text:
        raise ValueError("Empty response from model")

    # Remove markdown fences if present
    text = text.strip()
    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text)

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"No valid JSON found in response:\n{text}")

def get_api_key():
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')

    if anthropic_key:
        return ('anthropic', anthropic_key)
    elif openai_key:
        return ('openai', openai_key)
    elif gemini_key:
        return ('gemini', gemini_key)
    else:
        raise ValueError("No API key found. Please set OPENAI_API_KEY/ANTHROPIC_API_KEY/GEMINI_API_KEY.")


def get_response(url):
    try:
        response = requests.get(url, allow_redirects=True)

        soup = BeautifulSoup(response.content, 'html.parser')

        for tag in soup.select('style, link[rel="stylesheet"]'):
            tag.decompose()

        for tag in soup.find_all(True):
            if hasattr(tag, 'attrs') and tag.attrs is not None:
                tag.attrs.pop('style', None)

            if tag.name == 'svg':
                tag.decompose()
            if tag.name == 'img':
                tag.decompose()

        content = soup.prettify()

        return {
            "url": response.url,
            "headers": dict(response.headers),
            "cookies": dict(response.cookies),
            "content": content[:2500]
        }

    except requests.RequestException as e:
        print(f"Error fetching content: {e}")
        return {"error": "Error fetching content."}

def get_headers(url):
    try:
        response = requests.head(url, allow_redirects=True)
        if not response.headers:
            response = requests.get(url, allow_redirects=True)
        return dict(response.headers)
    except requests.RequestException as e:
        print(f"Error fetching headers: {e}")
        return {"Header": "Error fetching headers."}

EXTENSION_SCHEMA = {
    "type": "object",
    "properties": {
        "extensions": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": "^\\.[a-zA-Z0-9]+$"
            },
            "minItems": 1,
            "maxItems": 5
        }
    },
    "required": ["extensions"]
}

def heuristic_extensions(url, headers, max_extensions):
    exts = []

    server = str(headers.get("Server", "")).lower()
    powered = str(headers.get("X-Powered-By", "")).lower()
    ct = str(headers.get("Content-Type", "")).lower()

    if "apache" in server or "nginx" in server:
        exts += [".html", ".php", ".bak"]

    if "iis" in server or "asp.net" in powered:
        exts += [".aspx", ".asp", ".config"]

    if "json" in ct:
        exts += [".json"]

    if "javascript" in ct:
        exts += [".js"]

    if not exts:
        exts = [".html", ".php", ".txt"]

    return exts[:max_extensions]


def get_ai_extensions(url, headers, api_type, api_key, max_extensions):
    prompt = f"""
    Given the following URL and HTTP headers, suggest the most likely file extensions for fuzzing this endpoint.
    Respond with a JSON object containing a list of extensions. The response will be parsed with json.loads(),
    so it must be valid JSON. No preamble or yapping. Use the format: {{"extensions": [".ext1", ".ext2", ...]}}.
    Do not suggest more than {max_extensions}, but only suggest extensions that make sense. For example, if the path is
    /js/ then don't suggest .css as the extension. Also, if limited, prefer the extensions which are more interesting.
    The URL path is great to look at for ideas. For example, if it says presentations, then it's likely there
    are powerpoints or pdfs in there. If the path is /js/ then it's good to use js as an extension.

    Examples:
    1. URL: https://example.com/presentations/FUZZ
       Headers: {{"Content-Type": "application/pdf", "Content-Length": "1234567"}}
       JSON Response: {{"extensions": [".pdf", ".ppt", ".pptx"]}}

    2. URL: https://example.com/FUZZ
       Headers: {{"Server": "Microsoft-IIS/10.0", "X-Powered-By": "ASP.NET"}}
       JSON Response: {{"extensions": [".aspx", ".asp", ".exe", ".dll"]}}

    URL: {url}
    Headers: {headers}

    JSON Response:
    """

    if api_type == 'openai':
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that suggests file extensions for fuzzing based on URL and headers."},
                {"role": "user", "content": prompt}
            ]
        )
        return json.loads(response.choices[0].message.content.strip())
    elif api_type == 'anthropic':
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0,
            system="You are a helpful assistant that suggests file extensions for fuzzing based on URL and headers.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )


        return json.loads(message.content[0].text)

    elif api_type == 'gemini':
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=f"URL: {url}\nHeaders: {headers}",
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=128,
                response_mime_type="application/json",
                response_schema=EXTENSION_SCHEMA
            )
        )

        parsed = response.parsed

        if isinstance(parsed, dict):
            return parsed

        # Gemini failed schema compliance → deterministic fallback
        return {"extensions": heuristic_extensions(url, headers, max_extensions)}



def get_contextual_wordlist(url, headers, api_type, api_key, max_size, cookies=None, content=None):
    prompt = f"""
    Given the following URL and HTTP headers, suggest the most likely contextual wordlist for content discovery on this endpoint.
    Be as extensive as possible, provide the maximum number of directories and files that make sense for the endpoint.
    Try to create a list of size {max_size}.
    Respond with a JSON object containing a list of directories and files. The response will be parsed with json.loads(),
    so it must be valid JSON. No preamble or yapping. Use the format: { {"wordlist": ["dir1", "dir2", "file1", "file2"]} }.
    Only make suggestions that make sense. For example, if domain is for a book shop
    then don't suggest footbal as a directory. Also, if limited, prefer the files and directories which are more interesting.
    The URL path is great to look at for ideas, and so is the brand behind the URL.
    Focus on contents relevant to the identified industry and technology stack. Include technology-specific files.
    For example, if it says presentations, then it's likely there are powerpoints or pdfs in there. If the path is /js/ then it's good to fuzz for JS files.

    Example 1: WordPress Blog
    URL: https://blog.techstartup.io/wp-content/uploads/2024/FUZZ
    Headers: {{
      "Server": "nginx/1.22.1",
      "X-Powered-By": "PHP/8.1.2",
      "Link": "<https://blog.techstartup.io/wp-json/>; rel=\"https://api.w.org/\"",
      "Content-Type": "image/jpeg"
    }}

    Response:
    {{
      "wordlist": ["wp-content", "wp-includes", "wp-admin", "uploads", "themes", "plugins", "2024", "2023", "backup", "cache", "wp-config.php", "xmlrpc.php", "wp-login.php", "readme.html", ".htaccess", "wp-config.php.bak", "debug.log"],
    }}

    Example 2: E-commerce Platform
    URL: https://shop.globalretail.com/checkout/payment/FUZZ
    Headers:
    {{
      "Server": "Microsoft-IIS/10.0",
      "X-Powered-By": "ASP.NET",
      "X-AspNet-Version": "4.0.30319",
      "X-Frame-Options": "SAMEORIGIN",
      "Strict-Transport-Security": "max-age=31536000"
    }}

    Response:
    {{
      "wordlist": ["checkout", "payment", "api", "admin", "account", "orders", "products", "cart", "invoice", "App_Data", "bin", "Content", "web.config", "Global.asax", "payment.aspx", "checkout.aspx", "web.config.bak", "App_Data.mdf", "connectionstrings.config"],
    }}

    URL: {url}
    Headers: {headers}
    Cookies: {cookies}
    Content: {content}

    JSON Response:
    """

    if api_type == 'openai':
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that suggests wordlists for fuzzing based on URL and headers."},
                {"role": "user", "content": prompt}
            ]
        )
        return json.loads(response.choices[0].message.content.strip())

    elif api_type == 'anthropic':
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10000,
            temperature=0,
            system="You are a helpful assistant that suggests wordlists for fuzzing based on URL and headers.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return json.loads(message.content[0].text)

    

def validate_extensions(data, max_extensions):
    if not isinstance(data, dict):
        raise ValueError("AI output is not a JSON object")

    exts = data.get("extensions")
    if not isinstance(exts, list):
        raise ValueError("Missing 'extensions' list")

    clean = []
    for e in exts:
        if isinstance(e, str) and e.startswith("."):
            clean.append(e)

    return clean[:max_extensions]


def main():
    parser = argparse.ArgumentParser(description='ffufai - AI-powered ffuf wrapper')
    parser.add_argument('--ffuf-path', default='ffuf', help='Path to ffuf executable')
    parser.add_argument('--max-extensions', type=int, default=4, help='Maximum number of extensions to suggest')
    parser.add_argument('--wordlists', action='store_true', help='Generate contextual wordlists')
    parser.add_argument('--max-wordlist-size', type=int, help="The maximum size of the generated wordlist")
    parser.add_argument('--include-response', action='store_true', help='Makes a GET request and uses the Response as context for better wordlist generation (Uses More tokens)')
    args, unknown = parser.parse_known_args()

    # Find the -u argument in the unknown args
    try:
        url_index = unknown.index('-u') + 1
        url = unknown[url_index]
    except (ValueError, IndexError):
        print("Error: -u URL argument is required.")
        return

    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    base_url = url.replace('FUZZ', '')

    if 'FUZZ' not in path_parts[-1]:
        print("Warning: FUZZ keyword is not at the end of the URL path. Extension fuzzing may not work as expected.")

    headers = get_headers(base_url)

    api_type, api_key = get_api_key()


    if args.wordlists:
        try:
            if args.max_wordlist_size:
                size = args.max_wordlist_size
            else:
                size = 200

            if args.include_response:
                response = get_response(base_url)
                headers = response['headers']
                cookies = response['cookies']
                content = response['content']
                wordlists_data = get_contextual_wordlist(url, headers, api_type, api_key, size, cookies=cookies, content=content)

            else:
                wordlists_data = get_contextual_wordlist(url, headers, api_type, api_key, size)

            print(wordlists_data)
            wordlist = '\n'.join(wordlists_data['wordlist'])

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing AI response. The Wordlist size may have been too big for your max_tokens. Try again. Error: {e}")
            return

        if wordlist:
            file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            file.write(wordlist)
            file.close()
            ffuf_command = [args.ffuf_path] + unknown + ['-w', file.name]
            subprocess.run(ffuf_command)


    else:
        try:
            extensions_data = get_ai_extensions(url, headers, api_type, api_key, args.max_extensions)
            print(extensions_data)
            extensions = ','.join(
                validate_extensions(extensions_data, args.max_extensions)
            )

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing AI response. Try again. Error: {e}")
            return

        ffuf_command = [args.ffuf_path] + unknown + ['-e', extensions]

        subprocess.run(ffuf_command)


if __name__ == '__main__':
    main()
