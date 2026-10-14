import logging
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Self

from .download import ARCH, BIN_DIR, gh_asset
from .log import setup

logger = logging.getLogger(__name__)

CURL_IMPERSONATE_VER = "v2.2.3"


@dataclass
class Installable:
    install_dir: Path
    install: Callable[[Path], Path]
    path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.path = self.install(self.install_dir)

    def ensure(self) -> Self:
        if not self.path.exists():
            self.install(self.install_dir)
        return self

    def run(self, *args: str, **kw: Any) -> CompletedProcess[Any]:
        return subprocess.run([self.path, *args], **kw)


def _install_apk_fetch(install_dir: Path) -> Path:
    bin = f"apk-fetch{'.exe' if sys.platform == 'win32' else ''}"
    target = {
        "linux": "unknown-linux-musl",
        "darwin": "apple-darwin",
        "win32": "pc-windows-msvc",
    }[sys.platform]
    archive_dir = f"apk-fetch-{ARCH}-{target}"
    bin_full = install_dir / bin
    if bin_full.exists():
        logger.info(f"apk-fetch already installed at '{bin_full}'")
        return bin_full

    install_dir.mkdir(parents=True, exist_ok=True)
    asset = f"{archive_dir}.zip"
    with tempfile.TemporaryDirectory() as scratch:
        gh_asset("8LWXpg/apk-fetch", [asset], Path(scratch))
        with (
            zipfile.ZipFile(Path(scratch) / asset) as archive,
            archive.open(f"{archive_dir}/{bin}") as unpacked,
        ):
            bin_full.write_bytes(unpacked.read())
    bin_full.chmod(0o755)
    logger.info("apk-fetch installed at '%s'", bin_full)
    return bin_full


def _install_curl(install_dir: Path) -> Path:
    """Installs and use curl-impersonate"""
    bin = f"curl_chrome131_android{'.bat' if sys.platform == 'win32' else ''}"
    target = {
        "linux": "linux-musl",
        "darwin": "macos",
        "win32": "win32",
    }[sys.platform]
    bin_full = install_dir / bin
    if bin_full.exists():
        logger.info(f"curl-impersonate already installed at '{bin_full}'")
        return bin_full

    install_dir.mkdir(parents=True, exist_ok=True)
    asset = f"curl-impersonate-{CURL_IMPERSONATE_VER}.{ARCH}-{target}.tar.gz"
    with tempfile.TemporaryDirectory() as scratch:
        gh_asset("lexiforest/curl-impersonate", [asset], Path(scratch), CURL_IMPERSONATE_VER)
        subprocess.run(
            ["tar", "-xvzf", f"{scratch}/{asset}", "-C", install_dir],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    bin_full.chmod(0o755)
    logger.info("curl-impersonate installed at '%s'", bin_full)
    return bin_full


if __name__ == "__main__":
    setup()

CURL = Installable(BIN_DIR.joinpath("curl-impersonate"), _install_curl)
APK_FETCH = Installable(BIN_DIR.joinpath("apk-fetch"), _install_apk_fetch)
