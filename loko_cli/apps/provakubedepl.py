from kubernetes import client, config

config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

# Load the Kubernetes configuration from your local kubeconfig file
config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

# Create a new Kubernetes API client
api_client = client.CoreV1Api()

pod_name = "gw"
image = "lokoai/loko-gateway:0.0.4-dev"

RULES = []
RULES.extend([{"name": "orchestrator", "host": "orchestrator", "port": 8888,
               "type": "orchestrator", "scan": True},
              {"name": "predictor", "host": "predictor", "port": 8080,
               "type": "predictor"}])



apps_v1 = client.AppsV1Api()
api_client = client.CoreV1Api()

DEPLOYMENT_NAME = "mongo-deployment"
SERVICE_NAME = "mongo-service"

CONTAINER_NAME = 'mongo'
IMAGE = 'mongo:4.4'
CONTAINER_PORT = 27017

LABELS = {"app": "mongo"}

REPLICAS = 1

NODE_PORT = 30002
# Configureate Pod template container
container = client.V1Container(
    name=CONTAINER_NAME,
    image=IMAGE,
    ports=[client.V1ContainerPort(container_port=CONTAINER_PORT)],
    resources=client.V1ResourceRequirements(
        requests={"cpu": "100m", "memory": "200Mi"},
        limits={"cpu": "500m", "memory": "500Mi"},
    ),
)

# Deployment
deployment = client.V1Deployment(
    api_version="apps/v1",
    kind="Deployment",
    metadata=client.V1ObjectMeta(name=DEPLOYMENT_NAME),
    spec=client.V1DeploymentSpec(replicas=REPLICAS,
                                 template=client.V1PodTemplateSpec(metadata=client.V1ObjectMeta(labels=LABELS),
                                                                   spec=client.V1PodSpec(containers=[container])),
                                 selector={"matchLabels": LABELS}),
)


resp = apps_v1.create_namespaced_deployment(body=deployment, namespace="default")
print(resp)

# Service
service = client.V1Service(api_version='v1',
                           kind='Service',
                           metadata=client.V1ObjectMeta(name=SERVICE_NAME),
                           spec=client.V1ServiceSpec(selector=LABELS,
                                                     type='LoadBalancer', #'NodePort',
                                                     ports=[client.V1ServicePort(port=CONTAINER_PORT,
                                                                                 node_port=NODE_PORT)]))


api_client.create_namespaced_service(namespace="default", body=service)
print(resp)

api_client.create_namespaced_pod(namespace="default", body=pod)
