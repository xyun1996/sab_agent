from dataclasses import dataclass, field
from typing import Any, Literal


class ToolCall:
    id: str
    name: str
    arguments: dict
    raw_arguments: str


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


@dataclass()
class ChatRequest:
    model: str
    messages: list[Message]
    stream: bool | None = None
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None
