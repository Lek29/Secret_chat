import asyncio


async def main():
    reader, writer = await asyncio.open_connection('minechat.dvmn.org', 5000)

    try:
        while True:
            line = await reader.readline()

            message = line.decode().strip()

            if not message:
                break

            print(message)
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == '__main__':
    asyncio.run(main())