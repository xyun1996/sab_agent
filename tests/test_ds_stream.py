import asyncio
import json
from app.models.types import ChatRequest, Message, StreamEvent, ToolCall
from app.provider.provider import get_provider


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


def test_stream():
    async def _run():

        provider = get_provider("deepseek")
        assert provider
        quest = Message(role="user", content="上海天气")
        history_messages = [quest]
        req = ChatRequest(model="deepseek-v4-flash",
                          messages=history_messages, tools=TOOLS)
        content = ""
        reasoning = ""
        for _ in range(2):
            async for ev in provider.generate_stream(req=req):
                if ev.kind == "text":
                    if ev.text is not None:
                        if content == "":
                            print("【回答】")
                        content += ev.text
                        print(ev.text, end="", flush=True)
                elif ev.kind == "reasoning":
                    if ev.text is not None:
                        if reasoning == "":
                            print("【思考】")
                        print(ev.text, end="", flush=True)
                        reasoning += ev.text
                elif ev.kind == "done":
                    if ev.message is None:
                        break
                    history_messages.append(ev.message)
                    if ev.finish_reason == "tool_calls":
                        if ev.message.tool_calls is not None:
                            for tc in ev.message.tool_calls:
                                result = call(tc=tc)
                                history_messages.append(
                                    Message("tool", tool_call_id=tc.id, content=result))
                    elif ev.finish_reason == "stop":
                        break
            # if reasoning:
            #     print("【思考】", reasoning)
            # if content:
            #     print("【回答】", content)
            reasoning = ""
            content = ""
            req.messages = history_messages
    asyncio.run(_run())
