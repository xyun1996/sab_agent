import pytest
import asyncio
import httpx
import os
from dotenv import load_dotenv
import logging
import json

logger = logging.getLogger("sab_agent")

load_dotenv()


def test_oai_create():
    async def _request():
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
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "hi"},
                    ],
                    "stream": False,
                },
                timeout=30.0
            )
            resp.raise_for_status()
            return resp.json()
    data = asyncio.run(_request())
    logger.info(json.dumps(data, indent=2))
