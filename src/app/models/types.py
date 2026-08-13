from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass()
class ToolCall:
    id: str
    name: str
    arguments: dict
    raw_arguments: str


@dataclass()
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    reasoning: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


@dataclass()
class ChatRequest:
    model: str
    messages: list[Message]
    stream: bool | None = None
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None


@dataclass()
class Choice:
    index: int
    message: Message
#    logprobs:
    finish_reason: str


@dataclass
class PromptTokensDetails:
    cached_tokens: int


@dataclass
class CompletionTokensDetails:
    reasoning_tokens: int


@dataclass()
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: PromptTokensDetails
    completion_tokens_details: CompletionTokensDetails

    prompt_cache_hit_tokens: int
    prompt_cache_miss_tokens: int


@dataclass()
class ChatResponse:
    id: str
    model: str
    created: int
    choices: list[Choice]
    usage: Usage
    system_fingerprint: str | None


@dataclass()
class StreamEvent:
    kind: Literal["text", "reasoning", "done", "error"]

    text: str | None = None

    finish_reason: str | None = None

    usage: Usage | None = None
    message: Message | None = None
    error: str | None = None
