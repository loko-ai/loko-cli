from pathlib import Path
from typing import List

import paramiko
from azure.identity import AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import SubscriptionClient
from loguru import logger

class AzureVM:
    def __init__(self, id, network_client, compute_client):

        self.id = id
        self.rg_name, self.name = self._get_group_name(id)
        self.network_client = network_client
        self.compute_client = compute_client

        self._vm = None
        self._nic = None
        self._ip = None
        self._os_disk = None

        self._state = None
        self._public_dns_name = None
        self._public_ip_address = None


    def _get_group_name(self, id):
        reference = id.split('/')
        return reference[4], reference[8]

    @property
    def vm(self):
        if not self._vm:
            self._vm = self.compute_client.virtual_machines.get(vm_name=self.name,
                                                                resource_group_name=self.rg_name,
                                                                expand='instanceView')
        return self._vm

    @property
    def nic(self):
        if not self._nic:
            ni_group, ni_name = self._get_group_name(self.vm.network_profile.network_interfaces[0].id)

            self._nic = self.network_client.network_interfaces.get(resource_group_name=ni_group,
                                                                   network_interface_name=ni_name)

        return self._nic

    @property
    def ip(self):
        if not self._ip:
            ip_group, ip_name = self._get_group_name(self.nic.ip_configurations[0].id)
            self._ip = self.network_client.public_ip_addresses.get(public_ip_address_name=ip_name,
                                                                   resource_group_name=ip_group)
        return self._ip

    @property
    def os_disk(self):
        if not self._os_disk:
            os_disk_name = self.vm.storage_profile.os_disk.name
            self._os_disk = self.compute_client.disks.get(disk_name=os_disk_name,
                                                          resource_group_name=self.rg_name)
        return self._os_disk
    @property
    def state(self):
        if not self._state:
            self._state = dict(Name=self.vm.instance_view.statuses[1].display_status.replace('VM ', ''))
        return self._state

    @property
    def public_dns_name(self):
        if not self._public_dns_name:
            self._public_dns_name = self.ip.ip_address
        return self._public_dns_name

    @property
    def public_ip_address(self):
        return self.public_dns_name

    def terminate(self):
        vm = self.vm
        logger.debug(f'Deleting VM: {self.name}')
        self.compute_client.virtual_machines.begin_delete(vm_name=self.name,
                                                          resource_group_name=self.rg_name).wait()

        ni_group, ni_name = self._get_group_name(self.nic.id)
        logger.debug(f'Deleting NIC: {ni_name}')
        self.network_client.network_interfaces.begin_delete(network_interface_name=ni_name,
                                                            resource_group_name=ni_group).wait()

        ip_group, ip_name = self._get_group_name(self.ip.id)
        logger.debug(f'Deleting IP address: {ip_name}')
        self.network_client.public_ip_addresses.begin_delete(public_ip_address_name=ip_name,
                                                             resource_group_name=ip_group).wait()

        os_disk_name = vm.storage_profile.os_disk.name
        logger.debug(f'Deleting Disk: {os_disk_name}')
        self.compute_client.disks.begin_delete(disk_name=os_disk_name, resource_group_name=self.rg_name).wait()

class AzureManager:
    def __init__(self, region_name='westeurope', pem=None):

        self.region_name = region_name
        credential = AzureCliCredential()
        subscription_client = SubscriptionClient(credential)
        subscription_id = subscription_client.subscriptions.list().next().subscription_id
        self.network_client = NetworkManagementClient(credential, subscription_id)
        self.compute_client = ComputeManagementClient(credential, subscription_id)

        if isinstance(pem, str):
            pem = Path(pem)
        self.pem = pem

    def get(self, id):
        try:
            return AzureVM(id, self.network_client, self.compute_client)
        except Exception as e:
            raise Exception("Instance not found")

    def _create_ip_address(self, name, rg_name):
        poller = self.network_client.public_ip_addresses.begin_create_or_update(rg_name, name,
                                                                                {"location": self.region_name,
                                                                                 "sku": {"name": "Standard"},
                                                                                 "public_ip_allocation_method": "Static",
                                                                                 "public_ip_address_version": "IPV4"
                                                                                 })

        ip_address = poller.result()
        logger.debug(f"Provisioned public IP address {ip_address.name} with address {ip_address.ip_address}")

        return ip_address

    def _create_network_interface(self, name, rg_name, ip_add_name, sg_id, subnet_id, ip_add_id):
        poller = self.network_client.network_interfaces.begin_create_or_update(rg_name, name,
                                                                               {"location": self.region_name,
                                                                                "ip_configurations": [
                                                                                    {"name": ip_add_name,
                                                                                     "subnet": {"id": subnet_id},
                                                                                     "public_ip_address":
                                                                                         {"id": ip_add_id}
                                                                                     }],
                                                                                'network_security_group':
                                                                                    {'id': sg_id}
                                                                                })

        nic = poller.result()
        logger.debug(f"Provisioned network interface client {nic.name}")

        return nic

    def create(self, name, img='loko', username='ubuntu', rg_name='loko', sg_name='loko', vnet_name='loko',
               instance_type="Standard_B1s", device_volume_size=30):

        logger.debug(f"Provisioning virtual machine {name}; this operation might take a few minutes.")

        logger.debug(f'Security group: {sg_name} - {rg_name}')

        sg = self.network_client.network_security_groups.get(network_security_group_name=sg_name,
                                                             resource_group_name=rg_name)

        logger.debug(f'Virtual network: {vnet_name} - {rg_name}')

        vnet = self.network_client.virtual_networks.get(virtual_network_name=vnet_name,
                                                        resource_group_name=rg_name)

        subnet = self.network_client.subnets.get(subnet_name='default',
                                                 virtual_network_name=vnet_name,
                                                 resource_group_name=sg_name)
        ip_add = self._create_ip_address(name=name, rg_name=rg_name)
        nic = self._create_network_interface(name=name, rg_name=rg_name, ip_add_name=name, sg_id=sg.id,
                                             subnet_id=subnet.id, ip_add_id=ip_add.id)
        pub_key = self.compute_client.ssh_public_keys.get(ssh_public_key_name=self.pem.stem,
                                                          resource_group_name=rg_name).public_key

        img = self.compute_client.images.get(image_name=img, resource_group_name=rg_name)

        storage_profile = {
            "imageReference": {
                "id": img.id
            },
            "os_disk": {
                'caching': 'None',
                'create_option': 'FromImage',
                'disk_size_gb': device_volume_size}}

        hw_profile = {"vm_size": instance_type}

        os_profile = {
            'computer_name': name,
            'admin_username': username,
            "linux_configuration": {
                "disable_password_authentication": True,
                "ssh": {
                    "public_keys": [{
                        "path": f"/home/{username}/.ssh/authorized_keys",
                        "key_data": pub_key
             }]
        }
     }
}

        network_profile = {
            "network_interfaces": [{"id": nic.id}]
        }

        poller = self.compute_client.virtual_machines.begin_create_or_update(rg_name,
                                                                             name,
                                                                             {"location": self.region_name,
                                                                              "storage_profile": storage_profile,
                                                                              "hardware_profile": hw_profile,
                                                                              "os_profile": os_profile,
                                                                              "network_profile": network_profile})

        vm = poller.result()

        logger.debug(f"Provisioned virtual machine {vm.name}")

        return vm

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