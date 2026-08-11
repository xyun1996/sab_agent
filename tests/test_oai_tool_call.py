import json
from dotenv import load_dotenv
import asyncio

from app.models.types import ChatRequest, Message, ToolCall
from app.provider.error import ProviderError
from app.provider.provider import get_provider


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


def get_weather(location: str) -> str:
    return json.dumps({"location": location, "temperature_c": 24, "condition": "sunny"})


def call(tc: ToolCall) -> str:
    print(f"工具调用:{tc.name}")
    if tc.name == "get_weather":
        return get_weather(tc.arguments["location"])
    raise ValueError(f"unknown tool: {tc.name}")


def test_oai_tool_call_loop():
    async def _run():
        provider = get_provider("deepseek")
        assert provider
        quest = Message(role="user", content="How's the weather in Shanghai?")
        history_messages = [quest]
        max_iterations = 5
        for _ in range(max_iterations):
            try:
                req = ChatRequest(model="deepseek-v4-flash",
                                  messages=history_messages, stream=False, tools=TOOLS)
                response = await provider.generate(req=req)
                msg = response.choices[0].message

                history_messages.append(msg)

                if response.choices[0].finish_reason == "tool_calls":
                    if msg.tool_calls is not None:
                        for tc in msg.tool_calls:
                            result = call(tc)
                            history_messages.append(
                                Message(role="tool", tool_call_id=tc.id, content=result))
                else:
                    print(msg.content)
                if response.choices[0].finish_reason == "stop":
                    break

            except ProviderError as e:
                print(e)
                break

    asyncio.run(_run())
