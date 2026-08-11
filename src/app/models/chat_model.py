from typing import Protocol
from .types import ChatRequest, ChatResponse


class ChatModel(Protocol):
    async def generate(self, req: ChatRequest) -> ChatResponse:
        ...
