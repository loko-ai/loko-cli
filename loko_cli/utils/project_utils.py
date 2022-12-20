import glob
import json
import os.path
from pathlib import Path
from pprint import pprint

from loko_cli.model import loko
from loko_cli.model.microservices import Microservice
from loko_cli.model.loko import Template, Edge, Node, Endpoint, Graph,Project
from loko_cli.utils.jsonutils import GenericJsonDecoder, GenericJsonEncoder

dec = GenericJsonDecoder([Project, Template, Edge, Node, Endpoint, Graph], )


def get_loko_project(path):
    if not isinstance(path, Path):
        path = Path(path)
    path = path / "loko.project"
    with open(path) as f:
        o = json.loads(f.read(), object_hook=dec.object_hook)
        j = json.dumps(o, default=GenericJsonEncoder().default)
        j = json.loads(j)
        return Project(**j)


def get_side_containers(path):
    if not isinstance(path, Path):
        path = Path(path)
    config_path = path / "config.json"
    if not config_path.exists():
        return []
    with config_path.open() as fproject:
        p = json.load(fproject)
        for k, v in p['side_containers'].items():
            yield Microservice(name=f"{path.name}_{k}", **v)


def get_components_from_project(p: Project):
    for tab in p.tabs.all():
        for i, node in p.tabs[tab].nodes.nodes.items():
            # if node.data.get("microservice") =="predictor":
            if "pname" in node.data:
                yield node.data["pname"]
            if "microservice" in node.data:
                yield node.data["microservice"]


def get_required_resources_from_project(p: Project):
    for tab in p.tabs.all():
        for i, node in p.tabs[tab].nodes.nodes.items():
            if "Inputs" == node.data.get("options").get("group"):
                yield node.data.get("options").get("values").get("value").get("path")

if __name__ == '__main__':

    project_name = "primo"

    pjson = get_loko_project("/home/alejandro/loko/projects/tesseract_base_api")

    # for el in get_components_from_project(pjson):
    #     print(el)

    for el in get_required_resources_from_project(pjson):
        print(el)
