import asyncio
import os
from pathlib import Path

import click

import loko_cli.apps.total as tt
from loguru import logger


@click.group()
def loko():
    pass


@loko.command()
@click.option('--push', default=True, help='Push on registry')
@click.option('--company', required=True, type=str, help='Company name or private registry')
@click.option('--gateway_port', default=8080, type=int, help='the gateway public port (default:8080)')
def plan(push, company, gateway_port):
    """Simple program that greets NAME for a total of COUNT times."""
    logger.debug("Planning")
    asyncio.run(tt.plan(Path(os.getcwd()), push=push, company=company, gateway_port=gateway_port))


@loko.command()
@click.option("--target", default="ec2", type=click.Choice(["ec2"]))
@click.option("--name", required=True, type=str)
@click.option("--instance_type", default="t2.micro", type=str)
def init(target, name, instance_type):
    """dddd"""
    p = Path(os.getcwd())
    asyncio.run(tt.init(p, name, instance_type))


@loko.command()
def deploy():
    """dddd"""
    p = Path(os.getcwd())
    asyncio.run(tt.deploy(p))


if __name__ == '__main__':
    print(os.getcwd())
    # asyncio.run(plan(Path(os.getcwd()), company="livetechprove"))
    loko()
