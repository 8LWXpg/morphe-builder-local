from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

from .config import Config, Patch, PatchKey
from .tools import APK_FETCH


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


if __name__ == "__main__":
    main()
