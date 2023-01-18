import os

import ruamel.yaml

from loko_cli.model.microservices import Microservice

YAML = ruamel.yaml.YAML()
YAML.preserve_quotes = True
YAML.indent(sequence=3, offset=2)

GATEWAY_DS = Microservice(name="gw", image="lokoai/loko-gateway:0.0.4-dev", ports={8080: 19999},
                          environment=dict(AUTOSCAN=False,
                                           RULES='[{"name": "orchestrator", "host": "orchestrator", "port": 8888,"type": "orchestrator","scan":True},{"name": "predictor", "host": "predictor", "port": 8080,"type": "custom","scan":False}]'))
ORCHESTRATOR_DS = Microservice(name="orchestrator", image="lokoai/loko-orchestrator:0.0.3-dev",
                               environment=dict(GATEWAY="http://gw:8080", EXTERNAL_GATEWAY="http://localhost:9999",
                                                USER_UID=1000, USER_GID=129),
                               volumes=["/var/run/docker.sock:/var/run/docker.sock"],
                               volumes_from=["orchestrator_volume"])

ORCHESTRATOR_DC = Microservice(name="orchestrator_volume", image="project_data",
                               hostconfig=dict(Binds=["/root/loko/"]))

TEMPORARY_MAPPING = dict(predictor=Microservice(name="predictor", image="lokoai/ds4biz-predictor-dm:0.0.3-dev",
                                                volumes=[
                                                    f"{os.path.expanduser('~')}/loko/predictors:/ds4biz-predictor-dm/repo",
                                                    "/var/run/docker.sock:/var/run/docker.sock"],
                                                environment=dict(GATEWAY_URL="http://gw:8080",
                                                                 NETWORK_NAME="default",
                                                                 VOLUME_PATH=f"{os.path.expanduser('~')}/loko/predictors",
                                                                 IMGS_MAPPING={
                                                                     'predictor_base': 'lokoai/ds4biz-predictor-base:0.0.3-dev'})))
