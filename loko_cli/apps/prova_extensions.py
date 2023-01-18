import asyncio
import json
import os
import shutil
import time
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from pprint import pprint
from tempfile import TemporaryDirectory

from docker.utils import tar

from loko_cli.business.docker.dockermanager import LokoDockerClient
from loko_cli.dao.loko import FSLokoProjectDAO

base = Path("/home/fulvio/loko")


def get_required_ge(p: Path):
    dao = FSLokoProjectDAO()

    project = dao.get(p)
    for n, tab in project.nodes():
        print(n.data['name'])

    print("****")
    global_exts = base / "shared" / "extensions"
    ge_map = {}
    for el in global_exts.glob("**/extensions/components.json"):
        with el.open() as o:
            components = json.load(o)
            for c in components:
                ge_map[c['name']] = el

    for n, tab in project.nodes():
        name = n.data['name']
        if name in ge_map:
            yield ge_map[name]


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


@contextmanager
def set_directory(path: Path):
    origin = Path().absolute()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)


async def build(p, df: StringIO, client):
    with set_directory(p):
        exclude = prepare_docker_ignore(p)
        print(exclude)

        context = tar(
            p, exclude=exclude, dockerfile=("Dockerfile", df.getvalue()),
            gzip=True
        )

        resp = await client.client.images.build(fileobj=context, encoding="UTF-8", tag="popo")
        return resp


async def main():
    client = LokoDockerClient()
    project = FSLokoProjectDAO().get(p)
    os.chdir(p)
    company = "livetechprove"
    with TemporaryDirectory(dir=".") as d:
        d = Path(d)

        for ge in project.get_global_components():
            ge = base / "shared" / "extensions" / ge / "extensions" / "components.json"
            rel = ge.relative_to(base)
            dest = d / rel
            dest.parent.mkdir(exist_ok=True, parents=True)
            shutil.copyfile(ge, dest)
            root = ge.parent.parent
            GE_IMAGE_NAME = f"{company}/{root.name}"
            print(GE_IMAGE_NAME)
            resp = await client.build(root, GE_IMAGE_NAME)
            print(resp)

        df = StringIO()
        df.write(f"""FROM lokoai/loko-orchestrator:0.0.3-dev
        RUN mkdir -p /root/loko/projects/{p.name}
        COPY . /root/loko/projects/{p.name}/
        COPY {d}/shared/ /root/loko/shared/
        CMD python services.py
        """)
        df.seek(0)

        resp = await client.build(p, image=f"{company}/{p.name}_orchestrator", dockerfile=df)
        print(resp)

    await client.close()


p = Path("/home/fulvio/loko/projects/prova_mongo")

asyncio.run(main())
