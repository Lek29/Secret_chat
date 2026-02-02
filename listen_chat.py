import asyncio
import logging
from datetime import datetime

import aiofiles
import configargparse
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


async def watch_chat(host, port, logfile):

    while True:
        writer = None
        try:
            reader, writer = await asyncio.open_connection(host, port)

            timestamp = datetime.now().strftime('%d.%m.%y %H:%M')
            msg = f'[{timestamp}] Установлено соединение\n'
            logger.info(msg.strip())

            async with aiofiles.open(logfile, mode='a', encoding='utf-8') as f:
                await f.write(msg)
                await f.flush()

            while True:
                encoded_message = await reader.readline()
                if not encoded_message:
                    break

                decoded_message = encoded_message.decode().strip()
                timestamp = datetime.now().strftime('%d.%m.%y %H:%M')
                formatted_log = f'[{timestamp}] {decoded_message}\n'

                async with aiofiles.open(logfile, mode='a', encoding='utf-8') as f:
                    await f.write(formatted_log)
                    await f.flush()

                logger.info(formatted_log.strip())

        except (ConnectionError, asyncio.TimeoutError, OSError):
            logger.error('Ошибка соединения. Повторная попытка через 5 секунд...')
            await asyncio.sleep(5)
        finally:
            if writer:
                writer.close()
                await writer.wait_closed()


def get_args():
    parser = configargparse.ArgParser(
        default_config_files=['.env'],
        ignore_unknown_config_file_keys=True
    )
    parser.add_argument(
        '--host',
        type=str,
        default='minechat.dvmn.org',
        help='Адрес сервера чата',
        env_var='MINECHAT_HOST'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Порт сервера чата',
        env_var='MINECHAT_PORT'
    )
    parser.add_argument(
        '--history',
        type=str,
        default='chat_logfile.txt',
        help='Путь к файлу логов ',
        env_var='MINECHAT_HISTORY'
    )

    return parser.parse_args()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='{levelname} - {name} - {message}',
        style='{'
    )

    load_dotenv()
    args = get_args()

    await watch_chat(args.host, args.port, args.history)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('\nСкрипт остановлен пользователем.')
