import shutil
from pathlib import Path

from loko_cli.model.loko import Project


class Planner:
    def __init__(self):
        pass

    def plan(self, project: Project):
        pass


class DestPlanner(Planner):
    def __init__(self, output_dir: Path = None, version="0.1"):
        super().__init__()
        self.output_dir = Path(output_dir or f"dist/docker_compose/{version}")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.version = version

    def clean(self):
        shutil.rmtree(self.output_dir)
