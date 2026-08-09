import httpx
import os
import logging

from .error import RateLimitError, ProviderError, ProviderTimeout, ContextLengthError
from ..models.types import ChatRequest, Message

logger = logging.getLogger("provider-deepseek")


class DeepSeekProvider():
    async def generate(self, req: ChatRequest) -> str:
        body = self._to_request_body(req)
        data = await self._post(body)
        return data

    def _to_request_body(self, req: ChatRequest) -> dict:
        body = {
            "model": req.model,
            "messages": self._to_oai_message(req.messages),
        }
        return body

    def _to_oai_message(self, messages: list[Message]) -> list[dict]:
        # 'tool_calls':
        # [{'index': 0, 'id': 'call_00_OahgwZn5dPZfCaIP2c4n5742', '
        # type': 'function', 'function': {'name': 'get_weather', 'arguments': '{"location": "Shanghai"}'}
        out: list[dict] = []
        for m in messages:
            d = {"role": m.role, "content": m.content}
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

    async def _post(self, body: dict) -> str:
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
                content = data["choices"][0]["message"]["content"]
                if content is None:
                    raise ProviderError("模型未返回文本内容")
                return content
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
