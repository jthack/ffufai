#!/usr/bin/env python3

import argparse
import hashlib
import re
import json
import os
import random
import socket
import ssl
import string
import subprocess
import tempfile
import time
from urllib.parse import urlparse

import anthropic
from bs4 import BeautifulSoup
from openai import OpenAI
import requests

DEFAULT_CACHE_PATH = os.path.expanduser("~/.cache/ffufai/cache.json")
DEFAULT_STATE_PATH = os.path.expanduser("~/.cache/ffufai/state.json")
DEFAULT_FINDINGS_PATH = os.path.expanduser("~/.cache/ffufai/findings.json")
DEFAULT_KB_PATH = os.path.expanduser("~/.cache/ffufai/knowledge.json")
DEFAULT_SIGNATURE_PATH = os.path.join(os.path.dirname(__file__), "config", "tech_signatures.json")
DEFAULT_WORDLIST_CATALOG = os.path.join(os.path.dirname(__file__), "config", "wordlist_catalog.json")

DEFAULT_PROVIDER_ORDER = ["gemini", "openai", "anthropic", "groq", "openrouter"]

PROFILE_GUIDANCE = {
    "balanced": "Balance coverage and precision. Prioritize likely, meaningful files or directories.",
    "critical": "Favor high-impact targets: auth, admin, config, backups, credentials, secrets, logs, exports.",
    "stealth": "Keep list small and low-noise. Prefer high-confidence items only.",
    "depth": "Expand breadth with technology-specific folders and deep paths.",
    "api-only": "Focus on API endpoints, JSON, versioning, auth, schemas, and documentation.",
    "spa": "Focus on static assets, bundles, source maps, and client-side routes.",
    "admin-heavy": "Prioritize admin panels, dashboards, internal tools, and management endpoints.",
    "cloud-native": "Focus on cloud metadata, config, debug, and service-specific endpoints.",
    "legacy": "Hunt legacy endpoints, old versions, deprecations, and archived paths.",
    "mobile-backend": "Focus on mobile API endpoints, versions, and app-specific paths.",
    "partner-portal": "Target partner/vendor portals, B2B integrations, and shared access points.",
    "healthcheck": "Focus on status, metrics, health, and monitoring endpoints.",
    "cdn-edge": "Prioritize edge caches, static assets, and CDN-related paths.",
    "auth-heavy": "Focus on login, SSO, tokens, sessions, MFA, and account flows.",
    "storage": "Focus on uploads, downloads, media, and file storage endpoints.",
    "payments": "Focus on billing, invoices, payments, subscriptions, and webhooks.",
}

GOAL_GUIDANCE = {
    "general": "General discovery for the endpoint.",
    "auth-bypass": "Focus on auth, SSO, OAuth, JWT, tokens, sessions, login, MFA, password flows.",
    "data-exfil": "Focus on backups, dumps, exports, logs, archives, configs, .env, keys.",
    "rce": "Focus on upload, CI/CD, build, debug, admin consoles, plugins, eval endpoints.",
    "misconfig": "Focus on config files, debug, status, health, admin panels.",
    "idor": "Focus on object references, IDs, incremental resources, and parameter-driven access.",
    "ssrf": "Focus on fetch/proxy endpoints, webhooks, import URLs, and URL parameters.",
    "lfi": "Focus on file include endpoints, templates, and path traversal.",
    "sqli": "Focus on data endpoints, reports, exports, and query-based paths.",
    "xss": "Focus on input-heavy endpoints, forms, query params, and UI rendering paths.",
    "csrf": "Focus on state-changing endpoints, forms, and session-sensitive actions.",
    "file-upload": "Focus on upload, import, avatar, media, and attachment endpoints.",
    "secrets": "Focus on config, env, debug, logs, and credentials exposure.",
    "infra": "Focus on health, metrics, status, admin, and internal tooling endpoints.",
    "compliance": "Focus on audit, logs, exports, and data retention endpoints.",
    "webhooks": "Focus on integrations, callbacks, and webhook endpoints.",
    "graphql": "Focus on graphql endpoints, playgrounds, and schema exposure.",
    "mobile": "Focus on mobile API, v1/v2, and app-specific paths.",
    "bypass-waf": "Focus on alternate endpoints, legacy paths, and edge caches.",
}

TECH_KB = {
    "wordpress": [
        "wp-admin", "wp-content", "wp-includes", "xmlrpc.php", "wp-login.php", "wp-config.php", "readme.html",
    ],
    "drupal": ["sites/default", "modules", "core", "user/login", "install.php"],
    "joomla": ["administrator", "components", "modules", "configuration.php"],
    "magento": ["app/etc", "pub", "var", "index.php", "app/bootstrap.php"],
    "shopify": ["apps", "themes", "admin", "checkout"],
    "iis": ["web.config", "Global.asax", "bin", "App_Data", "appsettings.json", "web.config.bak"],
    "dotnet": ["appsettings.json", "bin", "obj", "web.config", "Global.asax"],
    "django": ["manage.py", "admin/", "static/", "media/", "settings.py", "requirements.txt"],
    "flask": ["app.py", "wsgi.py", "static", "templates", "requirements.txt"],
    "fastapi": ["main.py", "openapi.json", "docs", "redoc"],
    "laravel": ["artisan", ".env", "storage", "public", "routes", "vendor"],
    "rails": ["config", "db", "app", "public", "Gemfile", "config/database.yml"],
    "phoenix": ["lib", "priv", "mix.exs", "config", "endpoint.ex"],
    "express": ["app.js", "server.js", "routes", "public", "node_modules"],
    "nextjs": [".next", "next.config.js", "pages", "app", "api", "public"],
    "nuxt": [".nuxt", "nuxt.config.js", "pages", "server", "static"],
    "spring": ["application.properties", "application.yml", "actuator", "WEB-INF", "META-INF"],
    "go": ["main.go", "cmd", "internal", "pkg", "go.mod"],
    "php": ["index.php", "composer.json", "composer.lock", "vendor"],
    "java": ["WEB-INF", "META-INF", "pom.xml"],
    "graphql": ["/graphql", "graphiql", "graphql-playground"],
    "kibana": ["app/kibana", "kibana", "status"],
    "grafana": ["grafana", "login", "api/health"],
    "elasticsearch": ["_search", "_cluster", "_cat"],
    "kibana-api": ["api/saved_objects", "api/status"],
    "prometheus": ["metrics", "api/v1"],
    "loki": ["loki/api", "loki/api/v1"],
    "s3": ["s3.amazonaws.com", "amazonaws.com"],
    "gcs": ["storage.googleapis.com", "googleapis.com"],
    "azure-storage": ["blob.core.windows.net", "queue.core.windows.net"],
    "firebase": ["firebase", "firebaseio.com"],
    "supabase": ["supabase", "rest/v1"],
    "okta": ["okta", "oauth2", "authorize"],
    "auth0": ["auth0", "oauth"],
    "keycloak": ["realms", "protocol/openid-connect"],
    "vault": ["v1/sys", "vault"],
    "jira": ["jira", "rest/api"],
    "confluence": ["confluence", "rest/api"],
    "gitlab": ["gitlab", "api/v4"],
    "github": ["api.github.com", "github"],
    "jenkins": ["jenkins", "script", "manage"],
    "nexus": ["nexus", "service/rest"],
    "artifactory": ["artifactory", "api/storage"],
    "harbor": ["api/v2.0", "harbor"],
    "kubernetes-dashboard": ["api/v1", "kubernetes-dashboard"],
    "argocd": ["argocd", "api/v1"],
    "vaultwarden": ["vaultwarden", "admin"],
    "minio": ["minio", "minio/api"],
    "openapi": ["openapi.json", "swagger"],
}

