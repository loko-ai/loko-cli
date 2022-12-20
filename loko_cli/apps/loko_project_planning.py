import asyncio
from pathlib import Path

from loko_cli.config.app_init import GATEWAY_DS, ORCHESTRATOR_DS, TEMPORARY_MAPPING, YAML, ORCHESTRATOR_DC
from loko_cli.model.microservices import Microservice
from loko_cli.model.plan import Plan
from loko_cli.utils.project_utils import get_components_from_project, get_side_containers, get_loko_project, \
    get_required_resources_from_project


def plan2dc(pp: Plan, pp_path=None):
    dc_ms = {}

    for ms in pp.services:
        if isinstance(ms, Microservice):
            ms.environment = [f"{k}={str(v)}" for k, v in ms.environment.items()]
            extension = ms
        else:
            print(ms)
            extension = Microservice(name=ms["name"], image=ms["image"])
        dc_ms.update(extension.__dict__)

    d = dict(version="3.3", services=dc_ms)

    dc_path = 'docker-compose.yaml'
    if pp_path:
        if not isinstance(pp_path, Path):
            pp_path = Path(pp_path)
        dc_path = pp_path / 'docker-compose.yaml'

    with open(dc_path, 'w') as f:
        YAML.dump(d, f)


ENGINE_PLAN_MAPPING = dict(docker=plan2dc)


async def plan(project_path, engine=None):
    if not isinstance(project_path, Path):
        project_path = Path(project_path)
    # DCNAME = f"{project_path.name}_data"
    # GWNAME = f"{project_path.name}_gateway"
    # ORCHNAME = f"{project_path.name}_orchestrator"
    # ORCVOLUME = f"{ORCHNAME}_volume"

    loko_prj = get_loko_project(project_path)
    required_global_extensions = list(get_components_from_project(loko_prj))
    required_resources = get_required_resources_from_project(loko_prj)
    HAS_RESOURCES = bool(required_resources)
    HAS_EXTENSIONS = (project_path / "Dockerfile").exists()
    HAS_GLOBAL_EXTENSIONS = bool(required_global_extensions)

    #RULES = []

    if not isinstance(project_path, Path):
        project_path = Path(project_path)

    ## INIT PROJECT PLAN
    pp = Plan(project_path.name, [GATEWAY_DS, ORCHESTRATOR_DS, ORCHESTRATOR_DC])

    lp = get_loko_project(project_path)

    if HAS_RESOURCES:
        pp.resources = list(get_required_resources_from_project(lp))

    if HAS_EXTENSIONS:
        pimage = lp.id
        pp.add_local_extension(dict(name=lp.id, image=pimage))

    for el in get_components_from_project(lp):
        if el in TEMPORARY_MAPPING:
            pp.add_service(TEMPORARY_MAPPING[el])

    if HAS_GLOBAL_EXTENSIONS:
        for f in (project_path.parent.parent / "shared" / "extensions").glob("**/components.json"):
            global_ext_path = f.parent.parent
            pname = global_ext_path.name
            if pname in required_global_extensions:
                pp.add_global_extensio(Microservice(name=pname,image=pname))
                for ms in get_side_containers(global_ext_path):
                    pp.add_side_container(ms)


    ## SAVE JSON PLAN
    pp.save(project_path)

    ## IF ENGINE GENERATE ENGINE SPECIFIC TEMPLATE
    if engine:
        ENGINE_PLAN_MAPPING[engine](pp, project_path)


if __name__ == '__main__':
    asyncio.run(plan("/home/alejandro/loko/projects/tesseract_base_api", engine="docker"))
