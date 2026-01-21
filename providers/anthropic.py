# providers/anthropic.py

import json
import anthropic
from .base import AIProvider

SYSTEM_MSG = (
    "You are a security assistant helping with web fuzzing. "
    "Return only valid JSON. No prose."
)

class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)

    def get_extensions(self, url, headers, max_extensions):
        prompt = f"""
Given the following URL and HTTP headers, suggest the most likely file extensions
for fuzzing this endpoint.

Respond with valid JSON only.
Format:
{{"extensions": [".php", ".json", ".bak"]}}

Limit to at most {max_extensions} extensions.

URL: {url}
Headers: {headers}
"""

        msg = self.client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=500,
            temperature=0,
            system=SYSTEM_MSG,
            messages=[{"role": "user", "content": prompt}],
        )

        return json.loads(msg.content[0].text.strip())
