import pytest
import asyncio
from app.provider.provider import get_provider
from app.models.types import Message, ChatRequest
from app.provider.error import ProviderError


def test_chat_model():
    async def _run():
        provider = get_provider("deepseek")
        assert provider
        req = ChatRequest(model="deepseek-v4-flash",
                          messages=[Message(role="user", content="hi")])
        try:
            data = await provider.generate(req=req)
            return data
        except ProviderError as e:
            return e
    data = asyncio.run(_run())
    print(data)
