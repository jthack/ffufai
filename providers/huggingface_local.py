# providers/huggingface_local.py

import json
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from .base import AIProvider

SYSTEM_MSG = (
    "You are a security assistant helping with web fuzzing. "
    "Return only valid JSON. No prose."
)

class HuggingFaceLocalProvider(AIProvider):
    name = "huggingface"

    def __init__(self):
        model_name = "Qwen/Qwen2.5-1.5B-Instruct"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
        )

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

        messages = [
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": prompt},
        ]

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        output = self.model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=False,
        )

        output = output[:, inputs["input_ids"].shape[1]:]
        raw = self.tokenizer.decode(output[0], skip_special_tokens=True)

        return json.loads(raw.strip())
