<div align="center">

<img src="https://github.com/user-attachments/assets/1f9ce2d7-8f9d-4746-bad4-acfccad74900" alt="ffufai_logo" width="400">

# `ffufai`

![GitHub top language](https://img.shields.io/github/languages/top/jthack/ffufai)
![GitHub last commit](https://img.shields.io/github/last-commit/jthack/ffufai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

<p class="align center">

ffufai is an AI-powered wrapper for the popular web fuzzer ffuf. It automatically suggests file extensions or contextual wordlists for fuzzing based on the target URL, headers, and response signals, using Gemini (default priority), OpenAI, Anthropic, Groq, or OpenRouter models.

</p>

</div>

## Features
<img width="600  " alt="image" src="https://github.com/user-attachments/assets/0384d4f0-3a07-48d9-9805-ea1e76b6b693">

- Seamlessly integrates with ffuf
- Auto mode (extension or wordlist) with stack-aware suggestions
- Multi-phase AI inference (plan → generate → verify) to reduce false positives
- Multi-provider routing with Gemini-first priority and optional consensus mode
- Profiles and goals to bias toward critical targets
- Wappalyzer-style signature detection for fast tech hints
- Tech-aware wordlist selection via catalog mappings
- Optional feedback loop that refines wordlists based on ffuf results
- Active-learning persistence of successful findings
- DNS/TLS and error-page context enrichment
- Caching for faster repeated scans
- Passes through all ffuf parameters

## Prerequisites

- Python 3.6+
- ffuf (installed and accessible in your PATH)
- At least one API key: Gemini, OpenAI, Anthropic, Groq, or OpenRouter

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/jthack/ffufai
   cd ffufai
   ```

2. Install the required Python packages:
   ```
   pip install requests openai anthropic beautifulsoup4
   ```

3. Make the script executable:
   ```
   chmod +x ffufai.py
   ```

4. (Optional) To use ffufai from anywhere, you can create a symbolic link in a directory that's in your PATH. For example:
   ```
   sudo ln -s /full/path/to/ffufai.py /usr/local/bin/ffufai
   ```
   Replace "/full/path/to/ffufai.py" with the actual full path to where you cloned the repository.

5. Set up your API key as an environment variable:
   For OpenAI:
   ```
   export OPENAI_API_KEY='your-api-key-here'
   ```
   Or for Anthropic:
   ```
   export ANTHROPIC_API_KEY='your-api-key-here'
   ```
   Or for Gemini:
   ```
   export GEMINI_API_KEY='your-api-key-here'
   ```
   Or for Groq:
   ```
   export GROQ_API_KEY='your-api-key-here'
   ```
   Or for OpenRouter:
   ```
   export OPENROUTER_API_KEY='your-api-key-here'
   ```

   You can also provide multiple API keys for rotation:
   ```
   export GEMINI_API_KEYS='key1,key2'
   export OPENAI_API_KEYS='key1,key2'
   export ANTHROPIC_API_KEYS='key1,key2'
   export GROQ_API_KEYS='key1,key2'
   export OPENROUTER_API_KEYS='key1,key2'
   ```

   Optional model overrides:
   ```
   export GEMINI_MODEL='gemini-3.5-pro'
   export OPENAI_MODEL='gpt-4o'
   export ANTHROPIC_MODEL='claude-sonnet-4-20250514'
   export GROQ_MODEL='llama-3.1-70b-versatile'
   export OPENROUTER_MODEL='openrouter/auto'
   ```

   You can add these lines to your `~/.bashrc` or `~/.zshrc` file to make them permanent.

## Usage

Use ffufai just like you would use ffuf, but replace `ffuf` with `python3 ffufai.py` (or just `ffufai` if you've created the symbolic link):

```
python3 ffufai.py -u https://example.com/FUZZ -w /path/to/wordlist.txt
```

Or if you've created the symbolic link:

```
ffufai -u https://example.com/FUZZ -w /path/to/wordlist.txt
```

ffufai will automatically suggest extensions or wordlists based on the URL and add them to the ffuf command.

## Parameters

ffufai accepts all the parameters that ffuf does, plus a few additional ones:

- `--ffuf-path`: Specifies the path to the ffuf executable. Default is 'ffuf'.  
  Example: `ffufai --ffuf-path /usr/local/bin/ffuf -u https://example.com/FUZZ -w wordlist.txt`

- `--max-extensions`: Sets the maximum number of extensions to suggest. Default is 4.  
  Example: `ffufai --max-extensions 6 -u https://example.com/FUZZ -w wordlist.txt`

- `--mode`: Choose `extensions`, `wordlist`, or `auto` (default).  
  Example: `ffufai --mode wordlist -u https://example.com/FUZZ -w wordlist.txt`

- `--profile`: Tuning profile (`balanced`, `critical`, `stealth`, `depth`, `api-only`, `spa`, `admin-heavy`, `cloud-native`, `legacy`, `mobile-backend`, `partner-portal`, `healthcheck`, `cdn-edge`, `auth-heavy`, `storage`, `payments`).  
  Example: `ffufai --profile critical -u https://example.com/FUZZ -w wordlist.txt`

- `--goal`: Primary hunting goal (`general`, `auth-bypass`, `data-exfil`, `rce`, `misconfig`, `idor`, `ssrf`, `lfi`, `sqli`, `xss`, `csrf`, `file-upload`, `secrets`, `infra`, `compliance`, `webhooks`, `graphql`, `mobile`, `bypass-waf`).  
  Example: `ffufai --goal data-exfil -u https://example.com/FUZZ -w wordlist.txt`

- `--consensus`: Use all available providers to cross-check suggestions.  
  Example: `ffufai --consensus -u https://example.com/FUZZ -w wordlist.txt`

- `--cache-path`: Path to the cache file (default `~/.cache/ffufai/cache.json`).  
  Example: `ffufai --cache-path /tmp/ffufai-cache.json -u https://example.com/FUZZ -w wordlist.txt`

- `--no-cache`: Disable cache usage.  
  Example: `ffufai --no-cache -u https://example.com/FUZZ -w wordlist.txt`

- `--state-path`: Path to the rotation state file (default `~/.cache/ffufai/state.json`).  
  Example: `ffufai --state-path /tmp/ffufai-state.json -u https://example.com/FUZZ -w wordlist.txt`

- `--findings-path`: Path to the findings persistence file (default `~/.cache/ffufai/findings.json`).  
  Example: `ffufai --findings-path /tmp/ffufai-findings.json -u https://example.com/FUZZ -w wordlist.txt`

- `--knowledge-path`: Path to the global knowledge base (default `~/.cache/ffufai/knowledge.json`).  
  Example: `ffufai --knowledge-path /tmp/ffufai-knowledge.json -u https://example.com/FUZZ -w wordlist.txt`

- `--signature-path`: Path to the tech signature JSON file (default `config/tech_signatures.json`).  
  Example: `ffufai --signature-path /tmp/tech_signatures.json -u https://example.com/FUZZ -w wordlist.txt`

- `--wordlist-catalog`: Path to the wordlist catalog JSON file (default `config/wordlist_catalog.json`).  
  Example: `ffufai --wordlist-catalog /tmp/wordlist_catalog.json -u https://example.com/FUZZ -w wordlist.txt`

- `--providers`: Comma-separated provider order (gemini,openai,anthropic,groq,openrouter).  
  Example: `ffufai --providers gemini,openai,groq -u https://example.com/FUZZ -w wordlist.txt`

- `--no-rotate`: Disable provider/key rotation.  
  Example: `ffufai --no-rotate -u https://example.com/FUZZ -w wordlist.txt`

- `--probe-methods`: Use OPTIONS to check allowed HTTP methods and include in AI context.  
  Example: `ffufai --probe-methods -u https://example.com/FUZZ -w wordlist.txt`

- `--dns-tls`: Enrich context with DNS and TLS metadata.  
  Example: `ffufai --dns-tls -u https://example.com/FUZZ -w wordlist.txt`

- `--error-probe`: Probe a random error page for context.  
  Example: `ffufai --error-probe -u https://example.com/FUZZ -w wordlist.txt`

- `--ai-strategy`: Use AI to tune mode and list sizes.  
  Example: `ffufai --ai-strategy -u https://example.com/FUZZ -w wordlist.txt`

- `--recon`: Enable recon-driven wordlist generation (robots/sitemap/JS).  
  Example: `ffufai --recon -u https://example.com/FUZZ -w wordlist.txt`

- `--recon-max-js`: Max JS files to mine for paths (default 5).  
  Example: `ffufai --recon --recon-max-js 10 -u https://example.com/FUZZ -w wordlist.txt`

- `--no-persist`: Disable persistence of successful findings.  
  Example: `ffufai --no-persist -u https://example.com/FUZZ -w wordlist.txt`

- `--report`: Print a concise, AI-generated attack plan report.  
  Example: `ffufai --report -u https://example.com/FUZZ -w wordlist.txt`

- `--feedback-loop`: Run a refinement pass based on ffuf results (wordlist mode).  
  Example: `ffufai --wordlists --feedback-loop -u https://example.com/FUZZ -w wordlist.txt`

- `--feedback-rounds`: Number of refinement rounds (default 1).  
  Example: `ffufai --wordlists --feedback-loop --feedback-rounds 2 -u https://example.com/FUZZ -w wordlist.txt`

- `--targets-file`: Run against multiple URLs from a file (one URL per line).  
  Example: `ffufai --targets-file targets.txt -w wordlist.txt`

- `-u`: Specifies the target URL. This parameter is required and should include the FUZZ keyword.  
  Example: `ffufai -u https://example.com/FUZZ -w wordlist.txt`

- `-w`: Specifies the wordlist to use for fuzzing. This is a standard ffuf parameter.  
  Example: `ffufai -u https://example.com/FUZZ -w /path/to/wordlist.txt`

All other ffuf parameters can be used as normal. For a full list of ffuf parameters, refer to the ffuf documentation.

## Notes

- ffufai requires the FUZZ keyword to be at the end of the URL path for accurate extension suggestion. It will warn you if this is not the case.
- All ffuf parameters are passed through to ffuf, so you can use any ffuf option with ffufai.
- Provider priority defaults to Gemini → OpenAI → Anthropic → Groq → OpenRouter (override with `--providers`).
- Wappalyzer-style signature data lives in `config/tech_signatures.json` and can be extended.
- Wordlist catalog mappings live in `config/wordlist_catalog.json` and can be extended.

## Research Directions

Ideas to push AI-assisted fuzzing further:

- Hybrid wordlist generation that blends static knowledge bases with live target telemetry.
- Multi-model voting with confidence scoring and rate-aware routing.
- Passive asset graphing (JS maps, API schemas) feeding scoped fuzz queues.
- Active learning that promotes repeated high-signal discoveries into persistent dictionaries.

HUGE Shoutout to zlz, aka Sam Curry, for the amazing idea to make this project. He suggested it and 2 hours later, here it is :)    
<img width="744" alt="image" src="https://github.com/user-attachments/assets/9f914cc4-fe5f-4dbc-b7d9-548473ea2134">

## Troubleshooting

- If you encounter a "command not found" error, make sure you're using `python3 ffufai.py` or that you've correctly set up the symbolic link.
- If you get an API key error, ensure you've correctly set up your OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.
- If you see "import: command not found" errors, it means the script is being interpreted by the shell instead of Python. Make sure you're running it with `python3 ffufai.py` or that the shebang line at the top of the script is correct.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
