from typing import Protocol


class ChatModel(Protocol):
    async def generate(self, messages: list[dict[str, str]]) -> str:
        ...
