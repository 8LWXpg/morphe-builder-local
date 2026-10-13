import tomllib
from pathlib import Path
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

# app versions: 2+ components, any suffix (12.19.1-release.0, 1.2, 2026.24.0)
APK_VERSION_RE = r"^(auto|experimental|latest|v?\d+(\.\d+)*(-.*)?)$"
ApkVersion = Annotated[str, StringConstraints(pattern=APK_VERSION_RE)]

# morphe patches / cli tags: always vX.Y.Z or vX.Y.Z-dev.N, the v is optional
PATCH_VERSION_RE = r"^(latest|dev|v?\d+\.\d+\.\d+(-dev\.\d+)?)$"
PatchVersion = Annotated[str, StringConstraints(pattern=PATCH_VERSION_RE)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=lambda name: name.replace("_", "-"))


class AppConfig(Model):
    enabled: bool = True
    package_id: str
    app_name: str
    patch_source: str = "MorpheApp/morphe-patches"
    patch_version: PatchVersion = "latest"
    version: ApkVersion = "auto"
    archive_dlurl: str = ""
    included_patches: list[str] = []
    excluded_patches: list[str] = []
    exclusive_patches: bool = False
    patcher_args: str = ""


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
        apps = {name: {"app-name": name, **table} for name, table in raw.items() if isinstance(table, dict)}
        return {**scalars, "apps": apps}

    @classmethod
    def load(cls, path: str | Path = "config.toml") -> Self:
        with Path(path).open("rb") as f:
            return cls.model_validate(tomllib.load(f))
