import asyncio
import logging
import configargparse

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='{levelname} - {name} - {message}'
)
logger = logging.getLogger(__file__)

def parse_args():
    parser = configargparse.ArgParser()
    parser.add_argument('--host', default='minechat.dvmn.org', env_var='MINECHAT_HOST')
    parser.add_argument('--port', default=5050, type=int, env_var='MINECHAT_WRITE_PORT')
    parser.add_argument('--token', env_var='ACCOUNT_HASH', help='Твой хэш аккаунта')
    parser.add_argument('--message',  help='Текст сообщения')
    return parser.parse_args()

async def submit_message(host, port, token, message):
    logger.debug(f"Connecting to {host}:{port}")
    reader, writer = await asyncio.open_connection(host, port)

    try:
        await reader.readline()

        writer.write(f'{token}\n'.encode())
        await writer.drain()

        auth_response = await reader.readline()
        logger.debug(f'Ответ сервера: {auth_response.decode().strip()}')

        prepared_message = message.replace('\n', ' ')
        writer.write(f'{prepared_message}\n\n'.encode())
        await writer.drain()
        logger.info("Сообщение отправлено!")

    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    args = parse_args()
    logger.debug(f"Использован токен: {args.token}")
    if args.token is None:
        logger.error("ОШИБКА: Токен не найден! Проверьте файл .env или передайте через --token")
        return

    await submit_message(args.host, args.port, args.token, args.message)


if __name__ == '__main__':
    asyncio.run(main())