MODEL_DEFAULTS = {
    "gemini": os.getenv("GEMINI_MODEL", "gemini-3.5-pro"),
    "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
    "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
    "groq": os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
    "openrouter": os.getenv("OPENROUTER_MODEL", "openrouter/auto"),
}


def load_api_keys(single_env, multi_env):
    keys = []
    multi_value = os.getenv(multi_env)
    if multi_value:
        keys.extend([item.strip() for item in multi_value.split(",") if item.strip()])
    single_value = os.getenv(single_env)
    if single_value and single_value not in keys:
        keys.append(single_value)
    return keys


def load_state(state_path):
    try:
        with open(state_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"provider_index": 0, "key_index": {}}


def save_state(state_path, state_data):
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state_data, handle, indent=2, sort_keys=True)


def load_signature_config(signature_path):
    try:
        with open(signature_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"technologies": {}}

def load_wordlist_catalog(catalog_path):
    try:
        with open(catalog_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"lists": {}, "tech_map": {}, "profiles": {}, "goals": {}}

def extract_script_sources(content):
    if not content:
        return []
    soup = BeautifulSoup(content, "html.parser")
    sources = []
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            sources.append(src)
    return sources


def normalize_text(value):
    if not value:
        return ""
    return str(value).lower()


def detect_signatures(signature_config, headers, scripts, content):
    technologies = signature_config.get("technologies", {})
    header_blob = " ".join([f"{key}:{value}" for key, value in headers.items()]).lower()
    script_blob = " ".join(scripts).lower() if scripts else ""
    content_blob = content.lower() if content else ""
    detections = []

    for name, signatures in technologies.items():
        header_signatures = signatures.get("headers", [])
        script_signatures = signatures.get("scripts", [])
        html_signatures = signatures.get("html", [])
        matched = False
        for sig in header_signatures:
            if normalize_text(sig) in header_blob:
                matched = True
                break
        if not matched:
            for sig in script_signatures:
                if normalize_text(sig) in script_blob:
                    matched = True
                    break
        if not matched:
            for sig in html_signatures:
                if normalize_text(sig) in content_blob:
                    matched = True
                    break
        if matched:
            detections.append(name)
    return sorted(set(detections))


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
        return dict(response.headers)
    except requests.RequestException as e:
        print(f"Error fetching headers: {e}")
        return {"Header": "Error fetching headers."}

def probe_methods(url):
    try:
        response = requests.options(url, allow_redirects=True, timeout=20)
        allow_header = response.headers.get("Allow") or response.headers.get("Public")
        methods = []
        if allow_header:
            methods = [method.strip().upper() for method in allow_header.split(",") if method.strip()]
        return {"allowed_methods": methods, "status_code": response.status_code}
    except requests.RequestException as e:
        print(f"Error probing methods: {e}")
        return {"allowed_methods": [], "status_code": None}

def enrich_dns_tls(hostname):
    if not hostname:
        return {"addresses": [], "tls": {}}
    addresses = []
    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            if family == socket.AF_INET:
                addresses.append(sockaddr[0])
            elif family == socket.AF_INET6:
                addresses.append(sockaddr[0])
    except socket.gaierror:
        addresses = []
    addresses = sorted(set(addresses))

    tls_info = {}
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                tls_info = {
                    "issuer": cert.get("issuer"),
                    "subject": cert.get("subject"),
                    "notAfter": cert.get("notAfter"),
                    "notBefore": cert.get("notBefore"),
                    "subjectAltName": cert.get("subjectAltName", []),
                }
    except (OSError, ssl.SSLError):
        tls_info = {}

    return {"addresses": addresses, "tls": tls_info}


def probe_error_page(base_url):
    random_suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(12))
    target = f"{base_url.rstrip('/')}/{random_suffix}"
    try:
        response = requests.get(target, allow_redirects=True, timeout=15)
        content = response.text or ""
        soup = BeautifulSoup(content, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        snippet = " ".join(content.split())[:200]
        return {
            "status_code": response.status_code,
            "title": title,
            "snippet": snippet,
        }
    except requests.RequestException as e:
        print(f"Error probing error page: {e}")
        return {"status_code": None, "title": "", "snippet": ""}

def detect_platform_hints(headers, cookies, scripts, content):
    header_blob = " ".join([f"{key}:{value}" for key, value in headers.items()]).lower()
    cookie_blob = " ".join(cookies).lower() if cookies else ""
    script_blob = " ".join(scripts).lower() if scripts else ""
    content_blob = content.lower() if content else ""

    hints = set()
    for needle, label in [
        ("cloudflare", "cloudflare"),
        ("akamai", "akamai"),
        ("fastly", "fastly"),
        ("imperva", "imperva"),
        ("sucuri", "sucuri"),
        ("incapsula", "imperva"),
        ("vercel", "vercel"),
        ("netlify", "netlify"),
        ("cloudfront", "cloudfront"),
        ("azure frontdoor", "azure-frontdoor"),
        ("frontdoor", "azure-frontdoor"),
        ("aws", "aws"),
        ("amazonaws", "aws"),
        ("azure", "azure"),
        ("google", "gcp"),
        ("gcp", "gcp"),
        ("firebase", "firebase"),
        ("supabase", "supabase"),
        ("nginx", "nginx"),
        ("apache", "apache"),
        ("caddy", "caddy"),
        ("traefik", "traefik"),
        ("varnish", "varnish"),
        ("iis", "iis"),
        ("asp.net", "dotnet"),
        ("php", "php"),
        ("wordpress", "wordpress"),
        ("drupal", "drupal"),
        ("joomla", "joomla"),
        ("laravel", "laravel"),
        ("rails", "rails"),
        ("django", "django"),
        ("flask", "flask"),
        ("fastapi", "fastapi"),
        ("express", "express"),
        ("next", "nextjs"),
        ("nuxt", "nuxt"),
        ("svelte", "svelte"),
        ("vite", "vite"),
        ("react", "react"),
        ("vue", "vue"),
        ("angular", "angular"),
        ("spring", "spring"),
        ("graphql", "graphql"),
        ("shopify", "shopify"),
        ("magento", "magento"),
        ("kibana", "kibana"),
        ("grafana", "grafana"),
        ("elasticsearch", "elasticsearch"),
        ("prometheus", "prometheus"),
        ("loki", "loki"),
        ("okta", "okta"),
        ("auth0", "auth0"),
        ("keycloak", "keycloak"),
    ]:
        if needle in header_blob or needle in cookie_blob or needle in script_blob or needle in content_blob:
            hints.add(label)
    return sorted(hints)

def call_openai(api_key, system, prompt, max_tokens=800):
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=MODEL_DEFAULTS["openai"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def call_anthropic(api_key, system, prompt, max_tokens=1000):
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL_DEFAULTS["anthropic"],
        max_tokens=max_tokens,
        temperature=0,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def call_gemini(api_key, system, prompt, max_tokens=1000):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_DEFAULTS['gemini']}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "system_instruction": {"parts": [{"text": system}]},
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0},
    }
    response = requests.post(url, params={"key": api_key}, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini response missing candidates.")
    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts]
    return "".join(text_parts).strip()


