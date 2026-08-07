import httpx
import os
import logging
from ..models.types import Message

logger = logging.getLogger("provider-deepseek")


class DeepSeekProvider():

    async def generate(self, messages: Message) -> str:
        system_prompt = "You are a helpful assistant."
        api_key = os.environ["DEEPSEEK_API_KEY"]
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-v4-flash",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        messages.to_dict(),
                    ],
                    "stream": False,
                },
                timeout=30.0
            )
            resp.raise_for_status()
            return resp.json()
