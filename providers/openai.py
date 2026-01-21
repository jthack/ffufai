# providers/openai.py

import json
from openai import OpenAI
from .base import AIProvider

SYSTEM_MSG = (
    "You are a security assistant helping with web fuzzing. "
    "Return only valid JSON. No prose."
)

class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

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

        resp = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        return json.loads(resp.choices[0].message.content.strip())
