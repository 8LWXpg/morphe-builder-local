from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import click

from .app import App
from .config import Config, Patch, PatchKey
from .tools import APK_FETCH
from .util import gh, logger_setup


def config_to_app(cfg: Config, patches: dict[PatchKey, Patch], cli: Path) -> list[App]:
    return [
        app for _, a in cfg.apps.items() if (app := App.from_appconfig(a, patches, cli)) is not None
    ]


@click.command()
@click.option("--app", multiple=True)
def main(app: list[str]):
    APK_FETCH()
    cfg = Config.load()
    changelog: list[str] = ["## Morphe Build"]
    (cli, note) = cfg.fetch_cli()
    changelog.append(note)

    patch_keys = cfg.patches()
    patches: dict[PatchKey, Patch] = {}
    with ThreadPoolExecutor(cfg.parallel_jobs) as ex:
        results: Iterator[tuple[PatchKey, Patch]] = ex.map(lambda k: (k, k.download()), patch_keys)  # pyrefly: ignore [implicit-any-lambda]
        patches = {k: v for k, v in results if v is not None}
        changelog.extend(str(t[1]) for t in results)

    apps = config_to_app(cfg, patches, cli)
    if len(app) != 0:
        apps = [a for a in apps if a.spec.app_name in app]
    with ThreadPoolExecutor(cfg.parallel_jobs) as ex:
        # pyrefly: ignore[implicit-any-lambda]
        outs: list[Path] = list(ex.map(lambda a: a.build(APK_FETCH()), apps))

    gh(
        "release",
        "create",
        datetime.now().strftime("%Y.%m.%d"),
        *([str(p) for p in outs]),
        "-n",
        "\n".join(changelog),
        "-t",
        "Morphe Build",
    )


if __name__ == "__main__":
    logger_setup()
    main()
