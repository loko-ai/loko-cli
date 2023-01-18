from kubernetes import config, client

config.load_kube_config(config_file='/etc/rancher/k3s/k3s.yaml')
apps_v1 = client.AppsV1Api()
api_client = client.CoreV1Api()

DEPLOYMENT_NAME = "gw-deployment"
SERVICE_NAME = "gw-service"

CONTAINER_NAME = 'mongo'
IMAGE = 'lokoai/loko-gateway:0.0.4-dev'
CONTAINER_PORT = 8080

LABELS = {"app": "gw"}

REPLICAS = 1

RULES = []
RULES.extend([{"name": "orchestrator", "host": "orchestrator", "port": 8888,
               "type": "orchestrator", "scan": False},
              {"name": "predictor", "host": "predictor", "port": 8080,
               "type": "predictor"}])

NODE_PORT = 30004
# Configureate Pod template container
container = client.V1Container(
    name=CONTAINER_NAME,
    image=IMAGE,
    ports=[client.V1ContainerPort(container_port=CONTAINER_PORT)],
    env=[client.V1EnvVar(name="RULES", value=str(RULES))],
    volume_mounts=[client.V1VolumeMount(name="my-pv", mount_path="/root/loko")],
    # resources=client.V1ResourceRequirements(
    #    requests={"cpu": "100m", "memory": "200Mi"},
    #    limits={"cpu": "500m", "memory": "500Mi"},
    # ),
)

# Deployment
deployment = client.V1Deployment(
    api_version="apps/v1",
    kind="Deployment",
    metadata=client.V1ObjectMeta(name=DEPLOYMENT_NAME),
    spec=client.V1DeploymentSpec(replicas=REPLICAS,
                                 template=client.V1PodTemplateSpec(metadata=client.V1ObjectMeta(labels=LABELS),
                                                                   spec=client.V1PodSpec(containers=[container],
                                                                                         volumes=[client.V1Volume(
                                                                                             name="my-pvc",
                                                                                             persistent_volume_claim=client.V1PersistentVolumeClaim())])),
                                 selector={"matchLabels": LABELS}),
)

resp = apps_v1.create_namespaced_deployment(body=deployment, namespace="default")
print(resp)

# Service
service = client.V1Service(api_version='v1',
                           kind='Service',
                           metadata=client.V1ObjectMeta(name=SERVICE_NAME),
                           spec=client.V1ServiceSpec(selector=LABELS,
                                                     external_traffic_policy="Cluster",
                                                     type='LoadBalancer',  # 'NodePort',
                                                     ports=[client.V1ServicePort(port=CONTAINER_PORT,
                                                                                 node_port=NODE_PORT)]))

# api_client.create_namespaced_service(namespace="default", body=service)
print(resp)
