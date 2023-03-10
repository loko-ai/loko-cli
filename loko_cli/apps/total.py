import asyncio
import json
import os
import shutil
import sys
import time
import re
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import docker
from docker.utils import tar
from loguru import logger
from tenacity import retry

from loko_cli.business.deployment.cloud.ec2 import EC2Manager
from loko_cli.business.docker.dockermanager import LokoDockerClient
from loko_cli.config.app_init import YAML
from loko_cli.dao.loko import FSLokoProjectDAO
from loko_cli.utils.path_utils import set_directory

pred_env = ["IMGS_MAPPING=\"{'predictor_base': 'lokoai/ds4biz-predictor-base:0.0.3-dev'}\"",
            "GATEWAY_URL=http://gateway:8080", "NETWORK_NAME=loko"]
core_images = dict(predictor=dict(image="lokoai/ds4biz-predictor-dm:0.0.4-dev", environment=pred_env,
                                  volumes=["/var/run/docker.sock:/var/run/docker.sock"]))


def prepare_docker_ignore(path):
    dockerignore = os.path.join(path, '.dockerignore')
    exclude = None
    if os.path.exists(dockerignore):
        with open(dockerignore) as f:
            exclude = list(filter(
                lambda x: x != '' and x[0] != '#',
                [l.strip() for l in f.read().splitlines()]
            ))
    return exclude


class PlanDAO:
    def __init__(self, path: Path):
        self.path = path

    def get(self):
        f = self.path / "plan.json"
        if f.exists():
            with f.open() as o:
                return json.load(o)
        else:
            return {}

    def save(self, plan):
        with open(self.path / "plan.json", "w") as o:
            json.dump(plan, o)

    def delete(self):
        p = self.path / "plan.json"
        if p.exists():
            p.unlink()


base = Path.home() / "loko"


async def aprint(arg):
    logger.debug(arg['msg'])


