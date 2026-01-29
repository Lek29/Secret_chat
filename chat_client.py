import asyncio
import aiofiles

from datetime import datetime


async def main():
    host = 'minechat.dvmn.org'
    port = 5000
    logfile = 'chat_logfile.txt'

    writer = None

    while True:
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