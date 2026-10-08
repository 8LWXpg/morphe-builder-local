import json
import logging
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Self

from .config import PatchVersion
from .log import setup
from .shared import ARCH, BIN_DIR, _download, _gh

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


@cache
def prebuilt(repo: str, version: PatchVersion, kind: str) -> tuple[Path, str]:
	"""a patches bundle or cli jar in bin/, downloaded on first use, plus changelog notes"""
	if version == "dev":
		version = json.loads(_gh("release", "list", "-R", repo, "--json", "tagName", "-L", "1", "-q", ".[0].tagName"))
	# gh resolves an empty tag to the latest release
	tag = "" if version == "latest" else version
	pattern = "*" if version == "latest" else version.removeprefix("v")

	# keyed by user/repo, two sources can ship the same asset name
	directory = BIN_DIR / repo
	directory.mkdir(parents=True, exist_ok=True)
	globs = [f"*patches-{pattern}.*"] if kind == "patches" else [f"*cli-{pattern}*.jar", f"*desktop-{pattern}*.jar"]
	stable_only = "dev" not in pattern
	for glob in globs:
		for cached in sorted(directory.glob(glob)):
			if cached.name.endswith(".lock") or ".tmp." in cached.name:
				continue
			# a stable tag must never be served a cached dev bundle
			if stable_only and "dev" in cached.name:
				continue
			if not zipfile.is_zipfile(cached):
				# a truncated download or an HTML error page: drop it so it is fetched again
				cached.unlink()
				continue
			logger.info("Using '%s'", cached)
			return cached, ""

	release: dict[str, Any] = json.loads(_gh("release", "view", tag, "-R", repo, "--json", "tagName,assets"))
	# the first asset that is not a signature or a manifest
	asset = next(
		(a["name"] for a in release["assets"] if not a["name"].endswith((".asc", ".json"))),
		None,
	)
	if asset is None:
		raise RuntimeError(f"No asset was found in '{repo}'")
	tag_name = release["tagName"]
	logger.info("Getting '%s/%s' from '%s'", repo, asset, tag_name)
	_download(repo, asset, directory, tag)
	bundle = directory / asset
	# gh writes straight to the target, so validity can only be checked after
	if not zipfile.is_zipfile(bundle):
		bundle.unlink(missing_ok=True)
		raise RuntimeError(f"Corrupt download: {asset}")
	label = "Patches" if kind == "patches" else "CLI"
	note = f"{label}: {repo.split('/')[0]}/{asset}"
	if kind == "patches":
		note += f"\n[Changelog](https://github.com/{repo}/releases/tag/{tag_name})"
	return bundle, note


def install_apk_fetch(install_dir: Path) -> Path:
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
		_download("8LWXpg/apk-fetch", [asset], Path(scratch))
		with (
			zipfile.ZipFile(Path(scratch) / asset) as archive,
			archive.open(f"{archive_dir}/{bin}") as unpacked,
		):
			bin_full.write_bytes(unpacked.read())
	bin_full.chmod(0o755)
	logger.info("apk-fetch installed at '%s'", bin_full)
	return bin_full


def install_curl(install_dir: Path) -> Path:
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
		_download("lexiforest/curl-impersonate", [asset], Path(scratch), CURL_IMPERSONATE_VER)
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

CURL = Installable(BIN_DIR.joinpath("curl-impersonate"), install_curl)
APK_FETCH = Installable(BIN_DIR.joinpath("apk-fetch"), install_apk_fetch)
