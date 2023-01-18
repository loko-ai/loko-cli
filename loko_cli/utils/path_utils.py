import os
from contextlib import contextmanager
from pathlib import Path


def prepare_docker_ignore(path: Path):
    dockerignore = path / '.dockerignore'
    exclude = None
    if dockerignore.exists():
        with open(dockerignore) as f:
            exclude = list(filter(
                lambda x: x != '' and x[0] != '#',
                [l.strip() for l in f.read().splitlines()]
            ))
    return exclude


@contextmanager
def set_directory(path: Path):
    origin = Path().absolute()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)
