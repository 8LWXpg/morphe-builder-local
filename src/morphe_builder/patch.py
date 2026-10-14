import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .config import Config, PatchVersion
from .download import BIN_DIR, gh, gh_asset
from .log import setup

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
                version = gh("release", "list", "-R", self.source, "--json", "tagName", "-L", "1", "-q", ".[0].tagName")
            case "latest":
                version = gh("release", "view", "-R", self.source, "--json", "tagName", "-q", ".tagName")

        dir = BIN_DIR / self.source
        dir.mkdir(parents=True, exist_ok=True)
        asset_name = f"patches-{version.removeprefix('v')}.mpp"
        mpp = dir / asset_name
        changelog = dir / f"changelog-{version.removeprefix('v')}.md"
        if mpp.exists() and changelog.exists():
            return Patch(mpp, changelog.read_text())

        gh_asset(self.source, [asset_name], dir, version)
        note = f"""Patches: {self.source}/{asset_name}
\n[Changelog](https://github.com/{self.source}/releases/tag/{self.version})"""
        changelog.write_text(note)

        return Patch(mpp, note)


def resolve_patches(cfg: Config) -> dict[PatchKey, Patch]:
    keys = {PatchKey(a.patch_source, a.patch_version) for a in cfg.apps.values() if a.enabled}
    return {k: v for k in keys if (v := k.download()) is not None}


def fetch_cli(version: PatchVersion) -> tuple[Path, str]:
    morphe_desktop: Final = "MorpheApp/morphe-desktop"

    match version:
        case "dev":
            version = gh(
                "release",
                "list",
                "-R",
                morphe_desktop,
                "--json",
                "tagName",
                "-L",
                "1",
                "-q",
                ".[0].tagName",
            )
        case "latest":
            version = gh("release", "view", "-R", morphe_desktop, "--json", "tagName", "-q", ".tagName")
    dir = BIN_DIR / morphe_desktop
    dir.mkdir(parents=True, exist_ok=True)
    asset_name = f"morphe-desktop-{version.removeprefix('v')}-all.jar"
    jar = dir / asset_name
    changelog = dir / f"changelog-{version.removeprefix('v')}.md"
    if jar.exists() and changelog.exists():
        return (jar, changelog.read_text())

    gh_asset(morphe_desktop, [asset_name], dir, version)
    note = f"""Morphe Desktop: {asset_name}
\n[Changelog](https://github.com/{morphe_desktop}/release/tag/{version})"""
    changelog.write_text(note)

    return (jar, note)


if __name__ == "__main__":
    setup()
