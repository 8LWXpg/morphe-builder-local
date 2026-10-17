import logging
import os
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Self

from pydantic import BaseModel

from .config import ApkVersion
from .util import ARCH, BIN_DIR, Lazy, gh_asset, logger_setup

logger = logging.getLogger(__name__)

CURL_IMPERSONATE_VER = "v2.2.3"
CURL_IMPERSONATE_WRAPPER = "curl_chrome131_android"
APK_FETCH_VER = "v1.2.2"


class Apk(BaseModel):
    path: Path
    provider: str
    version: ApkVersion
    arch: str

    @classmethod
    def from_json(cls, text: str) -> Self:
        return cls.model_validate_json(text)


@dataclass
class ApkFetch:
    path: Path
    curl: Path

    @classmethod
    def install(cls, install_dir: Path, curl_dir: Path) -> Self:
        bin = f"apk-fetch{'.exe' if sys.platform == 'win32' else ''}"
        target = {
            "linux": "unknown-linux-musl",
            "darwin": "apple-darwin",
            "win32": "pc-windows-msvc",
        }[sys.platform]
        archive_dir = f"apk-fetch-{ARCH}-{target}"
        bin_full = (
            install_dir / f"apk-fetch-{APK_FETCH_VER}{'.exe' if sys.platform == 'win32' else ''}"
        )
        if bin_full.exists():
            logger.info(f"apk-fetch already installed at '{bin_full}'")
            return cls(bin_full, cls._install_curl(curl_dir))

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
        return cls(bin_full, cls._install_curl(curl_dir))

    @staticmethod
    def _install_curl(install_dir: Path) -> Path:
        """Installs and use curl-impersonate"""
        bin = f"{CURL_IMPERSONATE_WRAPPER}{'.bat' if sys.platform == 'win32' else ''}"
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

    def get(self, pkg: str, version: ApkVersion, out_dir: Path) -> Path:
        out_apk = out_dir.glob(f"{pkg}-{version}-*")
        for p in out_apk:
            logger.info(f"found {p} on disk")
            return p
        logger.info(f"downloading {pkg}")
        return Apk.from_json(
            subprocess.run(
                [
                    self.path,
                    "get",
                    pkg,
                    "--version",
                    version,
                    "--arch",
                    "arm64-v8a",
                    "--out-dir",
                    out_dir,
                    "--no-progress",
                    "--json",
                ],
                stdout=subprocess.PIPE,
                stderr=None,
                text=True,
                check=True,
                env={**os.environ, "APK_FETCH_CURL": str(self.curl.absolute())},
            ).stdout.strip()
        ).path


APK_FETCH = Lazy(
    partial(
        ApkFetch.install,
        BIN_DIR.joinpath("apk-fetch"),
        BIN_DIR.joinpath("curl-impersonate"),
    )
)

if __name__ == "__main__":
    logger_setup()
    APK_FETCH()
