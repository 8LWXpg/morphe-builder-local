from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .app import App
from .config import Config, Patch, PatchKey
from .tools import APK_FETCH
from .util import logger_setup


def config_to_app(cfg: Config, patches: dict[PatchKey, Patch], cli: Path) -> list[App]:
    return [
        app for _, a in cfg.apps.items() if (app := App.from_appconfig(a, patches, cli)) is not None
    ]


def main():
    APK_FETCH()
    cfg = Config.load()
    changelog: list[str] = []
    (cli, note) = cfg.fetch_cli()
    changelog.append(note)

    patch_keys = cfg.patches()
    patches: dict[PatchKey, Patch] = {}
    with ThreadPoolExecutor(cfg.parallel_jobs) as ex:
        results: Iterator[tuple[PatchKey, Patch]] = ex.map(lambda k: (k, k.download()), patch_keys)  # pyrefly: ignore [implicit-any-lambda]
        patches = {k: v for k, v in results if v is not None}

    apps = config_to_app(cfg, patches, cli)
    with ThreadPoolExecutor(cfg.parallel_jobs) as ex:
        results = ex.map(lambda a: a.build(patches), apps)  # pyrefly: ignore [implicit-any-lambda]


if __name__ == "__main__":
    logger_setup()
    main()
