import json
from pathlib import Path
from typing import List

from loko_cli.model.microservice_model import Microservice


class Plan:

    def __init__(self, namespace, services: List[Microservice] = None):
        self.namespace = namespace
        self.services = services or []
        self.local_extensions = []
        self.global_extensions = []
        self.side_containers = []

    def add_service(self, service: Microservice):
        self.services.append(service)

    def add_local_extension(self, service: Microservice):
        self.local_extensions.append(service)

    def add_global_extensio(self, service: Microservice):
        self.global_extensions.append(service)

    def add_side_container(self, service: Microservice):
        self.side_containers.append(service)

    # def get_json(self):
    #     return dict(version=self.dc_version, services={x.name: x.get_body() for x in self.services})

    def save(self, path):
        if not isinstance(path, Path):
            path = Path(path)

        def fun(services):
            ris = []
            for ms in services:
                if isinstance(ms, Microservice):
                    ris.append(ms.__dict__)
                else:
                    ris.append(ms)
            return ris

        self.services = fun(self.services)
        self.local_extensions = fun(self.local_extensions)
        self.global_extensions = fun(self.global_extensions)
        self.side_containers = fun(self.side_containers)

        d = self.__dict__
        with open(path / "plan.json", "w") as f:
            json.dump(d, f, indent=2)

# def plan_from_dc(path: Path):
#     with path.open("rb") as f:
#         r = YAML.load(f)
#         r = dict(r)
#     dc_version = r["version"]
#     services = dict(r["services"])
#     ds_json = json.loads(json.dumps(services))
#     services = [Microservice(name, **body) for name, body in ds_json.items()]
#
# # def plan2dc(p:Plan):
#


'''
{
  "services": {
    "orchestrator": {
      "version": "0.0.3-dev",
      "args": {
        "volumes": [
          "data_container:/root/loko/loko"
        ]
      }
    },
    "gateway": {
      "version": "0.0.3-dev",
      "args": {
        "volumes": [
          "data_container:/root/loko/loko"
        ]
      }
    },
    "local_extensions": [],
    "global_extensions": []
  },
  "namespace": "primo_project"
}
'''

if __name__ == '__main__':
    path = Path("/home/alejandro/loko/projects/vanilla")
    p = Plan(path.name)

    p.save(path)
