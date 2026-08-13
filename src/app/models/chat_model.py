from typing import AsyncIterator, Protocol
from .types import ChatRequest, ChatResponse, StreamEvent


class ChatModel(Protocol):
    async def generate(self, req: ChatRequest) -> ChatResponse:
        ...

    def generate_stream(self, req: ChatRequest) -> AsyncIterator[StreamEvent]:
        ...
