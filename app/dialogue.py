"""
Dialogue engine — sends the transcript to Claude and returns a reply.
Keeps per-call conversation history in memory (swap for Redis/DB for
multi-instance deployments).
"""

import logging
from anthropic import AsyncAnthropic

from app.config import settings

logger = logging.getLogger("voicebot.dialogue")

SYSTEM_PROMPT = """You are a voice assistant speaking with a caller on the phone.
Keep replies short (1-2 sentences), natural, and conversational — this is spoken aloud,
not read as text. Avoid lists, markdown, or long explanations. Ask one question at a time.
"""


class DialogueEngine:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.history: list[dict] = []

    async def get_response(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})

        response = await self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=self.history,
        )

        reply_text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        self.history.append({"role": "assistant", "content": reply_text})

        # Trim history so the call doesn't grow the context unbounded
        if len(self.history) > 20:
            self.history = self.history[-20:]

        return reply_text
