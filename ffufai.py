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

def get_api_key():
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_key:
        return ('anthropic', anthropic_key)
    elif openai_key:
        return ('openai', openai_key)
    else:
        raise ValueError("No API key found. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY.")

def get_headers(url):
    try:
        response = requests.head(url, allow_redirects=True)
        return dict(response.headers)
    except requests.RequestException as e:
        print(f"Error fetching headers: {e}")
        return {"Header": "Error fetching headers."}

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
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            temperature=0,
            system="You are a helpful assistant that suggests file extensions for fuzzing based on URL and headers.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return json.loads(message.content[0].text)

def get_contextual_wordlist(url, headers, api_type, api_key):
    prompt = f"""
    Given the following URL and HTTP headers, suggest the most likely contextual wordlist for fuzzing this endpoint.
    Respond with a JSON object containing a list of subdomais, directories and files. The response will be parsed with json.loads(),
    so it must be valid JSON. No preamble or yapping. Use the format: { {"subdomains": ["example1", "example2", ...]}, {"files" : ["file1", "file2"]} }.
    Only suggest subdomains that make sense. For example, if domain is for a book shop
    then don't suggest footbal as a subdomain. Also, if limited, prefer the subdomains which are more interesting.
    The URL path is great to look at for ideas, and so is the brand behind the URL.
    Focus on subdomains relevant to the identified industry and technology stack. Include technology-specific subdomains.
    For example, if it says presentations, then it's likely there
    are powerpoints or pdfs in there. If the path is /js/ then it's good to use js as an extension.

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
      "subdomains": ["dev-blog", "staging-blog", "admin", "api", "cdn", "media", "assets", "wp", "wordpress", "backup"],
      "directories": ["wp-content", "wp-includes", "wp-admin", "uploads", "themes", "plugins", "2024", "2023", "backup", "cache"],
      "files": ["wp-config.php", "xmlrpc.php", "wp-login.php", "readme.html", ".htaccess", "wp-config.php.bak", "debug.log"],
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
      "subdomains": ["admin-shop", "staging-shop", "dev", "test", "api", "payment", "checkout", "secure", "orders", "inventory", "warehouse", "cdn-shop"],
      "directories": ["checkout", "payment", "api", "admin", "account", "orders", "products", "cart", "invoice", "App_Data", "bin", "Content"],
      "files": ["web.config", "Global.asax", "payment.aspx", "checkout.aspx", "web.config.bak", "App_Data.mdf", "connectionstrings.config"],
    }}

    URL: {url}
    Headers: {headers}

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
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            temperature=0,
            system="You are a helpful assistant that suggests wordlists for fuzzing based on URL and headers.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return json.loads(message.content[0].text)

def main():
    parser = argparse.ArgumentParser(description='ffufai - AI-powered ffuf wrapper')
    parser.add_argument('--ffuf-path', default='ffuf', help='Path to ffuf executable')
    parser.add_argument('--max-extensions', type=int, default=4, help='Maximum number of extensions to suggest')
    parser.add_argument('--extensions', action='store_true', help='Generate extensions')
    parser.add_argument('--wordlists', action='store_true', help='Generate contextual wordlists')
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

    if 'FUZZ' not in path_parts[-1]:
        print("Warning: FUZZ keyword is not at the end of the URL path. Extension fuzzing may not work as expected.")

    base_url = url.replace('FUZZ', '')
    headers = get_headers(base_url)

    api_type, api_key = get_api_key()

    if args.extensions:
        try:
            extensions_data = get_ai_extensions(url, headers, api_type, api_key, args.max_extensions)
            print(extensions_data)
            extensions = ','.join(extensions_data['extensions'][:args.max_extensions])

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing AI response. Try again. Error: {e}")
            return

        ffuf_command = [args.ffuf_path] + unknown + ['-e', extensions]

        subprocess.run(ffuf_command)

    if args.wordlists:
        try:
            wordlists_data = get_contextual_wordlist(url, headers, api_type, api_key)
            print(wordlists_data)
            subdomains = '\n'.join(wordlists_data['subdomains'])
            directories = '\n'.join(wordlists_data['directories'])
            files = '\n'.join(wordlists_data['files'])

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing AI response. Try again. Error: {e}")
            return

        if subdomains:
            domain = parsed_url.netloc
            domain_parts = domain.split('.')
            if len(domain_parts) > 2:
                root_domain = '.'.join(domain_parts[-2:])
            else:
                root_domain = domain

            sub_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            sub_file.write(subdomains)
            sub_file.close()

            subdomain_url = f'{parsed_url.scheme}://FUZZ.{root_domain}'
            ffuf_command = [args.ffuf_path] + unknown +  ['-u', subdomain_url, '-w', sub_file.name]
            subprocess.run(ffuf_command)

        if directories:
            dir_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            dir_file.write(directories)
            dir_file.close()
            ffuf_command = [args.ffuf_path] + unknown + ['-w', dir_file.name]
            subprocess.run(ffuf_command)

        if files:
            files_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            files_file.write(files)
            files_file.close()
            ffuf_command = [args.ffuf_path] + unknown + ['-w', files_file.name]
            subprocess.run(ffuf_command)


if __name__ == '__main__':
    main()
