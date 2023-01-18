import asyncio

import aiodocker
import docker


async def main():
    client = docker.from_env()
    # client.login(username="livetechprove", password="lokolokoloko")
    # print(await client.auth(livetechprove="lokolokoloko"))

    for line in client.images.push("localhost:5000/hello_data", stream=True):
        print(line)
    for line in client.images.push("localhost:5000/hello", stream=True):
        print(line)

    # print("Pushed")
    client.close()


async def reg():
    client = aiodocker.Docker()
    registry = docker.utils.find_registry("localhost:5000")
    print(registry)


if __name__ == '__main__':
    asyncio.run(reg())