def call_groq(api_key, system, prompt, max_tokens=1000):
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": MODEL_DEFAULTS["groq"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def call_openrouter(api_key, system, prompt, max_tokens=1000):
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": MODEL_DEFAULTS["openrouter"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


class LLMRouter:
    def __init__(self, provider_order, providers, rotate=True, state_path=DEFAULT_STATE_PATH):
        self.provider_order = [p for p in provider_order if providers.get(p, {}).get("keys")]
        self.providers = providers
        self.rotate = rotate
        self.state_path = state_path
        self.state = load_state(state_path)

    def available_providers(self):
        return list(self.provider_order)

    def _next_provider_sequence(self):
        if not self.provider_order:
            return []
        if not self.rotate:
            return self.provider_order
        start_index = self.state.get("provider_index", 0) % len(self.provider_order)
        ordered = self.provider_order[start_index:] + self.provider_order[:start_index]
        return ordered

    def _next_key(self, provider):
        keys = self.providers[provider]["keys"]
        if not keys:
            raise ValueError(f"No API keys configured for {provider}.")
        if not self.rotate:
            return keys[0]
        key_index = self.state.get("key_index", {}).get(provider, 0) % len(keys)
        return keys[key_index]

    def _advance_rotation(self, provider):
        if not self.rotate:
            return
        key_index = self.state.setdefault("key_index", {}).get(provider, 0)
        self.state["key_index"][provider] = key_index + 1
        provider_index = self.state.get("provider_index", 0)
        self.state["provider_index"] = provider_index + 1
        save_state(self.state_path, self.state)

    def _call_provider(self, provider, system, prompt, max_tokens):
        key = self._next_key(provider)
        if provider == "gemini":
            return call_gemini(key, system, prompt, max_tokens=max_tokens)
        if provider == "openai":
            return call_openai(key, system, prompt, max_tokens=max_tokens)
        if provider == "anthropic":
            return call_anthropic(key, system, prompt, max_tokens=max_tokens)
        if provider == "groq":
            return call_groq(key, system, prompt, max_tokens=max_tokens)
        if provider == "openrouter":
            return call_openrouter(key, system, prompt, max_tokens=max_tokens)
        raise ValueError(f"Unsupported provider: {provider}")

    def complete(self, system, prompt, max_tokens=1000):
        errors = []
        for provider in self._next_provider_sequence():
            try:
                response = self._call_provider(provider, system, prompt, max_tokens)
                self._advance_rotation(provider)
                return response
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
        raise ValueError(f"All providers failed: {errors}")

    def complete_with_provider(self, provider, system, prompt, max_tokens=1000):
        if provider not in self.provider_order:
            raise ValueError(f"Provider {provider} not available.")
        response = self._call_provider(provider, system, prompt, max_tokens)
        self._advance_rotation(provider)
        return response


def extract_fingerprints(
    url,
    headers,
    cookies,
    content,
    allowed_methods=None,
    forms=None,
    dns_tls=None,
    error_page=None,
    wappalyzer_matches=None,
):
    fingerprints = {
        "server": headers.get("Server"),
        "powered_by": headers.get("X-Powered-By"),
        "cookies": list(cookies.keys()) if cookies else [],
        "meta_generators": [],
        "script_sources": [],
        "path_hints": [],
        "tech_matches": [],
        "platform_hints": [],
        "allowed_methods": allowed_methods or [],
        "forms": forms or [],
        "dns_tls": dns_tls or {},
        "error_page": error_page or {},
        "wappalyzer": wappalyzer_matches or [],
    }
    if content:
        soup = BeautifulSoup(content, "html.parser")
        for meta in soup.find_all("meta"):
            if meta.get("name", "").lower() == "generator":
                if meta.get("content"):
                    fingerprints["meta_generators"].append(meta.get("content"))
        for script in soup.find_all("script"):
            src = script.get("src")
            if src:
                fingerprints["script_sources"].append(src)
        if forms is None:
            parsed_forms = []
            for form in soup.find_all("form"):
                inputs = []
                for field in form.find_all(["input", "textarea", "select"]):
                    inputs.append({
                        "name": field.get("name"),
                        "type": field.get("type"),
                    })
                parsed_forms.append({
                    "action": form.get("action"),
                    "method": (form.get("method") or "get").lower(),
                    "inputs": inputs,
                })
            fingerprints["forms"] = parsed_forms

    path = urlparse(url).path.lower()
    for tech, indicators in TECH_KB.items():
        for indicator in indicators:
            if indicator.lower() in path:
                fingerprints["tech_matches"].append(tech)
                break
    if "wp-" in path:
        fingerprints["tech_matches"].append("wordpress")
    if "app_data" in path or "web.config" in path:
        fingerprints["tech_matches"].append("iis")
    fingerprints["platform_hints"] = detect_platform_hints(
        headers, fingerprints["cookies"], fingerprints["script_sources"], content or ""
    )
    return fingerprints


