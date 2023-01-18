import docker

# Create a Docker client
client = docker.from_env()

# Find the container by name
container = client.containers.get('orchestrator')

# Open the local file to be copied
# with open('/path/to/local/file', 'rb') as src_file:
# Copy the file to the container
#    container.put(src_file, '/path/to/destination/file')
print(container.exec_run("ls /home/loko/"))

with open("twos.yaml") as o:
    container.put(o, "/home/loko/twos.yaml")
