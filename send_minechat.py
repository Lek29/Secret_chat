import asyncio
import logging
import configargparse
import json

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='{levelname} - {name} - {message}',
    style='{'
)
logger = logging.getLogger(__file__)


def sanitize_text(text):
    if not text:
        return ''
    return text.replace('\n', '').strip()


def parse_args():
    parser = configargparse.ArgParser()
    parser.add_argument('--host', default='minechat.dvmn.org', env_var='MINECHAT_HOST')
    parser.add_argument('--port', default=5050, type=int, env_var='MINECHAT_WRITE_PORT')
    parser.add_argument('--token', env_var='ACCOUNT_HASH', help='Твой хэш аккаунта')
    parser.add_argument('--message', required=True, help='Текст сообщения')
    return parser.parse_args()


async def authorise(reader, writer, token):
    await reader.readline()
    writer.write(f'{token}\n'.encode())
    await writer.drain()

    response = await reader.readline()
    decode_response = json.loads(response.decode())

    if decode_response is None:
        logger.error("Неизвестный токен. Проверьте его или зарегистрируйтесь заново.")
        return None

    logger.debug(f"Выполнена авторизация под ником: {decode_response['nickname']}")
    await reader.readline()
    return decode_response


async def register(reader, writer, nickname):
    await reader.readline()
    writer.write('\n'.encode())
    await writer.drain()

    await reader.readline()
    sanitized_nickname = sanitize_text(nickname)
    writer.write(f'{sanitized_nickname}\n'.encode())
    await writer.drain()

    response = await reader.readline()

    return json.loads(response.decode())


async def main():
    args = parse_args()

    if not args.message:
        logger.error("Сообщение не введено! Используйте флаг --message")
        return

    reader, writer = await asyncio.open_connection(args.host, args.port)

    try:
        if not args.token:
            logger.info("Токен не указан. Запустите скрипт регистрации.")
            return

        account_info = await authorise(reader, writer, args.token)

        if account_info:
            message = sanitize_text(args.message)
            writer.write(f'{message}\n\n'.encode())
            await writer.drain()
            logger.info(f"Сообщение от имени {account_info['nickname']} отправлено!")
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == '__main__':
    asyncio.run(main())
