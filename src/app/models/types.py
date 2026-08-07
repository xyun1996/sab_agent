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
    stream: bool | None
