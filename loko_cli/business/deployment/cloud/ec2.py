import time

import boto3
import paramiko


def listify(o):
    if not isinstance(o, list):
        return [o]
    else:
        return o


class EC2Manager:
    def __init__(self, region_name='eu-central-1', pem="./ec2-keypair.pem"):
        self.ec2 = boto3.resource('ec2', region_name=region_name)
        self.pem = pem

    def all(self):
        return self.ec2.instances.all()

    def filter_by_tag(self, **kwargs):
        Filters = []
        for k, v in kwargs.items():
            Filters.append(dict(Name=f"tag:{k}", Values=listify(v)))
        return self.ec2.instances.filter(Filters=Filters)

    def create(self, name, img):
        instances = self.ec2.create_instances(
            ImageId=img,
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',
            KeyName='ec2-keypair'
        )

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
        return instances

    def commands(self, cmds, hostname, username="ubuntu"):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        privkey = paramiko.RSAKey.from_private_key_file(
            self.pem)
        ssh.connect(hostname=hostname,
                    username=username, pkey=privkey)
        for cmd in cmds:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            yield stdout.read(), stderr.read()
            del stdin, stdout, stderr
        ssh.close()


if __name__ == '__main__':
    img = "ami-06ce824c157700cd2"

    m = EC2Manager()
    m.create("fulvio", img)
    finst = None
    while finst is None:
        for inst in m.filter_by_tag(Name="fulvio"):
            print(inst, inst.state)
            print(inst.public_dns_name)
            if inst.state.get("Name") == "running":
                finst = inst
        time.sleep(10)
    name = finst.public_dns_name
    print(name)
    while True:
        try:
            for el in m.commands(["curl -fsSL https://get.docker.com -o get-docker.sh", "sudo sh get-docker.sh",
                                  "sudo usermod -aG docker ubuntu"], name):
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
