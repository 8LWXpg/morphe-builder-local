import platform
import subprocess
from itertools import chain
from pathlib import Path

BIN_DIR = Path("bin")

ARCH = platform.machine().lower().replace("amd64", "x86_64").replace("arm64", "aarch64")


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout.strip()


def _download(repo: str, patterns: list[str], dir: Path, tag: str = "") -> None:
    subprocess.run(
        [
            "gh",
            "release",
            "download",
            tag,
            "-R",
            repo,
            *chain.from_iterable(("-p", p) for p in patterns),
            "-D",
            str(dir),
        ],
        check=True,
    )
