import logging
import os
import platform
import subprocess
import threading
from collections.abc import Callable
from itertools import chain
from pathlib import Path
from typing import override

# region log
GREEN = "\033[0;32m"
RED = "\033[0;31m"
RESET = "\033[0m"

ROOT = __name__.split(".")[0]


class _Formatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        if record.levelno < logging.WARNING:
            return f"{GREEN}[+]{RESET} {msg}"
        if os.environ.get("GITHUB_REPOSITORY"):
            msg += f"\n::error::builder [-] {record.getMessage()}"
        return f"{RED}[-]{RESET} {msg}"


def logger_setup(level: int = logging.INFO) -> None:
    log = logging.getLogger()
    log.handlers.clear()  # idempotent
    handler = logging.StreamHandler()
    handler.setFormatter(_Formatter())
    log.addHandler(handler)
    log.setLevel(level)
    log.propagate = False


# endregion

# region download
BIN_DIR = Path("bin")
APK_DIR = Path("build")
ARCH = platform.machine().lower().replace("amd64", "x86_64").replace("arm64", "aarch64")


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout.strip()


def gh_asset(repo: str, patterns: list[str], dir: Path, tag: str = "") -> None:
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
            dir,
        ],
        check=True,
    )


# endregion


class Lazy[T]:
    """
    Lazily evaluated values, retrieve value with Lazy[T]()
    """

    __slots__ = ("_done", "_fn", "_lock", "_value")

    def __init__(self, fn: Callable[[], T]) -> None:
        self._fn: Callable[[], T] | None = fn
        self._lock = threading.Lock()
        self._done = False

    def get(self) -> T:
        if not self._done:
            with self._lock:
                self._value = self._fn()  # type: ignore[misc]
                self._done = True
                self._fn = None
        return self._value

    __call__ = get
