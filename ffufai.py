#!/usr/bin/env python3

import argparse
import os
import subprocess
import requests
import json
import shutil
import re
from urllib.parse import urlparse

from providers.gemini import GeminiProvider
from providers.openai import OpenAIProvider
from providers.anthropic import AnthropicProvider
from providers.huggingface_local import HuggingFaceLocalProvider


def get_provider():
    if os.getenv("GEMINI_API_KEY"):
        return GeminiProvider(os.getenv("GEMINI_API_KEY"))
    if os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicProvider(os.getenv("ANTHROPIC_API_KEY"))
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIProvider(os.getenv("OPENAI_API_KEY"))
    if os.getenv("HUGGINGFACE_API_KEY"):
        return HuggingFaceLocalProvider()

    raise RuntimeError("No AI provider API key found")


def get_headers(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=5)
        return dict(r.headers)
    except Exception:
        return {}


def colorize_ffuf_output(line):
    line = line.decode(errors="ignore").strip()
    m = re.search(r"\[Status: (\d{3})", line)
    if m:
        code = int(m.group(1))
        color = (
            "\033[92m" if code == 200 else
            "\033[94m" if code in (301, 302) else
            "\033[91m" if code == 403 else
            "\033[0m"
        )
        print(f"{color}{line}\033[0m")
    else:
        print(line)


def main():
    parser = argparse.ArgumentParser(
        description="ffufai – AI-powered ffuf wrapper"
    )
    parser.add_argument("--ffuf-path", default="ffuf")
    parser.add_argument("--max-extensions", type=int, default=5)
    args, unknown = parser.parse_known_args()

    try:
        url = unknown[unknown.index("-u") + 1]
    except Exception:
        print("❌ You must provide -u URL")
        return

    base_url = url.replace("FUZZ", "")
    headers = get_headers(base_url)

    provider = get_provider()
    print(f"🔌 Using AI backend: {provider.name}")

    try:
        data = provider.get_extensions(url, headers, args.max_extensions)
        exts = data.get("extensions", [])
        if not exts:
            raise ValueError
    except Exception:
        exts = [".php", ".html", ".json", ".bak"]

    exts = ",".join(e if e.startswith(".") else f".{e}" for e in exts[:args.max_extensions])

    if not shutil.which(args.ffuf_path):
        print("❌ ffuf binary not found")
        return

    cmd = [args.ffuf_path] + unknown + ["-e", exts]
    print("▶️ Running:", " ".join(cmd))

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
        for line in proc.stdout:
            colorize_ffuf_output(line)


if __name__ == "__main__":
    main()
