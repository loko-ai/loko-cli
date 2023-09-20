import asyncio
import os
import sys
from pathlib import Path

import click

import loko_cli.apps.total as tt
from loguru import logger


@click.group(name="loko", help="version 0.0.6")
@click.option('--verbose', is_flag=True, show_default=True, help='Verbose output')
def loko(verbose):
    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level='INFO')
    pass

@loko.command()
@click.option('--push', default=True, help='Push on registry', show_default=True)
@click.option('--company', required=True, type=str, help='Company name or private registry')
@click.option('--gateway_port', default=8080, type=int, help='the gateway public port', show_default=True)
@click.option('--https', default=True, type=bool, help='Expose services through https', show_default=True)
@click.option('--overwrite', default=True, type=bool, help='Overwrite deployment files', show_default=True)
@click.option("--no-cache", is_flag=True, help='Build docker images not using docker cache',
              show_default=True)
def plan(push, company, gateway_port, https, overwrite, no_cache):
    """Prepare the plan for the deployment of the Loko project"""
    logger.info("Planning")
    asyncio.run(tt.plan(Path(os.getcwd()), push=push, company=company, gateway_port=gateway_port, https=https,
                        overwrite=overwrite, no_cache=no_cache))


@loko.command()
@click.option("--name", required=True, type=str, help="the name of the instance")
@click.option("--region_name", default=None, type=str, help="the region name of the instance")
@click.option("--security_group", default="default", help="the security group associated to the instance",
              show_default=True, type=str)
@click.option("--instance_type", default="t2.micro", help="the instance type", show_default=True, type=str)
@click.option("--ami", default="ami-0a691527202ea8b3d", help="the instance ami", show_default=True, type=str)
@click.option("--device_volume_size", default=30, help="the instance volume size in GigaBytes", show_default=True,
              type=int)
@click.option("--pem", default=Path.home() / "loko.pem", help="the SSH Key path", show_default=True, type=str)
def ec2(name, region_name, security_group, instance_type, ami, device_volume_size, pem):
    """Manage ec2 instances"""
    p = Path(os.getcwd())
    asyncio.run(tt.init_ec2(p, name, instance_type, ami, security_group, device_volume_size, pem, region_name))


@loko.command()
@click.option("--name", required=True, type=str, help="the name of the VM")
@click.option("--region_name", default='westeurope', type=str, help="the region name of the instance",
              show_default=True)
@click.option("--resource_group", default="loko", type=str, help="the name of the resource group", show_default=True)
@click.option("--security_group", default="loko", help="the security group associated to the instance",
              show_default=True, type=str)
@click.option("--virtual_network", default="loko", help="the virtual network associated to the instance",
              show_default=True, type=str)
@click.option("--instance_type", default="Standard_B1s", help="the instance type", show_default=True, type=str)
@click.option("--img", default="loko", help="the vm image", show_default=True, type=str)
@click.option("--device_volume_size", default=30, help="the instance volume size in GigaBytes", show_default=True,
              type=int)
@click.option("--pem", default=Path.home() / "loko_azure.pem", help="the SSH Key path", show_default=True, type=str)
def azure(name, region_name, resource_group, security_group, virtual_network, instance_type, img, device_volume_size,
          pem):
    """Manage Azure VMs"""
    p = Path(os.getcwd())
    asyncio.run(tt.init_azure(p, name, instance_type, img, resource_group, security_group, virtual_network,
                              device_volume_size, pem, region_name))


@loko.command()
@click.option("--pem", default=Path.home() / "loko.pem", help="the SSH Key path", show_default=True, type=str)
def deploy(pem):
    """Deploy the project"""
    p = Path(os.getcwd())
    asyncio.run(tt.deploy(p, pem))


@loko.command()
def info():
    """Get info about the project status"""
    tt.info()


@loko.command()
def destroy():
    """Destroy instances"""
    tt.destroy()


if __name__ == '__main__':

    try:
        loko()
    except Exception as inst:
        logger.exception(inst)
        sys.exit(1)
