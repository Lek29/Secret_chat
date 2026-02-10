import tkinter as tk
from tkinter import messagebox
import asyncio
import  json

import aiofiles


async def register_at_server(host, port, nickname):
    reader, writer = await asyncio.open_connection(host, port)

    try:
        await reader.readline()
        writer.write(b'\n')
        await writer.drain()

        await reader.readline()

        writer.write(f"{nickname}\n".encode())
        await writer.drain()

        response = await reader.readline()

        return json.loads(response.decode())

    finally:
        writer.close()
        await writer.wait_closed()


def create_registration_ui(registration_queue):
    root = tk.Tk()
    root.title('Регистратор')
    root.geometry('300x200')

    label = tk.Label(root, text='Введи имя')
    label.pack(pady=20)

    nickname_entry = tk.Entry(root)
    nickname_entry.pack(pady=5)


    def on_button_click():
        nickname = nickname_entry.get()
        if nickname:
            registration_queue.put_nowait(nickname)
        else:
            messagebox.showinfo("Ошибка", "Ник пустой!")


    tk.Button(root, text="Зарегистрироваться", command=on_button_click).pack(pady=20)

    return root


async def run_registration_process():
    host = 'minechat.dvmn.org'
    port = 5050
    registration_queue = asyncio.Queue()

    root = create_registration_ui(registration_queue)

    while True:
        root.update()
        try:
            nickname = registration_queue.get_nowait()
            account = await register_at_server(host, port, nickname)
            token = account['account_hash']

            async with aiofiles.open('.env', mode='a', encoding='utf-8') as f:
                await f.write(f'\nACCOUNT_HASH={token}\n')
            messagebox.showinfo("Успех!", f"Регистрация прошла! Токен сохранен.\nТвой ник: {account['nickname']}")
            break
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.01)
        except tk.TclError:
            break
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось зарегистрироваться: {e}")
            break

    root.destroy()


if __name__ == "__main__":
    asyncio.run(run_registration_process())