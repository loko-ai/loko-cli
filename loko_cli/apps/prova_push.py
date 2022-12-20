import asyncio

import aiodocker
import docker


async def main():
    client = docker.from_env()
    client.login(username="livetechprove", password="lokolokoloko")
    # print(await client.auth(livetechprove="lokolokoloko"))

    client.images.push("livetechprove/hello_data")
    client.images.push("livetechprove/hello")

    # print("Pushed")
    client.close()


if __name__ == '__main__':
    asyncio.run(main())
