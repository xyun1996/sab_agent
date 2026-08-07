from typing import Protocol
from .types import ChatRequest


class ChatModel(Protocol):
    async def generate(self, req: ChatRequest) -> str:
        ...
