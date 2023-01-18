from kubernetes import client, config

# configure the client
config.load_kube_config(config_file='/etc/rancher/k3s/k3s.yaml')

api_instance = client.CoreV1Api()

# create the Persistent Volume
pv_manifest = client.V1PersistentVolume(
    api_version="v1",
    kind="PersistentVolume",
    metadata=client.V1ObjectMeta(
        name="my-pv",
    ),
    spec=client.V1PersistentVolumeSpec(
        storage_class_name="local-storage",
        capacity={"storage": "10Gi"},
        access_modes=["ReadWriteOnce"],
        host_path=client.V1HostPathVolumeSource(
            path="/root/loko"
        )
    )
)
api_instance.create_persistent_volume(body=pv_manifest)
