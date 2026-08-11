import json
import httpx
from dotenv import load_dotenv
import logging
import os
import asyncio

from app.models.types import ChatRequest, Message, ToolCall
from app.provider.error import ProviderError
from app.provider.provider import get_provider

logger = logging.getLogger("sab_agent_tool_call")

load_dotenv()

TOOLS = [
    {
        "type": "function",
        "function": {
            "description": "根据location获取天气信息，用户需要提供location",
            "name": "get_weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市或国家，例如：杭州，美国等"
                    },
                },
                "required": ["location"]
            },
        },
    },
]


async def chat_once(client: httpx.AsyncClient, messages: list[dict]) -> dict:
    api_key = os.environ["DEEPSEEK_API_KEY"]
    resp = await client.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-v4-flash",
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "stream": False,
        },
        timeout=30.0
    )
    resp.raise_for_status()
    return resp.json()


def get_weather(location: str) -> str:
    return json.dumps({"location": location, "temperature_c": 24, "condition": "sunny"})


def call(tool_call: dict) -> str:
    assert tool_call["type"] == "function"
    args = json.loads(tool_call["function"]["arguments"])
    if tool_call["function"]["name"] == "get_weather":
        return get_weather(args["location"])
    raise ValueError(f"unknown tool: {tool_call['function']['name']}")


def call2(tc: ToolCall) -> str:
    if tc.name == "get_weather":
        return get_weather(tc.arguments["location"])
    raise ValueError(f"unknown tool: {tc.name}")


def test_oai_tool_call_loop():
    async def _run():
        provider = get_provider("deepseek")
        assert provider
        messages = [
            Message(role="user", content="How's the weather in Shanghai?")]
        req = ChatRequest(model="deepseek-v4-flash",
                          messages=messages, stream=False, tools=TOOLS)
        try:
            response = await provider.generate(req=req)
            assert response.choices[0].finish_reason == "tool_calls"
            msg = response.choices[0].message
            assert msg.tool_calls

            messages.append(msg)

            for tc in msg.tool_calls:
                result = call2(tc)
                messages.append(
                    Message(role="tool", tool_call_id=tc.id, content=result))
            resp2 = await provider.generate(req)
            print(resp2)
            messages.append(resp2.choices[0].message)

        except ProviderError as e:
            print(e)
        # async with httpx.AsyncClient() as client:
        #     messages = [
        #         {"role": "user", "content": "How's the weather in Shanghai?"}]
        #     data = await chat_once(client, messages)
        #     assert data["choices"][0]["finish_reason"] == "tool_calls"
        #     msg = data["choices"][0]["message"]
        #     assert msg["tool_calls"], "模型应该发起工具调用"
        #     print(msg)

        #     messages.append(msg)
        #     for tc in msg["tool_calls"]:
        #         result = call(tc)
        #         messages.append(
        #             {"role": "tool", "tool_call_id": tc["id"], "content": result})
        #     # logger.info(json.dumps(messages, indent=2))
        #     data2 = await chat_once(client, messages)
        #     logger.info(json.dumps(data2, indent=2))

    asyncio.run(_run())
