import asyncio
import os
import shutil
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp

from docker.utils import tar

from loko_cli.business.docker.dockermanager import LokoDockerClient
from loko_cli.config.app_init import GATEWAY_DS
from loko_cli.utils.project_utils import get_loko_project, get_components_from_project, \
    get_required_resources_from_project, get_side_containers


async def main(project_path: Path):
    if not isinstance(project_path, Path):
        project_path = Path(project_path)

    DCNAME = f"{project_path.name}_data"
    GWNAME = f"{project_path.name}_gateway"
    ORCHNAME = f"{project_path.name}_orchestrator"
    ORCVOLUME = f"{ORCHNAME}_volume"

    RULES = []

    loko_path = project_path.parent.parent
    mgr = LokoDockerClient()
    client = mgr.client

    loko_prj = get_loko_project(project_path)
    required_global_extensions = list(get_components_from_project(loko_prj))
    required_resources = get_required_resources_from_project(loko_prj)
    HAS_RESOURCES = bool(required_resources)
    HAS_EXTENSIONS = (project_path / "Dockerfile").exists()
    HAS_GLOBAL_EXTENSIONS = bool(required_global_extensions)

    # DATA CONTAINER DOCKERFILE BUILDING
    df = StringIO()
    df.write("FROM alpine\n")
    df.write(f"COPY loko.project /root/loko/projects/{project_path.name}/\n")

    # MANUAL TEMP DIR INSTEAD OF TEMPDIR CONTEXT MANAGER
    td = mkdtemp(dir=project_path)

    # ADD REQUIRED RESOURCES

    if HAS_RESOURCES:

        df.write(f"COPY {Path(td).name}/data /root/loko/data\n")
        for rr in required_resources:

            fname = loko_path / os.path.join(*rr.split(os.sep)[1:])
            rpath = Path(td)/"data/"
            rpath.mkdir(parents=True, exist_ok=True)
            shutil.copy(fname, rpath)


    # IF PRESENT ADD, BUILD AND RUN LOCAL EXTENSIONS (SINGLE MICROSERVICE)
    if HAS_EXTENSIONS:

        print(f"Local extensions detected")
        df.write(f"COPY extensions/ /root/loko/projects/{project_path.name}/extensions/\n")

        MAIN_NAME = f"{project_path.name}_main"

        RULES.append({"name": project_path.name, "host": MAIN_NAME, "port": 8080,
                      "type": "custom"})

        resp = await mgr.build(project_path)
        print(resp)
        if not resp:
            raise Exception("Error in building")
        await mgr.run(name=MAIN_NAME, image=project_path.name, autoremove=True, network="loko")

    # IF PRESENT ADD GLOBAL EXTENSIONS (ONE OR MORE MICROSERVICES)
    if HAS_GLOBAL_EXTENSIONS:

        print(f"Required global extensions detected: {','.join(required_global_extensions)}")
        # DOCKER BUILD CUSTOM TEMPORARY CONTEXT

        df.write(f"COPY {Path(td).name}/shared/extensions /root/loko/shared/extensions\n")
        # RETRIEVE EXTENSIONS BLUEPRINTS
        for f in (loko_path / "shared" / "extensions").glob("**/components.json"):
            global_ext_path = f.parent.parent
            pname = global_ext_path.name
            if pname in required_global_extensions:
                extpath = Path(td) / "shared/extensions" / pname / "extensions"
                extpath.mkdir(parents=True, exist_ok=True)
                shutil.copy(f, extpath)

                SC_DOCKER_SERVICES = get_side_containers(global_ext_path)

                # BUILD GLOBAL EXTENSION
                # cname = f"{project_path.name}_{pname}" per differenziare estensioni globali deployate i progetti distinti

                r = await mgr.build(global_ext_path)
                print(r)
                await mgr.run(name=pname, image=pname, network="loko")
                # ADD GLOBAL EXTENSION RULE

                RULES.append({"name": pname, "host": pname, "port": 8080,
                              "type": "custom"})

                ## RUN SIDE CONTAINERS

                for sc in SC_DOCKER_SERVICES:
                    print(sc.get_body())
                    resp = await mgr.run(name=sc.name, **sc.get_body(), network="loko", autoremove=True)
                    print(resp)

    context = tar(
        project_path.resolve(), dockerfile=("Dockerfile", df.getvalue()),
        gzip=True
    )

    ## BUILD DATA CONTAINER
    resp = await client.images.build(fileobj=context, encoding="UTF-8", tag=DCNAME)
    print(resp)

    ## RIMUOVO LA TEMP DIR

    shutil.rmtree(td)


    # DECLARE VOLUME MOUNT BIND
    hc = dict(Binds=["/root/loko/"])

    # CREATE VOLUME FROM DATA CONTAINER IMAGE
    await client.containers.create_or_replace(name=ORCVOLUME,
                                              config=dict(Image=DCNAME, HostConfig=hc))

    # CREATE ORC CONTAINER
    orch = await client.containers.create_or_replace(name=ORCHNAME,
                                                     config=dict(Image="lokoai/loko-orchestrator:0.0.4-dev",
                                                                 Env=[f"GATEWAY=http://{GWNAME}:8080"],
                                                                 HostConfig=dict(VolumesFrom=[ORCVOLUME], Binds=[
                                                                     "/var/run/docker.sock:/var/run/docker.sock"],
                                                                                 NetworkMode="loko", AutoRemove=True),
                                                                 Cmd=["python", "services.py"]))

    RULES.extend([{"name": "orchestrator", "host": ORCHNAME, "port": 8888,
                   "type": "orchestrator", "scan": True},
                  {"name": "predictor", "host": "predictor", "port": 8080,
                   "type": "predictor"}])

    gw = await mgr.run(name=GWNAME, image=GATEWAY_DS.image, environment=dict(AUTOSCAN=False, RULES=RULES),
                       ports=GATEWAY_DS.ports, autoremove=True,
                       network="loko")
    print(await orch.start())

    await client.close()


if __name__ == '__main__':
    asyncio.run(main("/home/alejandro/loko/projects/tesseract_base_api"))
