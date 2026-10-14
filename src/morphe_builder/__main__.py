from .config import Config
from .patch import fetch_cli, resolve_patches


def main():
    cfg = Config.load()
    changelog: list[str] = []
    (cli, note) = fetch_cli(cfg.cli_version)
    changelog.append(note)
    patches = resolve_patches(cfg)


if __name__ == "__main__":
    main()
