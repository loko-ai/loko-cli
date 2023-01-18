from pathlib import Path

from loko_cli.business.deployment.appliers.appliers import Applier


class DCApplier2(Applier):
    def plan(self,p:Path):
