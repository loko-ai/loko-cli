import asyncio
import json
import shutil
import sys
import os
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import docker
from loguru import logger

from loko_cli.business.docker.dockermanager import LokoDockerClient
from loko_cli.config.app_init import YAML
from loko_cli.dao.loko import FSLokoProjectDAO
from loko_cli.utils.path_utils import set_directory

base = Path.home() / "loko"


async def aprint(arg):
    logger.debug(arg['msg'])


async def plan(p: Path, company: str, push=True):
    dao = FSLokoProjectDAO()
    project = dao.get(p)
    client2 = docker.from_env()
    # Has a dockerfile
    client = LokoDockerClient()
    name = project.path.name
    has_local = (project.path / "Dockerfile").exists()
    if has_local:
        # Build a local extension
        MAIN_IMAGE = f"{company}/{project.path.name}"
        logger.info(f"Building {MAIN_IMAGE}")
        resp = await client.build(project.path, image=MAIN_IMAGE)
        if resp:
            logger.info("Build successful")

    services = {}

    ges = list(project.get_global_components())
    with set_directory(p):
        with TemporaryDirectory(dir=".") as d:
            d = Path(d)
            if ges:
                for ge in ges:
                    ge = base / "shared" / "extensions" / ge / "extensions" / "components.json"
                    rel = ge.relative_to(base)
                    dest = d / rel
                    dest.parent.mkdir(exist_ok=True, parents=True)
                    shutil.copyfile(ge, dest)
                    root = ge.parent.parent
                    config_path = root / "config.json"
                    if config_path.exists():
                        with config_path.open() as cf:
                            config = json.load(cf)
                            sides = config.get("side_containers", {})
                            for k, v in sides.items():
                                services[f"{root.name}_{k}"] = dict(image=v['image'])

                    GE_IMAGE_NAME = f"{company}/{root.name}"
                    logger.info(f"Building global extension: {GE_IMAGE_NAME}")
                    resp = await client.build(root, GE_IMAGE_NAME)
                    if resp:
                        logger.info("Build successful")
                    if push:
                        logger.info(f"Pushing {GE_IMAGE_NAME}")
                        """for line in client2.images.push(GE_IMAGE_NAME, stream=True):
                            msg = json.loads(line.decode())
                            if "error" in msg:
                                logger.error(msg)
                                sys.exit(1)
                            logger.debug(msg)"""

            # Build orchestrator
            ORCH_IMAGE = f"{company}/{name}_orchestrator"
            os.chdir(project.path)
            df = StringIO()
            if ges:
                df.write(f"""FROM lokoai/loko-runner:0.0.1-dev
RUN mkdir -p /root/loko/projects/{name}
COPY . /root/loko/projects/{name}/
COPY {d}/shared/ /home/loko/shared/
CMD python services.py""")
            else:
                df.write(f"""FROM lokoai/loko-runner:0.0.1-dev
    RUN mkdir -p /root/loko/projects/{name}
    COPY . /root/loko/projects/{name}/
    CMD python services.py""")

            df.seek(0)

            logger.info(f"Building orchestrator: {ORCH_IMAGE}")
            resp = await client.build(project.path, dockerfile=df, image=ORCH_IMAGE, log_collector=aprint)
            if resp:
                logger.info("Build successful")

            if push:
                if has_local:
                    logger.info(f"Pushing {MAIN_IMAGE}")

                    for line in client2.images.push(MAIN_IMAGE, stream=True):
                        msg = json.loads(line.decode())
                        if "error" in msg:
                            logger.error(msg)
                            sys.exit(1)
                        logger.debug(msg)
                    logger.info(f"Pushed")

                logger.info(f"Pushing {ORCH_IMAGE}")

                for line in client2.images.push(ORCH_IMAGE, stream=True):
                    msg = json.loads(line.decode())
                    if "error" in msg:
                        logger.error(msg)
                        sys.exit(1)
                    logger.debug(msg)
                logger.info(f"Pushed")

            # Generate docker-compose

            for ge in ges:
                services[ge] = dict(image=f"{company}/{ge}")

            services['orchestrator'] = dict(image=ORCH_IMAGE,
                                            command="python services.py",
                                            environment=dict(K8="true", PROJECT_PATH=f"/root/loko/projects/{name}"),
                                            ports=["8080:8080"])

            if has_local:
                services[name] = dict(image=MAIN_IMAGE)

            dc = dict(version="3.3", services=services)

            logger.info("Creating docker-compose")

            with open("docker-compose.yml", "w") as o:
                YAML.dump(dc, o)
            logger.info("Done!")

    await client.close()


if __name__ == '__main__':
    asyncio.run(plan(Path("/home/fulvio/loko/projects/faces"), "livetechprove", True))