async def plan(p: Path, company: str, gateway_port=8080, push=True):
    dao = FSLokoProjectDAO()
    project = dao.get(p)
    client2 = docker.from_env()
    # company = "livetechprove"
    # Has a dockerfile
    client = LokoDockerClient()
    name = project.path.name
    has_local = (project.path / "Dockerfile").exists()
    if has_local:
        # Build a local extension
        MAIN_IMAGE = f"{company}/{project.path.name}"
        logger.info(f"Building {MAIN_IMAGE}")
        resp = await client.build(project.path, image=MAIN_IMAGE, log_collector=aprint)
        if resp:
            logger.info("Build successful")

    RULES = [
        {"name": "orchestrator", "host": "orchestrator", "port": 8888, "type": "orchestrator", "scan": True}]
    if has_local:
        RULES.append(dict(name=name, host=name, port=8080, type="custom", scan=False))

    services = {}
    project_config_path = p / "config.json"
    project_config = {}
    if project_config_path.exists():
        with open(project_config_path) as o:
            project_config = json.load(o)

    ges = set(project.get_global_components())
    with set_directory(p):
        with TemporaryDirectory(dir=".") as d:
            d = Path(d)
            if ges:
                for ge in ges:
                    _ge = ge
                    ge = base / "shared" / "extensions" / ge / "extensions" / "components.json"
                    rel = ge.relative_to(base)
                    dest = d / rel
                    dest.parent.mkdir(exist_ok=True, parents=True)
                    shutil.copyfile(ge, dest)
                    root = ge.parent.parent
                    config_path = root / "config.json"
                    df = root / "Dockerfile"
                    docker_cmds = [x.strip() for x in open(df) if x.strip()]
                    if config_path.exists():
                        with config_path.open() as cf:
                            config = json.load(cf)
                            sides = config.get("side_containers", {})
                            for k, v in sides.items():
                                services[f"{root.name}_{k}"] = dict(image=v['image'])
                            includes = project_config.get("includes", {}).get(_ge, [])
                            with set_directory(base / "shared" / "extensions" / _ge), TemporaryDirectory(
                                    dir=".") as dd:
                                dd = Path(dd)
                                for incl in includes:
                                    source = incl.get("source")
                                    target = incl.get("target")
                                    source = Path(source)
                                    target = Path(target)
                                    tt = dd / "includes"
                                    shutil.copytree(source, tt)
                                    docker_cmds.append(f"COPY {tt.as_posix()} {target.as_posix()}")

                                finaldf = StringIO()
                                finaldf.write("\n".join(docker_cmds))
                                finaldf.seek(0)

                                GE_IMAGE_NAME = f"{company}/{root.name}"
                                logger.info(f"Building global extension: {GE_IMAGE_NAME}")
                                resp = await client.build(root, dockerfile=finaldf, image=GE_IMAGE_NAME)
                                if resp:
                                    logger.info("Build successful")
                                if push:
                                    logger.info(f"Pushing {GE_IMAGE_NAME}")
                                    for line in client2.images.push(GE_IMAGE_NAME, stream=True):
                                        for ll in [x.strip() for x in re.split("\r\n|\r|\n", line.decode()) if
                                                   x.strip()]:
                                            msg = json.loads(ll)
                                            if "error" in msg:
                                                logger.error(msg)
                                                sys.exit(1)
                                            logger.debug(msg)

            # Build orchestrator
            resources = set(project.get_required_resources())

            logger.info(f"Resources: {resources}")
            ORCH_IMAGE = f"{company}/{name}_orchestrator"
            os.chdir(project.path)
            orchestrator_commands = ["FROM lokoai/loko-orchestrator:1.0.0-dev",
                                     f"RUN mkdir -p /root/loko/projects/{name}", f"COPY . /root/loko/projects/{name}/",
                                     "CMD python services.py"]

            for r in resources:
                r = Path(r).relative_to("data")
                dest = d / r
                if not dest.parent.exists():
                    dest.parent.mkdir(exist_ok=True, parents=True)
                shutil.copyfile(base / r, d / r)
                logger.info(f"Copying {base / r} to {d / r}")
                ss = (d / r)
                tt = Path('/root/loko') / r
                orchestrator_commands.append(f"COPY {ss.as_posix()} {tt.as_posix()}")

            df = StringIO()
            if ges:
                orchestrator_commands.append(f"COPY {d}/shared/ /root/loko/shared/")

            df.write("\n".join(orchestrator_commands))
            df.seek(0)

            logger.info(f"Building orchestrator: {ORCH_IMAGE}")
            resp = await client.build(project.path, dockerfile=df, image=ORCH_IMAGE, log_collector=aprint)
            if resp:
                logger.info("Build successful")

            if push:
                if has_local:
                    logger.info(f"Pushing {MAIN_IMAGE}")

                    for line in client2.images.push(MAIN_IMAGE, stream=True):
                        for ll in [x.strip() for x in re.split("\r\n|\r|\n", line.decode()) if x.strip()]:
                            msg = json.loads(ll)
                            if "error" in msg:
                                logger.error(msg)
                                sys.exit(1)
                            logger.debug(msg)
                    logger.info(f"Pushed")

                logger.info(f"Pushing {ORCH_IMAGE}")

                for line in client2.images.push(ORCH_IMAGE, stream=True):
                    for ll in [x.strip() for x in re.split("\r\n|\r|\n", line.decode()) if x.strip()]:
                        msg = json.loads(ll)
                        if "error" in msg:
                            logger.error(msg)
                            sys.exit(1)
                        logger.debug(msg)
                logger.info(f"Pushed")

            # Generate docker-compose

            for ge in ges:
                services[ge] = dict(image=f"{company}/{ge}")
                RULES.append(dict(name=ge, host=ge, port=8080, type="custom", scan=False))

            services['orchestrator'] = dict(image=ORCH_IMAGE,
                                            volumes=["/var/run/docker.sock:/var/run/docker.sock"],
                                            command="python services.py",
                                            environment=dict(GATEWAY="http://gateway:8080",
                                                             EXTERNAL_GATEWAY=f"http://localhost:{gateway_port}", ))

            if has_local:
                services[name] = dict(image=MAIN_IMAGE)

            dc = dict(version="3.3", services=services)

            """for core in set(project.get_core_components()):
                includes = project_config.get("includes", {}).get(core, [])
                if includes:
                    core_docker_cmds = [f"FROM {core_images[core]['image']}"]
                    for incl in includes:
                        source = Path(incl.get("source"))
                        target = incl.get("target")
                        tsource = d / "predictors" / source.name
                        shutil.copytree(source, tsource)
                        core_docker_cmds.append(f"COPY {tsource} {target}")
                        CORE_IMAGE = f"{company}/{p.name}_{core}"

                        logger.info(f"Building {core}: {CORE_IMAGE}")
                        finaldf = StringIO()
                        finaldf.write("\n".join(core_docker_cmds))
                        finaldf.seek(0)
                        print("\n".join(core_docker_cmds))

                        resp = await client.build(project.path, dockerfile=finaldf, image=CORE_IMAGE,
                                                  log_collector=aprint)
                        if resp:
                            logger.info("Build successful")
                        core_images[core]['image'] = CORE_IMAGE

                services[core] = core_images[core]

                RULES.append(dict(name=core, host=core, port=8080, type=core, scan=False))"""

            services['gateway'] = dict(image="lokoai/loko-gateway:0.0.4-dev", ports=[f"{gateway_port}:8080"],
                                       environment=dict(RULES=str(RULES)))

            logger.info("Creating docker-compose")

            with open("docker-compose.yml", "w") as o:
                YAML.dump(dc, o)
            logger.info("Done!")

    await client.close()


