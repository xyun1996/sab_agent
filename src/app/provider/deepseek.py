import httpx
import os
import logging

from .error import RateLimitError, ProviderError, ProviderTimeout, ContextLengthError
from ..models.types import Message

logger = logging.getLogger("provider-deepseek")


class DeepSeekProvider():

    async def generate(self, messages: Message) -> str:
        try:
            system_prompt = "You are a helpful assistant."
            api_key = os.environ["DEEPSEEK_API_KEY"]
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "deepseek-v4-flash",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            messages.to_dict(),
                        ],
                        "stream": False,
                    },
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
