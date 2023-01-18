import asyncio
import json
import os
import shutil
import time
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import docker
from docker.utils import tar
from tenacity import retry

from loko_cli.business.deployment.cloud.ec2 import EC2Manager
from loko_cli.business.docker.dockermanager import LokoDockerClient
from loko_cli.config.app_init import YAML
from loko_cli.dao.loko import FSLokoProjectDAO
from loko_cli.utils.path_utils import set_directory


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


base = Path.home() / "loko"


async def aprint(*args):
    print(*args)


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
        resp = await client.build(project.path, image=MAIN_IMAGE)
        print(resp)

    RULES = [
        {"name": "orchestrator", "host": "orchestrator", "port": 8888, "type": "orchestrator", "scan": True}]
    if has_local:
        RULES.append(dict(name=name, host=name, port=8080, type="custom"))

    services = {}

    ges = list(project.get_global_components())
    with set_directory(p):
        print("CWD", p, os.getcwd())
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
                    print(root)
                    config_path = root / "config.json"
                    if config_path.exists():
                        with config_path.open() as cf:
                            config = json.load(cf)
                            sides = config.get("side_containers", {})
                            for k, v in sides.items():
                                services[f"{root.name}_{k}"] = dict(image=v['image'])

                    GE_IMAGE_NAME = f"{company}/{root.name}"
                    print(GE_IMAGE_NAME)
                    print("Building ge", GE_IMAGE_NAME)
                    resp = await client.build(root, GE_IMAGE_NAME)
                    if push:
                        for line in client2.images.push(GE_IMAGE_NAME, stream=True):
                            print(line)

            # Build orchestrator
            ORCH_IMAGE = f"{company}/{name}_orchestrator"
            os.chdir(project.path)
            df = StringIO()
            if ges:
                df.write(f"""FROM lokoai/loko-orchestrator:0.0.4-dev
RUN mkdir -p /root/loko/projects/{name}
COPY . /root/loko/projects/{name}/
COPY {d}/shared/ /root/loko/shared/
CMD python services.py""")
            else:
                df.write(f"""FROM lokoai/loko-orchestrator:0.0.3-dev
    RUN mkdir -p /root/loko/projects/{name}
    COPY . /root/loko/projects/{name}/
    CMD python services.py""")

            df.seek(0)

            print("Building", ORCH_IMAGE)
            print(df.getvalue())
            print(df.getvalue())
            resp = await client.build(project.path, dockerfile=df, image=ORCH_IMAGE, log_collector=aprint)
            print(resp)
            # Pushing images if needed

            if push:
                if has_local:
                    for line in client2.images.push(MAIN_IMAGE, stream=True):
                        print(line)
                for line in client2.images.push(ORCH_IMAGE, stream=True):
                    print(line)

            # Generate docker-compose

            for ge in ges:
                services[ge] = dict(image=f"{company}/{ge}")
                RULES.append(dict(name=ge, host=ge, port=8080, type="custom"))

            services['orchestrator'] = dict(image=ORCH_IMAGE,
                                            volumes=["/var/run/docker.sock:/var/run/docker.sock"],
                                            command="python services.py",
                                            environment=dict(GATEWAY="http://gateway:8080",
                                                             EXTERNAL_GATEWAY=f"http://localhost:{gateway_port}", ))
            services['gateway'] = dict(image="lokoai/loko-gateway:0.0.4-dev", ports=[f"{gateway_port}:8080"],
                                       environment=dict(RULES=str(RULES)))
            if has_local:
                services[name] = dict(image=MAIN_IMAGE)

            dc = dict(version="3.3", services=services)

            print(dc)
            with open("docker-compose.yml", "w") as o:
                print(YAML.dump(dc, o))

    await client.close()


async def init(p: Path, instance_name, instance_type="t2.micro"):
    ec2 = EC2Manager()
    img = "ami-0a691527202ea8b3d"
    dao = PlanDAO(p)
    plan = dao.get()
    instance_id = plan.get("instance")
    if not instance_id:
        ii = ec2.create(instance_name, img, instance_type)
        plan['instance'] = ii.id
        dao.save(plan)
    instance_id = plan['instance']
    ec2.wait_for(instance_id, "running")
    inst = ec2.get(instance_id)

    # print(ii, ii[0].state)

    await asyncio.sleep(5)

    @retry
    def ii():
        for el in ec2.commands(["curl -fsSL https://get.docker.com -o get-docker.sh", "sudo sh get-docker.sh",
                                "sudo usermod -aG docker ubuntu",
                                'sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose',
                                'sudo chmod +x /usr/local/bin/docker-compose'],
                               inst.public_dns_name):
            print(el)

    # ii()


async def deploy(p: Path):
    ec2 = EC2Manager()
    dao = PlanDAO(p)
    plan = dao.get()
    instance_id = plan.get("instance")
    inst = ec2.get(instance_id)
    # img = "ami-06ce824c157700cd2"
    # ec2.create("accenture", img)

    ec2.copy([p / "docker-compose.yml"],
             inst.public_dns_name)
    for el in ec2.commands(["docker-compose pull", "docker-compose up -d"], inst.public_dns_name):
        print(el)


if __name__ == '__main__':
    p = Path("/home/fulvio/loko/projects/prova_mongo")

    asyncio.run(plan(p, "livetechprove", push=True))
    asyncio.run(init(p, "fp"))
    asyncio.run(deploy(p))
