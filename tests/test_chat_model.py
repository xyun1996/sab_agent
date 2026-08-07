import pytest
import asyncio
from app.provider.provider import get_provider
from app.models.types import Message


def test_chat_model():
    async def _run():
        provider = get_provider("deepseek")
        assert provider
        msg = Message(role="user", content="hi")
        data = await provider.generate(msg)
        return data
    data = asyncio.run(_run())
    print(data)