def build_plan(url, headers, fingerprints, profile, goal, learned_entries=None):
    prompt = f"""
    Create a brief JSON plan for fuzzing the endpoint with high confidence.
    Include technology_guess (string), likely_platforms (list), risk_focus (list), and rationale (string).
    Use the URL, headers, and fingerprints. Keep it concise and deterministic.
    Profile guidance: {PROFILE_GUIDANCE.get(profile, "")}
    Goal guidance: {GOAL_GUIDANCE.get(goal, "")}
    URL: {url}
    Headers: {headers}
    Fingerprints: {fingerprints}
    Learned entries: {learned_entries}
    JSON Response:
    """
    system = "You are a precise security analyst. Return JSON only."
    return prompt, system


def build_extension_prompt(url, headers, fingerprints, plan, max_extensions, profile, goal, learned_entries=None):
    prompt = f"""
    Given URL, headers, fingerprints, and plan, suggest likely file extensions for fuzzing.
    Respond with JSON: {{"extensions": [".ext1", ".ext2"]}}.
    Do not exceed {max_extensions}. Use high-confidence and relevant extensions only.
    Profile guidance: {PROFILE_GUIDANCE.get(profile, "")}
    Goal guidance: {GOAL_GUIDANCE.get(goal, "")}
    URL: {url}
    Headers: {headers}
    Fingerprints: {fingerprints}
    Plan: {plan}
    Learned entries: {learned_entries}
    JSON Response:
    """
    system = "You are a helpful assistant that suggests file extensions for fuzzing."
    return prompt, system


def build_extension_verification_prompt(url, plan, extensions, profile, goal):
    prompt = f"""
    Validate and prune extension suggestions based on plan and URL.
    Remove irrelevant or low-confidence items. Return JSON only.
    JSON format: {{"extensions": [".ext1", ".ext2"]}}.
    Profile guidance: {PROFILE_GUIDANCE.get(profile, "")}
    Goal guidance: {GOAL_GUIDANCE.get(goal, "")}
    URL: {url}
    Plan: {plan}
    Proposed extensions: {extensions}
    JSON Response:
    """
    system = "You are a strict reviewer who removes low-confidence suggestions."
    return prompt, system


def build_wordlist_prompt(url, headers, fingerprints, plan, max_size, profile, goal, cookies=None, content=None, learned_entries=None):
    prompt = f"""
    Given URL, headers, fingerprints, and plan, suggest a contextual wordlist for content discovery.
    Be as extensive as possible, target size {max_size}, but remain relevant.
    Respond with JSON: {{"wordlist": ["dir1", "file1"]}}.
    Profile guidance: {PROFILE_GUIDANCE.get(profile, "")}
    Goal guidance: {GOAL_GUIDANCE.get(goal, "")}
    URL: {url}
    Headers: {headers}
    Fingerprints: {fingerprints}
    Plan: {plan}
    Cookies: {cookies}
    Content: {content}
    Learned entries: {learned_entries}
    JSON Response:
    """
    system = "You are a helpful assistant that suggests wordlists for fuzzing based on context."
    return prompt, system


def build_wordlist_verification_prompt(url, plan, wordlist, profile, goal):
    prompt = f"""
    Validate and prune wordlist entries. Remove irrelevant or low-confidence items.
    Return JSON: {{"wordlist": ["dir1", "file1"]}}.
    Profile guidance: {PROFILE_GUIDANCE.get(profile, "")}
    Goal guidance: {GOAL_GUIDANCE.get(goal, "")}
    URL: {url}
    Plan: {plan}
    Proposed wordlist: {wordlist}
    JSON Response:
    """
    system = "You are a strict reviewer who removes low-confidence wordlist entries."
    return prompt, system


def build_attack_plan_prompt(url, headers, fingerprints, plan, profile, goal, learned_entries=None):
    prompt = f"""
    Produce a concise attack plan as JSON with fields:
    summary (string), top_targets (list), recommended_ffuf_options (list), follow_up_tools (list).
    Profile guidance: {PROFILE_GUIDANCE.get(profile, "")}
    Goal guidance: {GOAL_GUIDANCE.get(goal, "")}
    URL: {url}
    Headers: {headers}
    Fingerprints: {fingerprints}
    Plan: {plan}
    Learned entries: {learned_entries}
    JSON Response:
    """
    system = "You are a top-tier bug bounty hunter. Provide crisp, actionable steps."
    return prompt, system


def build_strategy_prompt(url, headers, fingerprints, profile, goal, learned_entries=None):
    prompt = f"""
    You are tuning a fuzzing strategy. Return JSON only with:
    mode (extensions|wordlist), wordlist_size (int), max_extensions (int),
    notes (string), and ffuf_tips (list).
    Consider fingerprints, errors, and tech signals.
    Profile guidance: {PROFILE_GUIDANCE.get(profile, "")}
    Goal guidance: {GOAL_GUIDANCE.get(goal, "")}
    URL: {url}
    Headers: {headers}
    Fingerprints: {fingerprints}
    Learned entries: {learned_entries}
    JSON Response:
    """
    system = "You are a precise security strategist. Return JSON only."
    return prompt, system


def get_ai_extensions(url, headers, fingerprints, router, max_extensions, profile, goal, learned_entries=None):
    plan_prompt, plan_system = build_plan(url, headers, fingerprints, profile, goal, learned_entries=learned_entries)
    plan = json.loads(router.complete(plan_system, plan_prompt, max_tokens=400))

    ext_prompt, ext_system = build_extension_prompt(
        url, headers, fingerprints, plan, max_extensions, profile, goal, learned_entries=learned_entries
    )
    extensions = json.loads(router.complete(ext_system, ext_prompt, max_tokens=400))

    verify_prompt, verify_system = build_extension_verification_prompt(
        url, plan, extensions, profile, goal
    )
    verified = json.loads(router.complete(verify_system, verify_prompt, max_tokens=300))
    return plan, verified

def get_contextual_wordlist(url, headers, fingerprints, router, max_size, profile, goal, cookies=None, content=None, learned_entries=None):
    plan_prompt, plan_system = build_plan(url, headers, fingerprints, profile, goal, learned_entries=learned_entries)
    plan = json.loads(router.complete(plan_system, plan_prompt, max_tokens=400))

    wl_prompt, wl_system = build_wordlist_prompt(
        url,
        headers,
        fingerprints,
        plan,
        max_size,
        profile,
        goal,
        cookies=cookies,
        content=content,
        learned_entries=learned_entries,
    )
    wordlists = json.loads(router.complete(wl_system, wl_prompt, max_tokens=2000))

    verify_prompt, verify_system = build_wordlist_verification_prompt(
        url, plan, wordlists, profile, goal
    )
    verified = json.loads(router.complete(verify_system, verify_prompt, max_tokens=1500))
    return plan, verified


