import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Final, NamedTuple, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

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
    model_config = ConfigDict(extra="forbid", alias_generator=lambda n: n.replace("_", "-"))


FilePatch = str | dict[str, dict[str, str]]  # "Name" | { "Name" = { opt = "v" } }


class FileApp(Model):
    enabled: bool = True
    package_id: str
    app_name: str | None = None
    patch_source: str = "MorpheApp/morphe-patches"
    patch_version: PatchVersion = "latest"
    version: ApkVersion = "latest"
    archive_dlurl: str = ""
    included_patches: list[FilePatch] = []
    excluded_patches: list[str] = []
    exclusive_patches: bool = False
    patcher_args: list[str] = []


class FileConfig(Model):
    model_config = ConfigDict(extra="allow")  # merged with Model's config

    parallel_jobs: int = 1
    cli_version: PatchVersion = "latest"
    # every unknown top-level table is an app
    # pyrefly: ignore[bad-override-mutable-attribute]
    __pydantic_extra__: dict[str, FileApp] = Field(init=False)


class PatchInclude(NamedTuple):
    name: str
    options: dict[str, str]

    @classmethod
    def from_file(cls, v: FilePatch) -> Self:
        if isinstance(v, str):
            return cls(v, {})
        if len(v) != 1:
            raise ValueError(f"patch table must have exactly one key, got {list(v)}")
        ((name, opts),) = v.items()
        return cls(name, opts)


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    package_id: str
    patch_source: str
    patch_version: str
    version: str
    archive_dlurl: str
    included_patches: list[PatchInclude]
    excluded_patches: list[str]
    exclusive_patches: bool
    patcher_args: list[str]

    @classmethod
    def from_file(cls, name: str, f: FileApp) -> Self:
        return cls(
            app_name=f.app_name or name,
            package_id=f.package_id,
            patch_source=f.patch_source,
            patch_version=f.patch_version,
            version=f.version,
            archive_dlurl=f.archive_dlurl,
            included_patches=[PatchInclude.from_file(p) for p in f.included_patches],
            excluded_patches=f.excluded_patches,
            exclusive_patches=f.exclusive_patches,
            patcher_args=f.patcher_args,
        )


@dataclass
class Config:
    parallel_jobs: int
    cli_version: str
    apps: list[AppConfig] = field(default_factory=list)

    @classmethod
    def from_file(cls, f: FileConfig) -> Self:
        extra = f.__pydantic_extra__ or {}
        return cls(
            f.parallel_jobs,
            f.cli_version,
            [AppConfig.from_file(n, a) for n, a in extra.items() if a.enabled],
        )

    @classmethod
    def load(cls, path: str | Path = "config.toml") -> Self:
        with Path(path).open("rb") as fh:
            return cls.from_file(FileConfig.model_validate(tomllib.load(fh)))

    def patches(self) -> set[PatchKey]:
        return {PatchKey(a.patch_source, a.patch_version) for a in self.apps}

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
