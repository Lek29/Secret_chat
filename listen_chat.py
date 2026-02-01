import asyncio
import aiofiles
import configargparse

from datetime import datetime


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
        env_var='MINICHAT_PORT'
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
    args = get_args()
    host = args.host
    port = args.port
    logfile = args.history


    while True:
        writer = None
        try:
            reader, writer = await asyncio.open_connection(host, port)

            async with aiofiles.open(logfile, mode='a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%d.%m.%y %H:%M')
                start_msg = f"[{timestamp}] Установлено соединение\n"

                print(start_msg)

                await f.write(start_msg)
                await f.flush()

            while True:
                encoded_message = await reader.readline()

                if not encoded_message:
                    break

                decoded_message = encoded_message.decode().strip()
                timestamp = datetime.now().strftime('%d.%m.%y %H:%M')
                formatted_log = f"[{timestamp}] {decoded_message}\n"

                async with aiofiles.open(logfile, mode='a', encoding='utf-8') as f:
                    await f.write(formatted_log)
                    await f.flush()

                print(formatted_log.strip())

        except (ConnectionError, asyncio.TimeoutError, OSError):
            await asyncio.sleep(5)
        finally:
            if writer:
                writer.close()
                await writer.wait_closed()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nСкрипт остановлен пользователем.")