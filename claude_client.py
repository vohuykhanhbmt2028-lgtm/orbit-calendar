# Thin wrapper around the Anthropic client.

import os
from anthropic import Anthropic
from dotenv import load_dotenv

from prompts import SYSTEM_PROMPT_VARIANTS, SYSTEM_PROMPT_CHAT

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"


class ClaudeClient:
    def __init__(self):
        key = os.getenv('CLAUDE_API_KEY')
        if not key:
            raise RuntimeError("CLAUDE_API_KEY not found in .env file")
        self.client = Anthropic(api_key=key)

    def build_variants(self, fixed, flexible, anchors, other):
        prompt = SYSTEM_PROMPT_VARIANTS.format(
            fixed=fixed, flexible=flexible, anchors=anchors, other=other)
        resp = self.client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=prompt,
            messages=[{"role": "user", "content": "Generate 4 schedule variants now."}],
        )
        return resp.content[0].text

    def chat_reply(self, messages):
        resp = self.client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=SYSTEM_PROMPT_CHAT,
            messages=messages,
        )
        return resp.content[0].text

    def chat_greeting(self):
        trigger = {"role": "user", "content": "Hi, I'd like to build my weekly schedule."}
        resp = self.client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=SYSTEM_PROMPT_CHAT,
            messages=[trigger],
        )
        return trigger, resp.content[0].text.strip()