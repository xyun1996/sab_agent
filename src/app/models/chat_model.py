from typing import Protocol
from .types import Message


class ChatModel(Protocol):
    async def generate(self, messages: Message) -> str:
        ...
