import asyncio
import shutil
from io import StringIO
from pathlib import Path
from tempfile import mkdtemp

from docker import DockerClient
from docker.utils import tar

from loko_cli.business.docker.dockermanager import LokoDockerClient

from loko_cli.business.deployment.appliers.appliers import Applier
from loko_cli.model.plan import Plan
import os


class DockerComposeApplier(Applier):
    def __init__(self, project_company, client: LokoDockerClient, registry=None, build=True, push=True):
        self.push = push
        self.build = build
        self.client = client
        self.project_company = project_company
        self.docker = DockerClient.from_env()

        self.registry = registry or "local"

    async def apply(self, plan: Plan):

        DATA_NAME = f"{plan.namespace}_data"
        DATA_IMAGE = f"{self.project_company}/{DATA_NAME}"
        GW = f"{plan.namespace}_gateway"
        ORCH = f"{plan.namespace}_orchestrator"

        RULES = []
        RULES.extend([{"name": "orchestrator", "host": ORCH, "port": 8888,
                       "type": "orchestrator", "scan": True},
                      {"name": "predictor", "host": "predictor", "port": 8080,
                       "type": "predictor"}])

        if plan.local_extensions:
            MAIN_NAME = f"{plan.namespace}_main"
            MAIN_IMAGE = f"{self.project_company}/{plan.namespace}"

            RULES.append({"name": plan.path.name, "host": MAIN_NAME, "port": 8080,
                          "type": "custom"})
            resp = await self.client.build(plan.path, image=MAIN_IMAGE)
            if not resp:
                raise Exception("Error in building")
            await self.client.run(name=MAIN_NAME, image=MAIN_IMAGE, autoremove=True, network="loko")

        for g in plan.global_extensions:
            print(g)

        await self._build_data_image(plan, DATA_IMAGE)

        if self.push:
            self._push(plan)

        # await self._create_data(DATA_NAME, image=DATA_IMAGE)
        # await self._run_gateway(plan, GW, RULES)

        # await self._run_orchestrator(plan, name=ORCH, gateway=GW, data=DATA_NAME)

    async def _build_data_image(self, plan: Plan, image_name):
        # MANUAL TEMP DIR INSTEAD OF TEMPDIR CONTEXT MANAGER
        td = mkdtemp(dir=plan.path)
        try:
            df = StringIO()
            df.write("FROM alpine\n")
            df.write(f"COPY loko.project /root/loko/projects/{plan.path.name}/\n")

            # ADD REQUIRED RESOURCES
            loko_path = plan.path.parent.parent

            if plan.resources:

                df.write(f"COPY {Path(td).name}/data /root/loko/data\n")
                for resource in plan.resources:
                    fname = loko_path / os.path.join(*resource.split(os.sep)[1:])
                    rpath = Path(td) / "data/"
                    rpath.mkdir(parents=True, exist_ok=True)
                    shutil.copy(fname, rpath)
            if plan.local_extensions:
                df.write(f"COPY extensions/ /root/loko/projects/{plan.path.name}/extensions/\n")
            context = tar(
                plan.path.resolve(), dockerfile=("Dockerfile", df.getvalue()),
                gzip=True
            )

            ## BUILD DATA CONTAINER
            resp = await self.client.client.images.build(fileobj=context, encoding="UTF-8", tag=image_name)
            return resp
        finally:
            # Cancellare la directory anche se va in eccezione
            shutil.rmtree(td)

    async def _create_data(self, name, image):
        hc = dict(Binds=["/root/loko/"])

        # CREATE VOLUME FROM DATA CONTAINER IMAGE
        await self.client.client.containers.create_or_replace(name=name,
                                                              config=dict(Image=image, HostConfig=hc))

    async def _run_orchestrator(self, plan: Plan, name, gateway, data):
        orch = await self.client.client.containers.create_or_replace(name=name,
                                                                     config=dict(
                                                                         Image="lokoai/loko-orchestrator:0.0.4-dev",
                                                                         Env=[f"GATEWAY=http://{gateway}:8080"],
                                                                         HostConfig=dict(VolumesFrom=[data], Binds=[
                                                                             "/var/run/docker.sock:/var/run/docker.sock"],
                                                                                         NetworkMode="loko",
                                                                                         AutoRemove=True),
                                                                         Cmd=["python", "services.py"]))
        await orch.start()

    async def _run_gateway(self, plan: Plan, name, rules):
        await self.client.run(name=name, image=plan.gateway.image, environment=dict(AUTOSCAN=False, RULES=rules),
                              ports=plan.gateway.ports, autoremove=True,
                              network="loko")

    async def build(self, dcp: Plan):

        for el in dcp.services:

            if not "lokoai" in el.image:
                # print(el.__dict__())
                await self.client.build("/home/alejandro/loko/projects/hello_ale")

    def _push(self, plan):
        DATA_NAME = f"{plan.namespace}_data"
        DATA_IMAGE = f"{self.project_company}/{DATA_NAME}"
        for line in self.docker.images.push(DATA_IMAGE, stream=True):
            print(line)


if __name__ == "__main__":
    async def main():
        pass


    asyncio.run(main())
