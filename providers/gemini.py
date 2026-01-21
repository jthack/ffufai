import json
from google import genai
from google.genai import types
from .base import AIProvider

SYSTEM_MSG = (
    "You are a security assistant helping with web fuzzing. "
    "Return only valid JSON. No prose."
)

class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)

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

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_MSG,
            response_mime_type="application/json",
            temperature=0.0
        )

        # Updated based on your diagnostic output
        # Prioritizing 2.0 Flash as it is fast and available to you
        model_candidates = [
            "gemini-2.0-flash", 
            "gemini-2.5-flash", 
            "gemini-flash-latest"
        ]

        for model_name in model_candidates:
            try:
                resp = self.client.models.generate_content(
                    model=model_name,
                    contents=[
                        {"role": "user", "parts": [{"text": prompt}]},
                    ],
                    config=config
                )
                return json.loads(resp.text.strip())

            except Exception as e:
                # If it's the last candidate, we need to handle the error
                if model_name == model_candidates[-1]:
                    print(f"DEBUG: All model attempts failed. Last error: {e}")
                    
                    # SELF-DIAGNOSIS (Kept for future safety)
                    if "404" in str(e):
                        print("\n🔍 DIAGNOSTIC: Fetching list of available models for your key...")
                        try:
                            for m in self.client.models.list():
                                if "generateContent" in (m.supported_actions or []):
                                    print(f" - {m.name}")
                        except Exception as list_err:
                            print(f"   Could not list models: {list_err}")
                        print("\n👉 Please update the 'model=' line in gemini.py with one of the above.\n")

                    return {"extensions": [".php", ".html", ".json"]}
                else:
                    continue