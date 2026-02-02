import json
import asyncio
import logging

from tools import sanitize_text

logger = logging.getLogger(__file__)

async def register(host, port, nickname):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        await reader.readline()
        writer.write('\n'.encode())
        await writer.drain()

        await reader.readline()

        safe_nickname = sanitize_text(nickname)
        writer.write(f'{safe_nickname}\n'.encode())
        await writer.drain()

        response = await reader.readline()
        decoded_response = response.decode().strip()

        return json.loads(decoded_response)
    finally:
        writer.close()
        await writer.wait_closed()
