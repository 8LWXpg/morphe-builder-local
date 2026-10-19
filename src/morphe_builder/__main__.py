import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import click

from .app import App
from .config import Config, Patch, PatchKey
from .tools import APK_FETCH
from .util import logger_setup

logger = logging.getLogger(__name__)


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
        # pyrefly: ignore [implicit-any-lambda]
        results = list(ex.map(lambda k: (k, k.download()), patch_keys))

    patches = {k: v for k, v in results if v is not None}
    changelog.extend(v.changelog for _, v in results if v is not None)

    apps = config_to_app(cfg, patches, cli)
    if len(app) != 0:
        apps = [a for a in apps if a.spec.app_name in app]
    with ThreadPoolExecutor(cfg.parallel_jobs) as ex:
        # pyrefly: ignore[implicit-any-lambda]
        outs: list[Path | None] = list(ex.map(lambda a: a.build(APK_FETCH()), apps))

    tag = datetime.now().strftime("%Y.%m.%d")
    notes = "\n".join(changelog)
    files = [str(p) for p in outs if p is not None]
    if len(files) == 0:
        logger.error("all build failed")
        return

    exists = (
        subprocess.run(
            ["gh", "release", "view", tag],
            capture_output=True,
        ).returncode
        == 0
    )

    if exists:
        logger.info("updating existing release %s...", tag)
        subprocess.run(["gh", "release", "upload", tag, *files, "--clobber"], check=True)
        subprocess.run(
            ["gh", "release", "edit", tag, "-n", notes, "-t", "Morphe Build"], check=True
        )
    else:
        logger.info("creating release %s...", tag)
        subprocess.run(
            ["gh", "release", "create", tag, *files, "-n", notes, "-t", "Morphe Build"],
            check=True,
        )


if __name__ == "__main__":
    logger_setup()
    main()
