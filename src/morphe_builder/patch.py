import logging
from dataclasses import dataclass
from pathlib import Path

from morphe_builder.shared import _download

from .config import Config, PatchVersion
from .log import setup
from .shared import BIN_DIR, _gh

logger = logging.getLogger(__name__)


@dataclass
class Patch:
    mpp: Path
    changelog: str


@dataclass(frozen=True)
class PatchKey:
    source: str
    version: PatchVersion

    def download(self) -> Patch | None:
        # Resolved version
        version = self.version
        match self.version:
            case "dev":
                version = _gh(
                    "release", "list", "-R", self.source, "--json", "tagName", "-L", "1", "-q", ".[0].tagName"
                )
            case "latest":
                version = _gh("release", "view", "-R", self.source, "--json", "tagName", "-q", ".tagName")

        dir = BIN_DIR / self.source
        dir.mkdir(parents=True, exist_ok=True)
        asset_name = f"patches-{version.removeprefix('v')}.mpp"
        mpp = dir / asset_name
        changelog = dir / f"changelog-{version.removeprefix('v')}.md"
        if mpp.exists() and changelog.exists():
            return Patch(mpp, changelog.read_text())

        _download(self.source, [asset_name], dir, version)
        note = f"""Patches: {self.source}/{asset_name}
\n[Changelog](https://github.com/{self.source}/releases/tag/{self.version})"""
        changelog.write_text(note)

        return Patch(mpp, note)


def resolve_bundles(cfg: Config) -> dict[PatchKey, Patch]:
    keys = {PatchKey(a.patch_source, a.patch_version) for a in cfg.apps.values() if a.enabled}
    return {k: v for k in keys if (v := k.download()) is not None}


if __name__ == "__main__":
    setup()
