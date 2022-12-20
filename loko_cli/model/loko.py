import uuid
from datetime import datetime
from pathlib import Path
from pprint import pprint

LATEST_PRJ_VERSION = "1.0.0"


class NodeInfo:
    def __init__(self, node):
        self.id = node.id
        self.values = {k: v for k, v in node.data['options']['values'].items() if v is not None}
        self.options = node.data['options']
        self.io = dict(zip([i['id'] for i in node.data['inputs']], [o['id'] for o in node.data['outputs']]))

        for k, v in node.data.items():
            if k != 'options':
                self.__dict__[k] = v


class Node:
    def __init__(self, id, **kwargs):
        self.id = id
        self.position = kwargs.pop("position") if "position" in kwargs else None
        self.type = kwargs.pop("type") if "type" in kwargs else None
        self.dragHandle = kwargs.pop("dragHandle") if "dragHandle" in kwargs else None
        self.sourcePosition = kwargs.pop("sourcePosition") if "sourcePosition" in kwargs else None
        self.targetPosition = kwargs.pop("targetPosition") if "targetPosition" in kwargs else None
        self.width = kwargs.pop("width") if "width" in kwargs else None
        self.height = kwargs.pop("height") if "height" in kwargs else None
        self.selected = kwargs.pop("selected") if "selected" in kwargs else None
        self.dragging = kwargs.pop("dragging") if "dragging" in kwargs else None
        self.data = kwargs.pop("data")
        for k, v in kwargs.items():
            setattr(self, k, v)

        # dict(name=name, inputs = inputs if inputs is not None else ["input"],outputs = outputs if outputs is not None else ["output"],)
        # self.type = type
        # self.values = values
        # self.options = options or []
        # self.values = values or {}
        # for k, v in kwargs.items():
        #     setattr(self, k, v)


class Endpoint:
    def __init__(self, id, endpoint):
        self.id = id
        self.endpoint = endpoint


class Edge:
    def __init__(self, id, source: str, sourceHandle: str, target: str, targetHandle, **kwargs):
        self.id = id
        self.source = source
        self.sourceHandle = sourceHandle
        self.target = target
        self.targetHandle = targetHandle
        for k, v in kwargs.items():
            setattr(self, k, v)


class Graph:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges


class Comment:
    def __init__(self, id, text, fill, height, width, x, y):
        self.id = id
        self.text = text
        self.fill = fill
        self.height = height
        self.width = width
        self.x = x
        self.y = y


'''{id:nome_template, flow:{nodes:[], edges: [], comments: []}}'''


class Template:

    def __init__(self, id, description="", created_on=None, last_modify=None, graph=None):
        self.id = id
        self.description = description
        self.created_on = created_on or datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        self.last_modify = last_modify or datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        self.graph = graph or dict(main=Graph(nodes=[], edges=[]))

    def info(self):
        return dict(id=self.id, description=self.description, created_on=self.created_on, last_modify=self.last_modify)


class Project:
    def __init__(self, name, path: Path = None, description="", created_on=None, last_modify=None, graphs=None,
                 open=None,
                 active=None,
                 id=None,
                 resources=None,
                 global_extensions=None,
                 **kwargs):
        self.id = id or str(uuid.uuid4())
        self.path = path,
        self.name = name
        self.description = description
        self.created_on = created_on or datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.last_modify = last_modify or datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.graphs = graphs or dict(main=Graph(nodes=[], edges=[]))
        self.open = open or ["main"]
        self.active = active or "main"
        self.version = LATEST_PRJ_VERSION
        self.resources = resources or []
        self.global_extensions = global_extensions or []

    def nodes(self):
        for id, g in self.graphs.items():
            for n in g.nodes:
                yield n, id

    def edges(self):
        for id, g in self.graphs.items():
            for e in g.edges:
                yield e

    def info(self):

        return dict(name=self.name, id=self.id, description=self.description, created_on=self.created_on,
                    last_modify=self.last_modify)

    def get_required_resources(self):
        for k, g in self.graphs.items():
            for node in g.nodes:
                if "Inputs" == node.data['options'].get("group"):
                    yield node.data['options'].get("values").get("value").get("path")

    def get_global_components(self):
        for k, g in self.graphs.items():
            for node in g.nodes:
                if "pname" in node.data:
                    yield node.data["pname"]

    def get_core_components(self):
        for k, g in self.graphs.items():
            for node in g.nodes:
                if "microservice" in node.data:
                    yield node.data["microservice"]

    def is_container(self):
        return (self.path / "Dockerfile").exists()


if __name__ == '__main__':
    # prrr = "{'name': 'asdasdasdasd', 'id': '27eb671b-fe71-45d2-8cd9-8a8d5fa7fcf9', 'description': '', 'created_on': '15/06/2022, 11:16:25', 'last_modify': '15/06/2022, 11:17:12', 'graphs': {'main': <ds4biz_orchestrator.model.projects.Graph object at 0x7f3821d181c0>}, 'open': ['main'], 'active': 'main'}"
    # p = Project(**eval(prrr))
    # print(p.id)
    print(Project.__dict__)
