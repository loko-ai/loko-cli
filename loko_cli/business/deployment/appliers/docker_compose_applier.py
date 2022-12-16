import asyncio
from pathlib import Path

from loko_tools.business.docker.dockermanager import LokoDockerClient
from loko_tools.model.docker_service_model import DockerService
from loko_tools.model.plan_model import DockerComposePlan


class Applier:

    def apply(self, plan):
        pass

    def validate(self, plan):
        pass

    def destroy(self, plan):
        pass

    def build(self):
        pass


class DockerComposeApplier(Applier):
    def __init__(self, client: LokoDockerClient, registry=None, build=True, push=True):
        self.push = push
        self.build = build
        self.client = client
        self.registry = registry or "local"

    async def apply(self, plan_or_plan_path):
        if isinstance(plan_or_plan_path, DockerComposePlan):
            plan: DockerComposePlan = plan_or_plan_path

        else:
            plan = DockerComposePlan()
            plan.load(plan_or_plan_path)

        if self.build:
            # Builda. Da considera anche data/volumi
            self.build_images(plan)
        if self.push:
            self.push_images(plan)

        for ds in plan.services:
            await self.client.run(ds.name, **ds.get_body())

    async def build(self, dcp: DockerComposePlan):

        for el in dcp.services:

            if not "lokoai" in el.image:
                # print(el.__dict__())
                await self.client.build("/home/alejandro/loko/projects/hello_ale")

    def push_images(self, dcp: DockerComposePlan):
        for el in dcp.services:
            print(el.name, el.image)

    def validate(self, plan):
        pass

    async def destroy(self, plan_or_plan_path: Path):
        if not isinstance(plan_or_plan_path, DockerComposePlan):
            plan_or_plan_path = DockerComposePlan(plan_or_plan_path)

        for ds in plan_or_plan_path.services:
            await self.client.kill(ds.name)


if __name__ == "__main__":
    async def main():
        client = LokoDockerClient()
        plan = DockerComposePlan()
        plan.load(Path(
            "/media/alejandro/DATA/workspace/livetech/loko-tools/loko_tools/business/deployment/dist/docker_compose/0.1/docker-compose.yml"))

        applier = DockerComposeApplier(client, build=True)
        # await applier.apply(plan)
        await applier.build_images(plan)

        # await applier.destroy(plan)

        await client.close()


    asyncio.run(main())
