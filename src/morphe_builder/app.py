import logging
import subprocess
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Self

from .config import AppConfig, Patch, PatchKey
from .tools import ApkFetch
from .util import APK_DIR

logger = logging.getLogger(__name__)


@dataclass
class App:
    spec: AppConfig
    patch: Patch
    cli: Path

    @classmethod
    def from_appconfig(
        cls, spec: AppConfig, patches: dict[PatchKey, Patch], cli: Path
    ) -> Self | None:
        patch = patches.get(PatchKey(spec.patch_source, spec.patch_version))
        if patch is None:
            logger.error(f"{spec.patch_source}:{spec.patch_version} is not downloaded")
            return None
        else:
            return cls(spec, patch, cli)

    def build(self, apk_fetch: ApkFetch) -> Path | None:
        ver = self._parse_ver()
        logger.info(f"Chose '{ver}' for '{self.spec.package_id}'")
        apk = apk_fetch.get(self.spec.package_id, ver, APK_DIR)
        if apk is None:
            return None

        out = APK_DIR / f"out/{self.spec.package_id}-{ver}.apk"
        try:
            subprocess.run(
                [
                    "java",
                    "-jar",
                    self.cli,
                    "patch",
                    apk,
                    *chain.from_iterable(("-d", d) for d in self.spec.excluded_patches),
                    *chain.from_iterable(("-e", e) for e in self.spec.included_patches),
                    *(["--excllusive"] if self.spec.exclusive_patches else []),
                    "--keystore=Morphe.keystore",
                    "-p",
                    self.patch.mpp,
                    "--striplibs=arm64-v8a",
                    "-o",
                    out,
                    *(self.spec.patcher_args),
                ],
                check=True,
            )
            return out
        except Exception:
            return None

    def _parse_ver(self):
        if self.spec.version not in ["dev", "latest"]:
            return self.spec.version

        return (
            subprocess.run(
                [
                    "java",
                    "-jar",
                    self.cli,
                    "list-versions",
                    f"--patches={self.patch.mpp}",
                    f"-f={self.spec.package_id}",
                    *(["-x"] if self.spec.version == "dev" else []),
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            .stdout.strip()
            .split("\n")[2]
            .split()[0]
        )
