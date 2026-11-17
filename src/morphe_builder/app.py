import logging
import subprocess
import traceback
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
                    *self._patch_args(),
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
            logger.info("built %s", out.name)
            return out
        except Exception:
            traceback.print_exc(limit=3)
            return None

    def _patch_args(self) -> list[str]:
        """Generate args for `excluded_patches`, `included_patches` and `exclusive_patches`"""
        s = self.spec
        args = list(chain.from_iterable(("-d", d) for d in s.excluded_patches))
        for name, opts in s.included_patches:
            args += ["-e", name]
            args += [f"-O{k}={v}" for k, v in opts.items()]
        if self.spec.exclusive_patches:
            args.append("--exclusive")
        return args

    def _parse_ver(self):
        """
        Parse output that should looks like following:

        ```
        INFO: Morphe data root: bin/MorpheApp/morphe-desktop/morphe-data (JAR-adjacent)
        INFO: Package name: com.google.android.youtube
        Most common compatible versions:
            21.13.164 (74 patches)
            20.05.46 (74 patches)
        ```
        """

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
            .split("\n")[3]
            .split()[0]
        )
