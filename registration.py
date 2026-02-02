import json
import asyncio
import logging


logger = logging.getLogger(__file__)

async def register(host, port, nickname):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        await reader.readline()

        writer.write('\n'.encode())
        await writer.drain()

        await reader.readline()

        writer.write(f'{nickname}\n'.encode())
        await writer.drain()

        response = await reader.readline()
        decoded_response = response.decode().strip()

        return json.loads(decoded_response)
    finally:
        writer.close()
        await writer.wait_closed()


def save_token_to_env(token):
    with open('.env', 'a', encoding='utf-8') as f:
        f.write(f'\nACCOUNT_HASH={token}\n')
    logger.info(f"Токен сохранен в файл .env")
