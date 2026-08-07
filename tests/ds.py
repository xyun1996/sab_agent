import json
import httpx
from dotenv import load_dotenv
import logging
import os
import asyncio

load_dotenv()

api_key = os.environ["DEEPSEEK_API_KEY"]

logger = logging.getLogger("sab_agent_ds")


def create_client() -> httpx.AsyncClient:
    return httpx.AsyncClient()


async def stream_chat(client: httpx.AsyncClient, messages: list[dict], tools=None) -> dict:
    body = {
        "model": "deepseek-v4-flash",
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    saw_done = False
    reasoning = False

    async with client.stream(
        "POST",
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=600,
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                saw_done = True
                break

            chunk = json.loads(payload)
            if chunk["delta"]["role"] == "assistant":
                reasoning = True

            if reasoning:
                print(chunk["delta"]["resasoning_content"])
                # logger.info(payload)

                # return resp.json()
    return {}
