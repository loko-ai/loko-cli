import json
from pathlib import Path

from loko_cli.model.loko import Project, Template, Edge, Node, Endpoint, Graph
from loko_cli.utils.jsonutils import GenericJsonDecoder, GenericJsonEncoder

dec = GenericJsonDecoder([Project, Template, Edge, Node, Endpoint, Graph])


class LokoProjectDAO:
    def get(self, id):
        pass


class FSLokoProjectDAO(LokoProjectDAO):
    def get(self, path) -> Project:
        if not isinstance(path, Path):
            path = Path(path)
        project_path = path / "loko.project"
        config = path / "config.json"
        ISLOCALEXTENSION = (path / "Dockerfile").exists()

        with open(project_path) as f:
            o = json.loads(f.read(), object_hook=dec.object_hook)
            o.path = path
            return o
            # j = json.dumps(o, default=GenericJsonEncoder().default)
            # j = json.loads(j)
            # return Project(**j)