async def init_ec2(p: Path, instance_name, instance_type="t2.micro", ami="ami-0a691527202ea8b3d",
                   security_group="default"):
    ec2 = EC2Manager()

    dao = PlanDAO(p)
    plan = dao.get()
    instance_id = plan.get("instance")
    logger.info("Creating ec2 instance")
    if instance_id:
        try:
            inst = ec2.get(instance_id)
            state = inst.state['Name']
            if state != "running":
                logger.error(f"EC2 instance {instance_id} is in state {state}")
                sys.exit(1)
        except Exception as e:
            logger.error(e)
            sys.exit(1)

    if not instance_id:
        ii = ec2.create(instance_name, ami, instance_type=instance_type, security_group=security_group)
        plan['instance'] = ii.id
        dao.save(plan)
    instance_id = plan['instance']
    logger.info("Waiting for instance running state...")
    ec2.wait_for(instance_id, "running")

    logger.info(f"Instance {instance_id} is running")
    inst = ec2.get(instance_id)
    logger.info(f"Public DNS name: {inst.public_dns_name}")
    logger.info(f"Public IP Address: {inst.public_ip_address}")


async def deploy(p: Path):
    ec2 = EC2Manager()
    dao = PlanDAO(p)
    plan = dao.get()
    instance_id = plan.get("instance")
    inst = ec2.get(instance_id)
    # img = "ami-06ce824c157700cd2"
    # ec2.create("accenture", img)
    logger.info(f"Deploying to {instance_id}...")
    if inst.state['Name'] != "running":
        logger.error(f"Can't deploy. Instance {instance_id} is in state {inst.state['Name']}")
        sys.exit(1)

    ec2.copy([p / "docker-compose.yml"],
             inst.public_dns_name)
    for el in ec2.commands(["docker-compose down", "docker-compose pull", "docker-compose up -d"],
                           inst.public_dns_name):
        logger.info(el.strip())
    logger.info("Done!")


def info():
    dao = PlanDAO(Path(os.getcwd()))
    plan = dao.get()
    instance_id = plan.get("instance")
    logger.info(f"Instance id: {instance_id}")
    dao = FSLokoProjectDAO()
    ec2 = EC2Manager()
    dns = None
    if instance_id:
        try:
            ec2inst = ec2.get(instance_id)
        except Exception as e:
            logger.error(e)
            sys.exit(1)
        logger.info(f"Instance {instance_id} status: {ec2inst.state['Name']}")
        logger.info(f"Public DNS name: {ec2inst.public_dns_name}")
        dns = ec2inst.public_dns_name
        logger.info(f"Public IP Address: {ec2inst.public_ip_address}")

    project = dao.get(Path(os.getcwd()))

    for n in project.nodes():
        try:
            if n[0].data.get('name') == "Route":
                path = n[0].data['options']['values']['path']
                if dns:
                    logger.info(f"Endpoint: http://{dns}:8080/routes/orchestrator/endpoints/{project.id}/{path}")
                else:
                    logger.info(f"Endpoint: routes/orchestrator/endpoints/{project.id}/{path}")
        except Exception as inst:
            pass


def destroy():
    dao = PlanDAO(Path(os.getcwd()))
    plan = dao.get()
    instance_id = plan.get("instance")
    if instance_id is None:
        logger.error("There is no instance to destroy")
        sys.exit(1)
    ec2 = EC2Manager()
    inst = ec2.get(instance_id)
    logger.info(f"Terminating {instance_id}...")
    inst.terminate()
    dao.delete()

    logger.info("Done!")
