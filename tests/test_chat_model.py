import pytest
import asyncio
from app.provider.provider import get_provider
from app.models.types import Message
from app.provider.error import ProviderError


def test_chat_model():
    async def _run():
        provider = get_provider("deepseek")
        assert provider
        msg = Message(role="user", content="hi")
        try:
            data = await provider.generate(msg)
            return data
        except ProviderError as e:
            return e
    data = asyncio.run(_run())
    print(data)
