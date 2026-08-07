import asyncio
from ds import create_client, stream_chat


def test_stream():
    async def _run():

        client = create_client()
        x = await stream_chat(client, [{"role": "user", "content": "用一句话介绍上海"}])

    asyncio.run(_run())
