import asyncio
import os
import sys
from pathlib import Path

import click

import loko_cli.apps.total as tt
from loguru import logger


@click.group()
@click.option('--verbose', default=False, show_default=True, help='Verbose output')
def loko(verbose):
    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level='INFO')
    pass


@loko.command()
@click.option('--push', default=True, help='Push on registry', show_default=True)
@click.option('--company', required=True, type=str, help='Company name or private registry')
@click.option('--gateway_port', default=8080, type=int, help='the gateway public port', show_default=True)
def plan(push, company, gateway_port):
    """Prepare the plan for the deployment of the Loko project"""
    logger.info("Planning")
    asyncio.run(tt.plan(Path(os.getcwd()), push=push, company=company, gateway_port=gateway_port))


@loko.command()
@click.option("--name", required=True, type=str, help="the name of the instance")
@click.option("--security_group", default="default", help="the security group associated to the instance",
              show_default=True, type=str)
@click.option("--instance_type", default="t2.micro", help="the instance type", show_default=True, type=str)
@click.option("--ami", default="ami-0a691527202ea8b3d", help="the instance ami", show_default=True, type=str)
def ec2(name, security_group, instance_type, ami):
    """Manage ec2 instances"""
    p = Path(os.getcwd())
    asyncio.run(tt.init_ec2(p, name, instance_type, ami, security_group))


@loko.command()
def deploy():
    """Deploy the project"""
    p = Path(os.getcwd())
    asyncio.run(tt.deploy(p))


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
        logger.error(inst)
        sys.exit(1)
