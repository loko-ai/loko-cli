import json

from loko_cli.config.app_init import YAML
from loko_cli.model.microservices import Microservice
from loko_cli.model.plan import Plan
from loko_cli.utils.jsonutils import GenericJsonDecoder

with open("plan.json") as o:
    dec = GenericJsonDecoder([Plan, Microservice])
    p: Plan = json.load(o, object_hook=dec.object_hook)
    print(p.namespace)

    main = p.local_extensions[0]
    print(main)
    services = dict(orchestrator=p.orchestrator.get_body(), gateway=p.gateway.get_body())
    services[main['name']] = dict(image=f"{p.namespace}/{main['image']}")
    dc = dict(version="3.3", services=services)
    print(dc)
    with open("docker-compose.yml", "w") as o:
        print(YAML.dump(dc, o))
