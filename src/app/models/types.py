from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None

    def to_dict(self) -> dict:
        d: dict = {"role": self.role, "content": self.content}
        return d


@dataclass()
class ChatRequest:
    model: str
    messages: list[Message]
    stream: bool | None = None

    def to_messages_dict(self) -> list[dict]:
        out: list[dict] = []
        for msg in self.messages:
            out.append(msg.to_dict())
        return out
