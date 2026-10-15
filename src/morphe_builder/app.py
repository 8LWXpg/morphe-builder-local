import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from .config import AppConfig, Patch, PatchKey
from .tools import ApkFetch

logger = logging.getLogger(__name__)


@dataclass
class App:
    spec: AppConfig
    patch: Patch
    cli: Path

    @classmethod
    def from_config(cls, spec: AppConfig, patches: dict[PatchKey, Patch], cli: Path) -> Self | None:
        patch = patches.get(PatchKey(spec.patch_source, spec.patch_version))
        if patch is None:
            logger.error(f"{spec.patch_source}:{spec.patch_version} is not downloaded")
            return None
        else:
            return cls(spec, patch, cli)

    def build(self, apk_fetch: ApkFetch) -> Path | None:
        return
