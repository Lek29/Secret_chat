import os

import anyio
import datetime
import json
import logging
import socket

import aiofiles
import gui
import asyncio

from async_timeout import timeout

from gui_from_registration import run_registration_process
from send_minechat import parse_args
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
watchdog_logger =logging.getLogger('watchdog')


async def get_valid_token(args):
    if args.token:
        return args.token

    load_dotenv()
    token = os.getenv('ACCOUNT_HASH')

    if not token:
        logger.info('Токен не найден. Запускаю регистрацию')
        await run_registration_process()

        load_dotenv(override=True)
        token = os.getenv('ACCOUNT_HASH')

    return token


async def run_reconnect_loop(args, messages_queue, sending_queue, status_updates_queue, watchdog_queue, save_history_queue):
    while True:
        try:
            await handle_connection(
                args.host, 5000, args.token,
                messages_queue, sending_queue, status_updates_queue,
                watchdog_queue, save_history_queue
            )
        except (ConnectionError, ExceptionGroup, socket.gaierror):
            logger.info("Потеря соединения. Повторная попытка через 2 сек...")
            await asyncio.sleep(2)


async def handle_connection(host, port, token, messages_queue, sending_queue,
                            status_updates_queue, watchdog_queue, save_history_queue):
    async with anyio.create_task_group() as tg:
        tg.start_soon(read_msgs, host, 5000, messages_queue, save_history_queue,
                      status_updates_queue, watchdog_queue)

        tg.start_soon(send_msgs, host, 5050, token, sending_queue, status_updates_queue, watchdog_queue)

        tg.start_soon(watch_for_connection, watchdog_queue)


async def watch_for_connection(watchdog_queue):
    check_timeout = 2.0

    while True:
        try:
            async with timeout(check_timeout) as cm:
                event_description = await watchdog_queue.get()
                timestamp = int(datetime.datetime.now().timestamp())

                watchdog_logger.info(f'[{timestamp}] Connection is alive. Source: {event_description}')
        except asyncio.TimeoutError:
            if cm.expired:
                timestamp = int(datetime.datetime.now().timestamp())
                watchdog_logger.info(f'[{timestamp}] {int(check_timeout)}s timeout is elapsed')
                raise ConnectionError("Watchdog detected connection timeout")


class InvalidToken(Exception):
    pass


async def send_msgs(host, port, token, sending_queue, status_updates_queue, watchdog_queue):
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    writer = None

    try:
        async with timeout(5.0):
            reader, writer = await asyncio.open_connection(host, port)

        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)


        await reader.readline()
        writer.write(f'{token}\n'.encode())
        await writer.drain()

        auth_answer = await reader.readline()
        account_info = json.loads(auth_answer.decode())

        if not account_info:
            raise InvalidToken("Передан неверный токен. Проверьте настройки.")

        watchdog_queue.put_nowait("Authorization done")

        nickname = account_info['nickname']
        logger.info(f"Выполнена авторизация. Пользователь {nickname}.")

        status_updates_queue.put_nowait(gui.NicknameReceived(nickname))

        while True:
            try:
                async with timeout(20) as cm:
                    message = await sending_queue.get()

                    clean_message = message.replace('\n', ' ')
                    writer.write(f"{clean_message}\n\n".encode())
                    await writer.drain()

                    watchdog_queue.put_nowait("Message sent")

                    logger.info(f"Сообщение '{clean_message}' улетело на сервер!")
            except asyncio.TimeoutError:
                writer.write(b'\n')
                await writer.drain()
                watchdog_logger.debug("Application-level PING sent")
    except (ConnectionError, asyncio.TimeoutError, socket.gaierror, OSError) as e:
        logger.error(f'Потеряно соединение с сервером: {e}')
        raise
    finally:
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
        if writer:
            writer.close()
            await writer.wait_closed()
        await asyncio.sleep(1)


async def save_messages(file_path, queue):
    async with aiofiles.open(file_path, mode='a', encoding='utf-8') as f:
        while True:
            message = await queue.get()
            await f.write(f'{message}\n')


async def load_history(filepath, messages_queue):
    try:
        async with aiofiles.open(filepath, mode='r', encoding='utf-8') as f:
            async for line in f:
                clean_line = str(line).strip()
                if clean_line:
                    messages_queue.put_nowait(clean_line)
    except FileNotFoundError:
        ...


async def read_msgs(host, port, gui_queue,save_queue, status_updates_queue, watchdog_queue):
    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    watchdog_queue.put_nowait("Prompt before auth")

    async with timeout(5.0):
        reader, writer = await asyncio.open_connection(host, port)

    try:
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)

        while True:
            async with timeout(10.0):
                line = await reader.readline()

            if not line:
                break

            watchdog_queue.put_nowait("New message in chat")
            message = line.decode().strip()
            gui_queue.put_nowait(message)
            save_queue.put_nowait(message)
    finally:
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
        if writer:
            writer.close()
            await writer.wait_closed()


async  def main():
    load_dotenv()

    logging.basicConfig(
        level=logging.DEBUG,
        format='{levelname} - {name} - {message}',
        style='{'
    )

    args = parse_args()

    messages_queue = asyncio.Queue()
    save_history_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    await load_history(args.history, messages_queue)

    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)

    args = parse_args()

    args.token = await get_valid_token(args)

    if not args.token:
        logger.error("Не удалось получить токен. Завершение работы.")
        return

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)

            tg.start_soon(run_reconnect_loop, args, messages_queue, sending_queue,
                          status_updates_queue, watchdog_queue, save_history_queue)

            tg.start_soon(save_messages, args.history, save_history_queue)
    except (gui.TkAppClosed, KeyboardInterrupt, ExceptionGroup, asyncio.exceptions.CancelledError):
        logger.info("Приложение завершено пользователем.")
    except Exception as e:
        logger.exception(f"Программа завершилась с критической ошибкой: {e}")


if __name__ == '__main__':
    asyncio.run(main())