import asyncio
import json
import logging

import configargparse
from dotenv import load_dotenv

from registration import register
from tools import sanitize_text, save_token_to_env

logger = logging.getLogger(__name__)


async def submit_message(writer, message):
    cleaned_message = sanitize_text(message)

    if not cleaned_message:
        return

    writer.write(f'{cleaned_message}\n\n'.encode())

    await writer.drain()


def parse_args():
    parser = configargparse.ArgParser()
    parser.add_argument('--host', default='minechat.dvmn.org', env_var='MINECHAT_HOST')
    parser.add_argument('--port', default=5050, type=int, env_var='MINECHAT_WRITE_PORT')
    parser.add_argument('--token', env_var='ACCOUNT_HASH', help='Твой хэш аккаунта')
    parser.add_argument('--nickname', help='Имя пользователя для регистрации')
    parser.add_argument('--history', default='chat_history.txt', help='Путь к файлу истории чата')
    parser.add_argument('--message', help='Текст сообщения')
    return parser.parse_args()


async def authorise(reader, writer, token):
    await reader.readline()
    writer.write(f'{token}\n'.encode())
    await writer.drain()

    response = await reader.readline()
    decode_response = json.loads(response.decode())

    if decode_response is None:
        logger.error('Неизвестный токен. Проверьте его или зарегистрируйтесь заново.')
        return None

    logger.debug(f"Выполнена авторизация под ником: {decode_response['nickname']}")
    await reader.readline()
    return decode_response


async def handle_connection(args):
    token = args.token
    reader, writer = await asyncio.open_connection(args.host, args.port)

    try:
        if not token:
            logger.info('Токен не найден. Переходим в режим регистрации.')

            nickname = args.nickname or input('Введите никнейм для регистрации: ').strip()

            if not nickname:
                logger.error('Имя не может быть пустым.')
                return

            new_account = await register(reader, writer, nickname)
            token = new_account['account_hash']
            save_token_to_env(token)
            logger.info('Регистрация завершена! Хэш сохранен в .env.')

            if not args.message:
                print('Для отправки сообщения используйте флаг --message')
                return

        if not args.message:
            logger.error("Ошибка: нечего отправлять. Используйте --message 'текст'")
            return

        account_info = await authorise(reader, writer, token)
        if account_info:
            await submit_message(writer, args.message)
            logger.info('Сообщение успешно отправлено!')

    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='{levelname} - {name} - {message}',
        style='{'
    )

    load_dotenv()

    args = parse_args()

    await handle_connection(args)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
