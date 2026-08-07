import json
import httpx
from dotenv import load_dotenv
import logging
import os
import asyncio

logger = logging.getLogger("sab_agent_prefix")

load_dotenv()

api_key = os.environ["DEEPSEEK_API_KEY"]


async def chat_once(client: httpx.AsyncClient, messages: list[dict], stop=None) -> dict:
    body = {
        "model": "deepseek-v4-flash",
        "messages": messages,
    }
    if stop:
        body["stop"] = stop
    resp = await client.post(
        "https://api.deepseek.com/beta/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=270.0
    )
    resp.raise_for_status()
    return resp.json()


def test_prefix_content():
    async def _run():
        async with httpx.AsyncClient() as client:
            messages = [
                {"role": "user", "content": "请写一个快速排序代码，只要代码不要解释"},
                {"role": "assistant", "content": "```python\n", "prefix": True},
            ]
            data = await chat_once(client, messages, stop=["```"])
            content = data["choices"][0]["message"]["content"]
            logger.info(content)

    asyncio.run(_run())


def test_reasoning_continuation():
    async def _run():
        async with httpx.AsyncClient() as client:
            q = "懂一些ai技术，如何不通过工作，在网上赚到100块钱？请先思考在回答。"
            data1 = await chat_once(client, [{"role": "user", "content": q}])
            msg1 = data1["choices"][0]["message"]
            reasoning1 = msg1.get("reasoning_content") or ""
            print("第一轮思考链")
            # logger.info(reasoning1)

            truncated = reasoning1[:len(reasoning1)//2]
            inject_a = (
                "用户懂AI但没本金，最稳的路径是出卖AI技能换钱。"
                "我决定推荐他去猪八戒/闲鱼接单：AI修图、写文案、做PPT，"
                "一单30-50元，接3单就够100元。"
            )
            inject_b = (
                "用户懂AI但没本金，边际成本为零的路径是卖数字产品。"
                "我决定推荐他用AI批量生成Prompt合集/简历模板，"
                "定价9.9元挂到闲鱼和小红书，卖11份就够100元。"
            )
            message2 = [
                {"role": "user", "content": q},
                {
                    "role": "assistant",
                    "content": "答案是:",
                    "prefix": True,
                    "reasoning_content": inject_b,
                },
            ]
            data2 = await chat_once(client, message2)
            msg2 = data2["choices"][0]["message"]

            logger.info("第二轮思考链")
            logger.info(msg2.get("reasoning_content"))
            logger.info("最终回答")
            logger.info(msg2.get("content"))
    asyncio.run(_run())
