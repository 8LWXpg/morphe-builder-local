import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Final, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from .util import BIN_DIR, gh, gh_asset

logger = logging.getLogger(__name__)

# app versions: 2+ components, any suffix (12.19.1-release.0, 1.2, 2026.24.0)
APK_VERSION_RE = r"^(latest|dev|v?\d+(\.\d+)*(-.*)?)$"
ApkVersion = Annotated[str, StringConstraints(pattern=APK_VERSION_RE)]

# morphe patches / cli tags: always vX.Y.Z or vX.Y.Z-dev.N, the v is optional
PATCH_VERSION_RE = r"^(latest|dev|v?\d+\.\d+\.\d+(-dev\.\d+)?)$"
PatchVersion = Annotated[str, StringConstraints(pattern=PATCH_VERSION_RE)]


@dataclass
class Patch:
    mpp: Path
    changelog: str


@dataclass(frozen=True)
class PatchKey:
    source: str
    version: PatchVersion

    def download(self) -> Patch | None:
        try:
            # Resolved to version
            version = self.version
            match self.version:
                case "dev":
                    version = gh(
                        "release",
                        "list",
                        "-R",
                        self.source,
                        "--json",
                        "tagName",
                        "-L",
                        "1",
                        "-q",
                        ".[0].tagName",
                    )
                case "latest":
                    version = gh(
                        "release", "view", "-R", self.source, "--json", "tagName", "-q", ".tagName"
                    )

            dir = BIN_DIR / self.source
            dir.mkdir(parents=True, exist_ok=True)
            asset_name = f"patches-{version.removeprefix('v')}.mpp"
            mpp = dir / asset_name
            changelog = dir / f"changelog-{version.removeprefix('v')}.md"
            if mpp.exists() and changelog.exists():
                logger.info(f"{self.source}:{version} already installed at {dir}")
                return Patch(mpp, changelog.read_text())

            gh_asset(self.source, [asset_name], dir, version)
            note = f"Patches: {self.source}/{asset_name}\n[Changelog](https://github.com/{self.source}/releases/tag/{self.version})"
            changelog.write_text(note)
            logger.info(f"{self.source}:{version} installed at {dir}")

            return Patch(mpp, note)
        except Exception as e:
            logger.error(e)
            return None


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=lambda name: name.replace("_", "-"))


class AppConfig(Model):
    enabled: bool = True
    package_id: str
    app_name: str
    patch_source: str = "MorpheApp/morphe-patches"
    patch_version: PatchVersion = "latest"
    version: ApkVersion = "latest"
    archive_dlurl: str = ""
    included_patches: list[str] = []
    excluded_patches: list[str] = []
    exclusive_patches: bool = False
    patcher_args: list[str] = []


class Config(Model):
    parallel_jobs: int = 1
    cli_version: PatchVersion = "latest"
    apps: dict[str, AppConfig]

    @model_validator(mode="before")
    @classmethod
    def _group_apps(cls, raw: Any) -> Any:
        if not isinstance(raw, dict):
            return raw
        scalars = {k: v for k, v in raw.items() if not isinstance(v, dict)}
        apps = {
            name: {"app-name": name, **table}
            for name, table in raw.items()
            if isinstance(table, dict) and table.get("enabled") in (True, None)
        }
        return {**scalars, "apps": apps}

    @classmethod
    def load(cls, path: str | Path = "config.toml") -> Self:
        with Path(path).open("rb") as f:
            return cls.model_validate(tomllib.load(f))

    def patches(self) -> set[PatchKey]:
        return {PatchKey(a.patch_source, a.patch_version) for a in self.apps.values() if a.enabled}

    def fetch_cli(self) -> tuple[Path, str]:
        morphe_desktop: Final = "MorpheApp/morphe-desktop"

        match self.cli_version:
            case "dev":
                self.cli_version = gh(
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
                self.cli_version = gh(
                    "release", "view", "-R", morphe_desktop, "--json", "tagName", "-q", ".tagName"
                )
        dir = BIN_DIR / morphe_desktop
        dir.mkdir(parents=True, exist_ok=True)
        asset_name = f"morphe-desktop-{self.cli_version.removeprefix('v')}-all.jar"
        jar = dir / asset_name
        changelog = dir / f"changelog-{self.cli_version.removeprefix('v')}.md"
        if jar.exists() and changelog.exists():
            return (jar, changelog.read_text())

        gh_asset(morphe_desktop, [asset_name], dir, self.cli_version)
        note = f"Morphe Desktop: {asset_name}\n[Changelog](https://github.com/{morphe_desktop}/release/tag/{self.cli_version})"
        changelog.write_text(note)

        return (jar, note)
