import json
from typing import AsyncIterator, Any

import httpx
import os
import logging

from .error import RateLimitError, ProviderError, ProviderTimeout, ContextLengthError
from ..models.types import ChatRequest, Message, ChatResponse, Usage, CompletionTokensDetails, PromptTokensDetails, Choice, ToolCall, StreamEvent

logger = logging.getLogger("provider-deepseek")


class DeepSeekProvider():
    async def generate(self, req: ChatRequest) -> ChatResponse:
        body = self._to_request_body(req)
        data = await self._post(body)
        response = self._parse_response(data)
        return response

    async def generate_stream(self, req: ChatRequest) -> AsyncIterator[StreamEvent]:
        body = self._to_request_body(req)
        api_key = os.environ["DEEPSEEK_API_KEY"]
        base_url = os.environ["DEEPSEEK_BASE_URL"]
        body["stream"] = True
        body["stream_options"] = {"include_usage": True}
        usage: Usage | None = None
        finish_reason: str | None = None
        tool_calls_acc: dict[int, dict] = {}
        message: Message | None = None
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    base_url+"/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=600.0
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line .startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            break

                        chunk = json.loads(payload)
                        if chunk.get("usage"):
                            usage = self._parse_usage(chunk.get("usage"))
                        if not chunk.get("choices"):
                            continue

                        choice = chunk.get("choices")[0]
                        delta = choice["delta"]
                        if delta.get("role"):
                            message = Message(delta.get("role"), "")
                        if delta.get("content"):
                            assert message is not None
                            message.content += delta["content"]
                            yield StreamEvent("text", text=delta["content"])
                        if delta.get("reasoning_content"):
                            assert message is not None
                            if message.reasoning is None:
                                message.reasoning = ""
                            message.reasoning += delta["reasoning_content"]
                            yield StreamEvent("reasoning", text=delta["reasoning_content"])
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                acc = tool_calls_acc.setdefault(
                                    tc["index"], {"id": "", "name": "", "arguments": ""})
                                acc["id"] = tc.get("id") or acc["id"]
                                acc["name"] = tc.get("function", {}).get(
                                    "name") or acc["name"]
                                acc["arguments"] += tc["function"].get(
                                    "arguments", "")
                        if choice.get("finish_reason"):
                            finish_reason = choice.get("finish_reason")
                    if finish_reason == "tool_calls":
                        tool_calls: list[ToolCall] = []
                        for idx in sorted(tool_calls_acc):
                            acc = tool_calls_acc[idx]
                            try:
                                args = json.loads(acc["arguments"])
                            except:
                                raise ProviderError(
                                    f"工具参数不是合法 JSON: {acc['arguments']!r}") from None
                            t = ToolCall(acc["id"], acc["name"],
                                         args, acc["arguments"])
                            tool_calls.append(t)
                        assert message is not None
                        message.tool_calls = tool_calls
                    yield StreamEvent("done", usage=usage, finish_reason=finish_reason, message=message)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                raise RateLimitError("请求频繁") from e
            if status == 402:
                raise ProviderError("余额不足") from e
            if status == 400:
                raise ProviderError(f"错误请求 {e}") from e
            raise ProviderError("未知错误") from e
        except httpx.TimeoutException as e:
            raise ProviderTimeout("请求超时") from e
        except httpx.TransportError as e:
            raise ProviderError(f"网络错误: {e}") from e

    def _to_request_body(self, req: ChatRequest) -> dict:
        body = {
            "model": req.model,
            "messages": self._to_oai_message(req.messages),
        }
        if req.tools is not None:
            body["tools"] = req.tools
            if req.tool_choice is not None:
                body["tool_choice"] = req.tool_choice
            else:
                body["tool_choice"] = "auto"
        return body

    def _to_oai_message(self, messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            d: dict[str, Any] = {"role": m.role, "content": m.content, }
            if m.tool_calls is not None and len(m.tool_calls) > 0:
                d["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.raw_arguments},
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id is not None:
                d["tool_call_id"] = m.tool_call_id
            out.append(d)
        return out

    def _parse_usage(self, data: dict) -> Usage:
        usage = Usage(
            prompt_tokens=data["prompt_tokens"],
            completion_tokens=data["completion_tokens"],
            total_tokens=data["total_tokens"],
            prompt_tokens_details=PromptTokensDetails(
                data["prompt_tokens_details"]["cached_tokens"]),
            completion_tokens_details=CompletionTokensDetails(
                data["completion_tokens_details"]["reasoning_tokens"]),
            prompt_cache_hit_tokens=data["prompt_cache_hit_tokens"],
            prompt_cache_miss_tokens=data["prompt_cache_miss_tokens"],
        )
        return usage

    def _parse_response(self, data: dict) -> ChatResponse:
        usage = self._parse_usage(data["usage"])

        choices: list[Choice] = []
        for c in data["choices"]:
            x: Choice = Choice(c["index"], self._parse_message(
                c["message"], c["finish_reason"]), c["finish_reason"])

            choices.append(x)

        out: ChatResponse = ChatResponse(
            id=data["id"],
            model=data["model"],
            created=data["created"],
            choices=choices,
            usage=usage,
            system_fingerprint=data.get("system_fingerprint"),
        )
        return out

    def _parse_message(self, data: dict, finish_reason: str) -> Message:
        out: Message = Message(
            data["role"],
            data["content"],
            "",
            self._parse_tool_calls(
                data["tool_calls"]) if finish_reason == "tool_calls" else None,
        )

        return out

    def _parse_tool_calls(self, data: dict) -> list[ToolCall]:
        out: list[ToolCall] = []
        for tc in data:
            try:
                args = json.loads(tc["function"]["arguments"])
            except:
                raise ProviderError(
                    f"工具参数不是合法 JSON: {tc['function']['arguments']!r}") from None
            t = ToolCall(tc["id"], tc["function"]["name"],
                         args, tc["function"]["arguments"])
            out.append(t)
        return out

    async def _post(self, body: dict) -> dict:
        api_key = os.environ["DEEPSEEK_API_KEY"]
        base_url = os.environ["DEEPSEEK_BASE_URL"]
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    base_url+"/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=30.0
                )
                resp.raise_for_status()
                data = resp.json()
                return data
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                raise RateLimitError("请求频繁") from e
            if status == 402:
                raise ProviderError("余额不足") from e
            if status == 400:
                raise ProviderError(f"错误请求 {e}") from e
            raise ProviderError("未知错误") from e
        except httpx.TimeoutException as e:
            raise ProviderTimeout("请求超时") from e
        except httpx.TransportError as e:
            raise ProviderError(f"网络错误: {e}") from e
