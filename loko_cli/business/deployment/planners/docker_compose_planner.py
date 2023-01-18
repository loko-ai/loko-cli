# crea wstruttura
# plan(loko_project)
import asyncio
import dataclasses
import json
import pprint
import shutil
from pathlib import Path

from loko_cli.business.deployment.planners.planners import DestPlanner
from loko_cli.business.docker.dockermanager import LokoDockerClient
from loko_cli.config.app_init import YAML, GATEWAY_DS, ORCHESTRATOR_DS, ORCHESTRATOR_DC, TEMPORARY_MAPPING
from loko_cli.dao.loko import FSLokoProjectDAO
from loko_cli.model.loko import Project
from loko_cli.model.plan import Plan
from loko_cli.utils.jsonutils import GenericJsonEncoder


class DCPlanner(DestPlanner):
    def __init__(self, output_dir: Path = None, version="0.1"):
        super().__init__(output_dir, version)
        self.dc = None

    def plan(self, project: Project):

        # required_global_extensions = list(get_components_from_project(loko_prj))
        # required_resources = get_required_resources_from_project(loko_prj)
        # HAS_RESOURCES = bool(required_resources)
        # HAS_EXTENSIONS = (project_path / "Dockerfile").exists()
        # HAS_GLOBAL_EXTENSIONS = bool(required_global_extensions)

        # RULES = []

        ## INIT PROJECT PLAN
        plan = Plan(path=project.path, namespace=project.name, orchestrator=ORCHESTRATOR_DS, gateway=GATEWAY_DS)

        plan.resources = list(project.get_required_resources())

        if project.is_container():
            plan.add_local_extension(dict(name=project.id, image=project.name))

        for el in project.get_core_components():
            if el in TEMPORARY_MAPPING:
                plan.add_service(TEMPORARY_MAPPING[el])

        available_global_extensions = {}
        for f in (project.path.parent.parent / "shared" / "extensions").glob("**/components.json"):
            global_ext_path = f.parent.parent
            pname = global_ext_path.name
            available_global_extensions[pname] = f

        for global_extension in project.get_global_components():
            print(global_extension)

        """if HAS_GLOBAL_EXTENSIONS:
                global_ext_path = f.parent.parent
                pname = global_ext_path.name
                if pname in required_global_extensions:
                    pp.add_global_extensio(Microservice(name=pname, image=pname))
                    for ms in get_side_containers(global_ext_path):
                        pp.add_side_container(ms)"""

        ## SAVE JSON PLAN
        # pp.save(project_path)

        ## IF ENGINE GENERATE ENGINE SPECIFIC TEMPLATE
        # if engine:
        #    ENGINE_PLAN_MAPPING[engine](pp, project_path)
        return plan

    def save(self):
        dest = self.output_dir / "docker-compose.yml"

        if self.plan:

            with dest.open("w") as f:
                YAML.dump(self.dc.get_json(), f)
        else:
            raise Exception("Can't save empty plan, try to make one first")

    """def services_from_project(self, loko_project_path: Path):

        lp = get_loko_project(loko_project_path)

        serv_img = dict()

        for el in get_components_from_project(lp):
            if el in TEMPORARY_MAPPING:
                serv_img.update({el: TEMPORARY_MAPPING[el]})

        for m in get_side_containers(p):
            serv_img.update({m.name: m})

        for k, v in serv_img.items():
            if isinstance(v, DockerService):
                extension = v
            else:
                extension = DockerService(name=k, image=v)
            yield extension"""


if __name__ == "__main__":
    # d = dict(version="3.3", networks=dict(loko=dict(driver="bridge")), services=services)
    from loko_cli.business.deployment.appliers.docker_compose_applier import DockerComposeApplier


    async def main():
        p = Path("/home/fulvio/loko/projects/hello")
        dao = FSLokoProjectDAO()
        project = dao.get(p)
        # DCPlanner(version="0.2").plan(p)
        # AWSPlanner().plan(p)
        # Generazione piano
        planner = DCPlanner()
        print(project.path)
        plan = planner.plan(project)
        client = LokoDockerClient()
        applier = DockerComposeApplier(project_company="livetechprove", client=client)

        # planner.save()
        # o="/dsdfs/ddd"
        # plan.save(o)

        # plan + apply senza salvare
        # DockerComposeApplier.apply(DCPlanner(p))

        # plan+apply passando per disco
        # plan = DCPlanner(p)
        # plan.save(o)
        # DockerComposeApplier().apply(o)
        enc = GenericJsonEncoder(include_class=True)
        with open("plan.json", "w") as o:
            json.dump(plan, o, default=enc.default, indent=4)
        await applier.apply(plan)
        await client.close()


    asyncio.run(main())
