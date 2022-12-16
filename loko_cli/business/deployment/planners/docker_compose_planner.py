# crea wstruttura
# plan(loko_project)
import shutil
from pathlib import Path

from loko_tools.config.app_init import GATEWAY_DS, ORCHESTRATOR_DS, TEMPORARY_MAPPING, YAML
from loko_tools.model.docker_service_model import DockerService
from loko_tools.model.plan_model import DockerComposePlan
from loko_tools.utils.project_utils import get_loko_project, get_side_containers, get_components_from_project


class Planner:
    def __init__(self):
        pass

    def plan(self, loko_project: Path):
        pass


class DestPlanner(Planner):
    def __init__(self, output_dir: Path = None, version="0.1"):
        super().__init__()
        self.output_dir = Path(output_dir or f"dist/docker_compose/{version}")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.version = version

    def clean(self):
        shutil.rmtree(self.output_dir)


class DCPlanner(DestPlanner):
    def __init__(self, project_company, output_dir: Path = None, version="0.1"):
        super().__init__(output_dir, version)
        self.project_company = project_company
        self.dc = None

    def plan(self, loko_project: Path) -> DockerComposePlan:

        dcplan = DockerComposePlan()
        dcplan.add_service(GATEWAY_DS)
        dcplan.add_service(ORCHESTRATOR_DS)
        dcplan.add_service(DockerService(name=loko_project.name, image=f"{self.project_company}/{loko_project.name}"))

        # for ds in self.services_from_project(loko_project):
        #    dcplan.add_service(ds)

        # self.dc = dcplan
        return dcplan

    def save(self):
        dest = self.output_dir / "docker-compose.yml"

        if self.plan:

            with dest.open("w") as f:
                YAML.dump(self.dc.get_json(), f)
        else:
            raise Exception("Can't save empty plan, try to make one first")

    def services_from_project(self, loko_project_path: Path):

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
            yield extension


class AWSPlanner(DestPlanner):
    def __init__(self):
        super().__init__(Path("../dist/aws"))

    def plan(self, loko_project: Path):
        for i in range(5):
            dest = self.output_dir / f"Conf{i}.yml"
            dest.touch()


if __name__ == "__main__":
    # d = dict(version="3.3", networks=dict(loko=dict(driver="bridge")), services=services)

    p = Path("/home/alejandro/loko/projects/hello_ale")
    # DCPlanner(version="0.2").plan(p)
    # AWSPlanner().plan(p)
    # Generazione piano
    planner = DCPlanner(project_company="lokairepo")
    plan = planner.plan(p)
    print(plan)
    planner.save()
    # o="/dsdfs/ddd"
    # plan.save(o)

    # plan + apply senza salvare
    # DockerComposeApplier.apply(DCPlanner(p))

    # plan+apply passando per disco
    # plan = DCPlanner(p)
    # plan.save(o)
    # DockerComposeApplier().apply(o)
