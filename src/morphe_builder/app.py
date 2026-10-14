from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig
from .patch import Patch


@dataclass
class App:
    config: AppConfig
    patch: Patch
    cli: Path

    def build(self) -> Path | None:
        return