def load_cache(cache_path):
    if not cache_path:
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save_cache(cache_path, cache_data):
    if not cache_path:
        return
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as handle:
        json.dump(cache_data, handle, indent=2, sort_keys=True)

def load_findings(findings_path):
    try:
        with open(findings_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_knowledge(kb_path):
    try:
        with open(kb_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"tech_tokens": {}, "global_tokens": {}}


def save_knowledge(kb_path, knowledge_data):
    os.makedirs(os.path.dirname(kb_path), exist_ok=True)
    with open(kb_path, "w", encoding="utf-8") as handle:
        json.dump(knowledge_data, handle, indent=2, sort_keys=True)


def save_findings(findings_path, findings_data):
    os.makedirs(os.path.dirname(findings_path), exist_ok=True)
    with open(findings_path, "w", encoding="utf-8") as handle:
        json.dump(findings_data, handle, indent=2, sort_keys=True)


def update_findings(findings_data, target_url, findings):
    parsed = urlparse(target_url)
    host_key = parsed.netloc
    entries = findings_data.get(host_key, {"paths": [], "extensions": [], "last_seen": None})
    for item in findings:
        if not item:
            continue
        try:
            path = urlparse(item).path
        except ValueError:
            path = str(item)
        if path and path not in entries["paths"]:
            entries["paths"].append(path)
        if "." in path:
            ext = os.path.splitext(path)[1]
            if ext and ext not in entries["extensions"]:
                entries["extensions"].append(ext)
    entries["last_seen"] = time.time()
    findings_data[host_key] = entries
    return findings_data


def extract_learned_entries(findings_data, target_url):
    parsed = urlparse(target_url)
    host_key = parsed.netloc
    entries = findings_data.get(host_key, {})
    return {
        "paths": entries.get("paths", []),
        "extensions": entries.get("extensions", []),
    }


def extract_tokens_from_paths(paths):
    tokens = []
    for path in paths:
        if not path:
            continue
        cleaned = path.strip("/")
        if not cleaned:
            continue
        for segment in cleaned.split("/"):
            if segment and segment not in tokens:
                tokens.append(segment)
    return tokens


def update_knowledge_base(knowledge_data, techs, paths):
    tokens = extract_tokens_from_paths(paths)
    for token in tokens:
        knowledge_data["global_tokens"][token] = knowledge_data["global_tokens"].get(token, 0) + 1
    for tech in techs:
        tech_bucket = knowledge_data["tech_tokens"].setdefault(tech, {})
        for token in tokens:
            tech_bucket[token] = tech_bucket.get(token, 0) + 1
    return knowledge_data


def get_top_tokens(token_map, limit=30):
    sorted_items = sorted(token_map.items(), key=lambda item: item[1], reverse=True)
    return [item[0] for item in sorted_items[:limit]]


def merge_unique(primary_list, extra_list, max_size=None):
    combined = list(primary_list)
    for item in extra_list:
        if item not in combined:
            combined.append(item)
    if max_size is not None:
        return combined[:max_size]
    return combined


def normalize_learned_paths(paths):
    normalized = []
    for path in paths:
        if not path:
            continue
        cleaned = path.lstrip("/")
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def normalize_extensions(extensions):
    normalized = []
    for ext in extensions:
        if not ext:
            continue
        cleaned = ext if ext.startswith(".") else f".{ext}"
        if cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def load_wordlist_entries(catalog, list_names, max_size=None):
    entries = []
    lists = catalog.get("lists", {})
    for list_name in list_names:
        list_def = lists.get(list_name, {})
        for entry in list_def.get("entries", []):
            if entry not in entries:
                entries.append(entry)
        for path in list_def.get("paths", []):
            if not path or not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        value = line.strip()
                        if value and value not in entries:
                            entries.append(value)
            except OSError:
                continue
    if max_size is not None:
        return entries[:max_size]
    return entries


def select_wordlists(catalog, techs, profile, goal, mode):
    selected = []
    profiles = catalog.get("profiles", {})
    goals = catalog.get("goals", {})
    tech_map = catalog.get("tech_map", {})
    if mode == "wordlist":
        selected.extend(profiles.get(profile, []))
        selected.extend(goals.get(goal, []))
    for tech in techs:
        selected.extend(tech_map.get(tech, []))
    return list(dict.fromkeys(selected))


def classify_findings(findings):
    categories = set()
    for item in findings:
        if not item:
            continue
        path = urlparse(item).path.lower()
        if "/admin" in path or "admin" in path:
            categories.add("admin")
        if "/api" in path or "graphql" in path:
            categories.add("api")
        if "login" in path or "auth" in path or "signin" in path:
            categories.add("auth")
        if "backup" in path or "dump" in path or "tar" in path or "zip" in path:
            categories.add("backup")
        if "debug" in path or "trace" in path:
            categories.add("debug")
    return sorted(categories)


def merge_wordlists(primary, extra, max_size=None):
    combined = list(primary)
    for entry in extra:
        if entry not in combined:
            combined.append(entry)
    if max_size is not None:
        return combined[:max_size]
    return combined


def extract_paths_from_js(js_content):
    if not js_content:
        return []
    paths = set()
    for match in re.findall(r"\\/([a-zA-Z0-9_\\-\\/]{3,})", js_content):
        if match:
            paths.add(match)
    for match in re.findall(r"/[a-zA-Z0-9_\\-\\/]{3,}", js_content):
        paths.add(match.lstrip("/"))
    return sorted(paths)


def fetch_js_paths(script_urls, base_url, max_files=5):
    paths = []
    for url in script_urls[:max_files]:
        if url.startswith("//"):
            url = f"https:{url}"
        elif url.startswith("/"):
            url = f"{base_url.rstrip('/')}{url}"
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            paths.extend(extract_paths_from_js(response.text))
        except requests.RequestException:
            continue
    return list(dict.fromkeys(paths))


def fetch_sitemap_paths(base_url):
    candidates = [f"{base_url.rstrip('/')}/sitemap.xml", f"{base_url.rstrip('/')}/sitemap_index.xml"]
    paths = []
    for url in candidates:
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            xml = response.text
            for match in re.findall(r"<loc>(.*?)</loc>", xml):
                try:
                    parsed = urlparse(match)
                    if parsed.path:
                        paths.append(parsed.path.lstrip("/"))
                except ValueError:
                    continue
        except requests.RequestException:
            continue
    return list(dict.fromkeys(paths))


def fetch_robots_paths(base_url):
    paths = []
    url = f"{base_url.rstrip('/')}/robots.txt"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        for line in response.text.splitlines():
            line = line.strip()
            if line.lower().startswith("disallow:") or line.lower().startswith("allow:"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    value = parts[1].strip()
                    if value and value != "/":
                        paths.append(value.lstrip("/"))
    except requests.RequestException:
        return []
    return list(dict.fromkeys(paths))
def parse_provider_order(value):
    if not value:
        return DEFAULT_PROVIDER_ORDER
    return [item.strip() for item in value.split(",") if item.strip()]


def build_provider_pool():
    return {
        "gemini": {"keys": load_api_keys("GEMINI_API_KEY", "GEMINI_API_KEYS")},
        "openai": {"keys": load_api_keys("OPENAI_API_KEY", "OPENAI_API_KEYS")},
        "anthropic": {"keys": load_api_keys("ANTHROPIC_API_KEY", "ANTHROPIC_API_KEYS")},
        "groq": {"keys": load_api_keys("GROQ_API_KEY", "GROQ_API_KEYS")},
        "openrouter": {"keys": load_api_keys("OPENROUTER_API_KEY", "OPENROUTER_API_KEYS")},
    }

def cache_key(url, headers, fingerprints, mode, profile, goal, max_size, learned_entries=None):
    payload = json.dumps(
        {
            "url": url,
            "headers": headers,
            "fingerprints": fingerprints,
            "mode": mode,
            "profile": profile,
            "goal": goal,
            "max_size": max_size,
            "learned_entries": learned_entries,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def choose_mode(url, profile=None):
    parsed = urlparse(url)
    path = parsed.path.lower()
    if profile == "api-only":
        return "wordlist"
    if profile == "spa":
        return "extensions"
    if path.endswith((".js", ".css", ".json", ".xml")):
        return "extensions"
    if any(segment in path for segment in ["/api", "/admin", "/login", "/auth", "/account", "/checkout"]):
        return "wordlist"
    if path.count("/") <= 2:
        return "extensions"
    return "wordlist"


def get_consensus_extensions(url, headers, fingerprints, max_extensions, profile, goal, router, learned_entries=None):
    providers = router.available_providers()
    if not providers:
        raise ValueError("Consensus requires at least one provider.")
    results = []
    for provider in providers:
        plan_prompt, plan_system = build_plan(url, headers, fingerprints, profile, goal, learned_entries=learned_entries)
        plan = json.loads(router.complete_with_provider(provider, plan_system, plan_prompt, max_tokens=400))
        ext_prompt, ext_system = build_extension_prompt(
            url, headers, fingerprints, plan, max_extensions, profile, goal, learned_entries=learned_entries
        )
        extensions = json.loads(router.complete_with_provider(provider, ext_system, ext_prompt, max_tokens=400))
        verify_prompt, verify_system = build_extension_verification_prompt(url, plan, extensions, profile, goal)
        verified = json.loads(router.complete_with_provider(provider, verify_system, verify_prompt, max_tokens=300))
        results.append((plan, verified))
    merged = [entry for _, entry in results]
    all_extensions = []
    for item in merged:
        all_extensions.extend(item.get("extensions", []))
    extensions = list(dict.fromkeys(all_extensions))
    intersection = set(merged[0].get("extensions", []))
    for entry in merged[1:]:
        intersection &= set(entry.get("extensions", []))
    final = list(intersection) if intersection else extensions
    plan = results[0][0]
    return plan, {"extensions": final[:max_extensions]}


def get_consensus_wordlist(url, headers, fingerprints, max_size, profile, goal, router, cookies=None, content=None, learned_entries=None):
    providers = router.available_providers()
    if not providers:
        raise ValueError("Consensus requires at least one provider.")
    results = []
    for provider in providers:
        plan_prompt, plan_system = build_plan(url, headers, fingerprints, profile, goal, learned_entries=learned_entries)
        plan = json.loads(router.complete_with_provider(provider, plan_system, plan_prompt, max_tokens=400))
        wl_prompt, wl_system = build_wordlist_prompt(
            url,
            headers,
            fingerprints,
            plan,
            max_size,
            profile,
            goal,
            cookies=cookies,
            content=content,
            learned_entries=learned_entries,
        )
        wordlists = json.loads(router.complete_with_provider(provider, wl_system, wl_prompt, max_tokens=2000))
        verify_prompt, verify_system = build_wordlist_verification_prompt(url, plan, wordlists, profile, goal)
        verified = json.loads(router.complete_with_provider(provider, verify_system, verify_prompt, max_tokens=1500))
        results.append((plan, verified))
    merged = [entry for _, entry in results]
    all_items = []
    for item in merged:
        all_items.extend(item.get("wordlist", []))
    combined = list(dict.fromkeys(all_items))
    intersection = set(merged[0].get("wordlist", []))
    for entry in merged[1:]:
        intersection &= set(entry.get("wordlist", []))
    final = list(intersection) if intersection else combined
    plan = results[0][0]
    return plan, {"wordlist": final[:max_size]}


def generate_attack_plan(url, headers, fingerprints, plan, router, profile, goal, learned_entries=None):
    prompt, system = build_attack_plan_prompt(
        url, headers, fingerprints, plan, profile, goal, learned_entries=learned_entries
    )
    return json.loads(router.complete(system, prompt, max_tokens=500))


def parse_ffuf_json(output_path):
    try:
        with open(output_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    results = data.get("results", [])
    return [item.get("url") or item.get("input", {}).get("FUZZ") for item in results]


def build_refinement_prompt(url, findings, profile, goal):
    prompt = f"""
    Based on the discovered URLs/paths, suggest refined additions for fuzzing.
    Return JSON: {{"wordlist": ["new1", "new2"]}}.
    Profile guidance: {PROFILE_GUIDANCE.get(profile, "")}
    Goal guidance: {GOAL_GUIDANCE.get(goal, "")}
    URL: {url}
    Findings: {findings}
    JSON Response:
    """
    system = "You are a strict reviewer who proposes only high-signal refinements."
    return prompt, system


def apply_strategy_overrides(strategy, default_mode, default_wordlist_size, default_max_extensions):
    if not strategy:
        return default_mode, default_wordlist_size, default_max_extensions
    mode = strategy.get("mode") or default_mode
    wordlist_size = strategy.get("wordlist_size") or default_wordlist_size
    max_extensions = strategy.get("max_extensions") or default_max_extensions
    return mode, wordlist_size, max_extensions

def main():
    parser = argparse.ArgumentParser(description='ffufai - AI-powered ffuf wrapper')
    parser.add_argument('--ffuf-path', default='ffuf', help='Path to ffuf executable')
    parser.add_argument('--max-extensions', type=int, default=4, help='Maximum number of extensions to suggest')
    parser.add_argument('--wordlists', action='store_true', help='Generate contextual wordlists')
    parser.add_argument('--max-wordlist-size', type=int, help="The maximum size of the generated wordlist")
    parser.add_argument('--include-response', action='store_true', help='Makes a GET request and uses the Response as context for better wordlist generation (Uses More tokens)')
    parser.add_argument('--mode', choices=['extensions', 'wordlist', 'auto'], default='auto', help='Choose extension, wordlist, or auto mode')
    parser.add_argument('--profile', choices=PROFILE_GUIDANCE.keys(), default='balanced', help='Tuning profile')
    parser.add_argument('--goal', choices=GOAL_GUIDANCE.keys(), default='general', help='Primary hunting goal')
    parser.add_argument('--consensus', action='store_true', help='Use all available providers for consensus suggestions')
    parser.add_argument('--cache-path', default=DEFAULT_CACHE_PATH, help='Cache path for AI results')
    parser.add_argument('--no-cache', action='store_true', help='Disable cache usage')
    parser.add_argument('--state-path', default=DEFAULT_STATE_PATH, help='State file path for provider rotation')
    parser.add_argument('--findings-path', default=DEFAULT_FINDINGS_PATH, help='Path for persisted findings')
    parser.add_argument('--knowledge-path', default=DEFAULT_KB_PATH, help='Path to global knowledge base')
    parser.add_argument('--signature-path', default=DEFAULT_SIGNATURE_PATH, help='Path to tech signature JSON file')
    parser.add_argument('--wordlist-catalog', default=DEFAULT_WORDLIST_CATALOG, help='Path to wordlist catalog JSON')
    parser.add_argument('--providers', help='Comma-separated provider order (gemini,openai,anthropic,groq,openrouter)')
    parser.add_argument('--no-rotate', action='store_true', help='Disable provider/key rotation')
    parser.add_argument('--probe-methods', action='store_true', help='Use OPTIONS to check allowed methods')
    parser.add_argument('--dns-tls', action='store_true', help='Enrich context with DNS and TLS metadata')
    parser.add_argument('--error-probe', action='store_true', help='Probe a random error page for context')
    parser.add_argument('--ai-strategy', action='store_true', help='Use AI to tune mode and list sizes')
    parser.add_argument('--recon', action='store_true', help='Enable recon-driven wordlist generation')
    parser.add_argument('--recon-max-js', type=int, default=5, help='Max JS files to mine for paths')
    parser.add_argument('--no-persist', action='store_true', help='Disable persistence of successful findings')
    parser.add_argument('--report', action='store_true', help='Generate a concise attack plan report')
    parser.add_argument('--feedback-loop', action='store_true', help='Run a refinement pass based on ffuf results')
    parser.add_argument('--feedback-rounds', type=int, default=1, help='How many refinement rounds to run')
    parser.add_argument('--targets-file', help='Run against multiple URLs from a file (one URL per line)')
    args, unknown = parser.parse_known_args()

    # Find the -u argument in the unknown args or use targets file
    urls = []
    if args.targets_file:
        try:
            with open(args.targets_file, "r", encoding="utf-8") as handle:
                urls = [line.strip() for line in handle if line.strip()]
        except FileNotFoundError:
            print("Error: targets file not found.")
            return
    else:
        try:
            url_index = unknown.index('-u') + 1
            urls = [unknown[url_index]]
        except (ValueError, IndexError):
            print("Error: -u URL argument is required.")
            return

    cache_data = {} if args.no_cache else load_cache(args.cache_path)
    if "results" in cache_data:
        cache_results = cache_data.get("results", {})
    else:
        cache_results = cache_data

    provider_pool = build_provider_pool()
    provider_order = parse_provider_order(args.providers)
    router = LLMRouter(provider_order, provider_pool, rotate=not args.no_rotate, state_path=args.state_path)
    if not router.available_providers():
        print("Error: No API keys found. Set GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, or OPENROUTER_API_KEY.")
        return

    findings_data = load_findings(args.findings_path)
    knowledge_data = load_knowledge(args.knowledge_path)
    signature_config = load_signature_config(args.signature_path)
    wordlist_catalog = load_wordlist_catalog(args.wordlist_catalog)

    for url in urls:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        base_url = url.replace('FUZZ', '')

        if 'FUZZ' not in path_parts[-1]:
            print("Warning: FUZZ keyword is not at the end of the URL path. Extension fuzzing may not work as expected.")

        headers = get_headers(base_url)
        cookies = None
        content = None
        allowed_methods = []
        dns_tls = {}
        error_page = {}
        strategy = None
        if args.probe_methods:
            method_probe = probe_methods(base_url)
            allowed_methods = method_probe.get("allowed_methods", [])
        if args.dns_tls:
            dns_tls = enrich_dns_tls(parsed_url.hostname)
        if args.error_probe:
            error_page = probe_error_page(base_url)
        if args.include_response:
            response = get_response(base_url)
            headers = response.get('headers', headers)
            cookies = response.get('cookies')
            content = response.get('content')
        scripts = extract_script_sources(content or "")
        wappalyzer_matches = detect_signatures(signature_config, headers, scripts, content or "")
        fingerprints = extract_fingerprints(
            base_url,
            headers,
            cookies or {},
            content,
            allowed_methods=allowed_methods,
            dns_tls=dns_tls,
            error_page=error_page,
            wappalyzer_matches=wappalyzer_matches,
        )
        learned_entries = extract_learned_entries(findings_data, base_url)
        combined_techs = list(dict.fromkeys(fingerprints.get("platform_hints", []) + wappalyzer_matches))
        catalog_lists = select_wordlists(wordlist_catalog, combined_techs, args.profile, args.goal, mode)

        mode = args.mode
        if args.wordlists:
            mode = "wordlist"
        elif mode == "auto":
            mode = choose_mode(url, args.profile)

        default_wordlist_size = args.max_wordlist_size or 200
        max_extensions = args.max_extensions
        recon_paths = []
        if mode == "wordlist" and catalog_lists:
            default_wordlist_size = max(default_wordlist_size, len(catalog_lists) * 25)
        if args.recon and mode == "wordlist":
            recon_paths.extend(fetch_robots_paths(base_url))
            recon_paths.extend(fetch_sitemap_paths(base_url))
            if scripts:
                recon_paths.extend(fetch_js_paths(scripts, base_url, max_files=args.recon_max_js))
            recon_paths = list(dict.fromkeys(recon_paths))
        if args.ai_strategy:
            strategy_prompt, strategy_system = build_strategy_prompt(
                url, headers, fingerprints, args.profile, args.goal, learned_entries=learned_entries
            )
            try:
                strategy = json.loads(router.complete(strategy_system, strategy_prompt, max_tokens=300))
                mode, default_wordlist_size, max_extensions = apply_strategy_overrides(
                    strategy, mode, default_wordlist_size, max_extensions
                )
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing AI strategy response. Using defaults. Error: {e}")

        cache_identifier = cache_key(
            url,
            headers,
            fingerprints,
            mode,
            args.profile,
            args.goal,
            default_wordlist_size if mode == "wordlist" else max_extensions,
            learned_entries=learned_entries,
        )

        plan = None
        report = None
        if not args.no_cache and cache_identifier in cache_results:
            cached = cache_results[cache_identifier]
            plan = cached.get("plan")
            output = cached.get("output")
            report = cached.get("report")
        else:
            output = None

        if mode == "wordlist":
            try:
                size = default_wordlist_size
                if output is None:
                    if args.consensus:
                        plan, output = get_consensus_wordlist(
                            url,
                            headers,
                            fingerprints,
                            size,
                            args.profile,
                            args.goal,
                            router,
                            cookies=cookies,
                            content=content,
                            learned_entries=learned_entries,
                        )
                    else:
                        plan, output = get_contextual_wordlist(
                            url,
                            headers,
                            fingerprints,
                            router,
                            size,
                            args.profile,
                            args.goal,
                            cookies=cookies,
                            content=content,
                            learned_entries=learned_entries,
                        )
                if args.report and report is None:
                    report = generate_attack_plan(
                        url, headers, fingerprints, plan, router, args.profile, args.goal, learned_entries=learned_entries
                    )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error parsing AI response. Error: {e}")
                return

            print(output)
            if strategy:
                print(json.dumps(strategy, indent=2))
            learned_paths = normalize_learned_paths(learned_entries.get("paths", []))
            catalog_entries = load_wordlist_entries(wordlist_catalog, catalog_lists)
            knowledge_tokens = get_top_tokens(knowledge_data.get("global_tokens", {}), limit=50)
            tech_tokens = []
            for tech in combined_techs:
                tech_tokens.extend(get_top_tokens(knowledge_data.get("tech_tokens", {}).get(tech, {}), limit=30))
            combined_wordlist = merge_wordlists(catalog_entries, output['wordlist'])
            combined_wordlist = merge_wordlists(combined_wordlist, learned_paths)
            combined_wordlist = merge_wordlists(combined_wordlist, recon_paths)
            combined_wordlist = merge_wordlists(combined_wordlist, tech_tokens)
            combined_wordlist = merge_wordlists(combined_wordlist, knowledge_tokens, max_size=size)
            wordlist = '\n'.join(combined_wordlist)

            if args.report and report:
                print(json.dumps(report, indent=2))

            if not args.no_cache:
                cache_results[cache_identifier] = {"plan": plan, "output": output, "report": report, "timestamp": time.time()}
                if cache_results is cache_data:
                    save_cache(args.cache_path, cache_results)
                else:
                    cache_data["results"] = cache_results
                    save_cache(args.cache_path, cache_data)

            if wordlist:
                file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
                file.write(wordlist)
                file.close()
                ffuf_command = [args.ffuf_path] + unknown + ['-w', file.name]
                output_json = None
                if not args.no_persist or args.feedback_loop:
                    output_json = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
                    output_json.close()
                    ffuf_command += ['-o', output_json.name, '-of', 'json']
                subprocess.run(ffuf_command)

                if output_json and not args.no_persist:
                    findings = parse_ffuf_json(output_json.name)
                    if findings:
                        findings_data = update_findings(findings_data, base_url, findings)
                        save_findings(args.findings_path, findings_data)
                        knowledge_data = update_knowledge_base(knowledge_data, combined_techs, findings)
                        save_knowledge(args.knowledge_path, knowledge_data)

                if args.feedback_loop:
                    for _ in range(max(1, args.feedback_rounds)):
                        if not output_json:
                            break
                        findings = parse_ffuf_json(output_json.name)
                        if not findings:
                            break
                        refine_prompt, refine_system = build_refinement_prompt(url, findings, args.profile, args.goal)
                        refinement = json.loads(router.complete(refine_system, refine_prompt, max_tokens=600))
                        refined_list = refinement.get("wordlist", [])
                        categories = classify_findings(findings)
                        adaptive_lists = load_wordlist_entries(wordlist_catalog, categories)
                        refined_list = merge_wordlists(refined_list, adaptive_lists)
                        if not refined_list:
                            break
                        refinement_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
                        refinement_file.write('\n'.join(refined_list))
                        refinement_file.close()
                        ffuf_command = [args.ffuf_path] + unknown + ['-w', refinement_file.name]
                        output_json = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
                        output_json.close()
                        ffuf_command += ['-o', output_json.name, '-of', 'json']
                        subprocess.run(ffuf_command)

        else:
            try:
                if output is None:
                    if args.consensus:
                        plan, output = get_consensus_extensions(
                            url,
                            headers,
                            fingerprints,
                            max_extensions,
                            args.profile,
                            args.goal,
                            router,
                            learned_entries=learned_entries,
                        )
                    else:
                        plan, output = get_ai_extensions(
                            url,
                            headers,
                            fingerprints,
                            router,
                            max_extensions,
                            args.profile,
                            args.goal,
                            learned_entries=learned_entries,
                        )
                if args.report and report is None:
                    report = generate_attack_plan(
                        url, headers, fingerprints, plan, router, args.profile, args.goal, learned_entries=learned_entries
                    )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error parsing AI response. Try again. Error: {e}")
                return

            print(output)
            if strategy:
                print(json.dumps(strategy, indent=2))
            learned_exts = normalize_extensions(learned_entries.get("extensions", []))
            combined_extensions = merge_unique(learned_exts, output['extensions'], max_size=max_extensions)
            extensions = ','.join(combined_extensions)

            if args.report and report:
                print(json.dumps(report, indent=2))

            if not args.no_cache:
                cache_results[cache_identifier] = {"plan": plan, "output": output, "report": report, "timestamp": time.time()}
                if cache_results is cache_data:
                    save_cache(args.cache_path, cache_results)
                else:
                    cache_data["results"] = cache_results
                    save_cache(args.cache_path, cache_data)

            ffuf_command = [args.ffuf_path] + unknown + ['-e', extensions]
            output_json = None
            if not args.no_persist:
                output_json = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
                output_json.close()
                ffuf_command += ['-o', output_json.name, '-of', 'json']
            subprocess.run(ffuf_command)
            if output_json and not args.no_persist:
                findings = parse_ffuf_json(output_json.name)
                if findings:
                    findings_data = update_findings(findings_data, base_url, findings)
                    save_findings(args.findings_path, findings_data)
                    knowledge_data = update_knowledge_base(knowledge_data, combined_techs, findings)
                    save_knowledge(args.knowledge_path, knowledge_data)


if __name__ == '__main__':
    main()
