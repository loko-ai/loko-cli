import time
from pathlib import Path
from typing import List

import boto3
import paramiko


def listify(o):
    if not isinstance(o, list):
        return [o]
    else:
        return o


blockDeviceMappings = [
    {
        'DeviceName': "/dev/sda1",
        'Ebs': {
            'DeleteOnTermination': True,
            'VolumeSize': 30,
            'VolumeType': 'gp2'
        }
    },
]


class EC2Manager:
    def __init__(self, region_name='eu-central-1', pem=Path.home() / "loko.pem"):
        self.ec2 = boto3.resource('ec2', region_name=region_name)
        self.pem = pem

    def get(self, id):
        for inst in self.all():
            if inst.id == id:
                return inst
        raise Exception("Instance not found")

    def get_security_group(self, id):
        for g in self.ec2.security_groups.all():
            if g.id == id:
                return g
        raise Exception("Group not found")

    def wait_for(self, id, status_name, t=5):
        while True:
            inst = self.get(id)
            if inst.state['Name'] == status_name:
                return
            time.sleep(t)

    def all(self):
        return self.ec2.instances.all()

    def filter_by_tag(self, **kwargs):
        Filters = []
        for k, v in kwargs.items():
            Filters.append(dict(Name=f"tag:{k}", Values=listify(v)))
        return self.ec2.instances.filter(Filters=Filters)

    def create(self, name, img, security_group="default", instance_type="t2.micro"):
        if security_group == "default":
            args = dict(ImageId=img,
                        MinCount=1,
                        MaxCount=1,
                        InstanceType=instance_type,
                        KeyName=self.pem.stem,
                        BlockDeviceMappings=blockDeviceMappings)
        else:
            args = dict(ImageId=img,
                        MinCount=1,
                        MaxCount=1,
                        InstanceType=instance_type,
                        KeyName=self.pem.stem,
                        BlockDeviceMappings=blockDeviceMappings, SecurityGroupIds=[security_group])

        instances = self.ec2.create_instances(**args)

        instance_id = instances[0].instance_id
        tag = {
            'Key': 'Name',
            'Value': name
        }

        # Add the tag to the instance
        response = self.ec2.create_tags(
            Resources=[instance_id],
            Tags=[tag]
        )
        return instances[0]

    def commands(self, cmds, hostname, username="ubuntu"):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        privkey = paramiko.RSAKey.from_private_key_file(
            self.pem)
        ssh.connect(hostname=hostname,
                    username=username, pkey=privkey)
        for cmd in cmds:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            line = None
            while True:
                line = stderr.readline()
                if not line:
                    break

                yield line
            del stdin, stdout, stderr
        ssh.close()

    def copy(self, paths: List[Path], hostname, username="ubuntu"):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        privkey = paramiko.RSAKey.from_private_key_file(
            self.pem)
        ssh.connect(hostname=hostname,
                    username=username, pkey=privkey)
        ftp_client = ssh.open_sftp()

        for p in paths:
            ftp_client.put(p.resolve(), f"/home/ubuntu/{p.name}")

        ssh.close()


if __name__ == '__main__':
    img = "ami-06ce824c157700cd2"

    m = EC2Manager()
    m.create("fulvio", img)
    finst = None
    while finst is None:
        for inst in m.filter_by_tag(Name="fulvio"):

            if inst.state.get("Name") == "running":
                print(inst, inst.state)
                print(inst.public_dns_name)
                finst = inst
        time.sleep(10)
    name = finst.public_dns_name
    print(name)
    while True:
        try:
            for el in m.commands(["curl -fsSL https://get.docker.com -o get-docker.sh", "sudo sh get-docker.sh",
                                  "sudo usermod -aG docker ubuntu",
                                  'sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose',
                                  'sudo chmod +x /usr/local/bin/docker-compose'],
                                 name):
                print(el)
            m.copy([Path("/home/fulvio/projects/loko-cli/loko_cli/business/deployment/planners/docker-compose.yml")],
                   name)
            for el in m.commands(["docker-compose up -d"], name):
                print(el)
            break
        except Exception as inst:
            print(inst)

"""h = "ec2-3-122-193-162.eu-central-1.compute.amazonaws.com"
 for inst in m.filter_by_tag(Name="Fulvio2"):
     inst.terminate()
     # print("dsdas", inst.public_dns_name)
     for el in m.commands(["curl -fsSL https://get.docker.com -o get-docker.sh", "sudo sh get-docker.sh",
                           "sudo usermod -aG docker ubuntu"], inst.public_dns_name):
         print(el)

 # m.create("Fulvio2", img)

 # for el in m.commands(["curl -fsSL https://get.docker.com -o get-docker.sh", "sudo sh get-docker.sh",
 #                      "sudo usermod -aG docker ubuntu"], h):
 #    print(el)"""
