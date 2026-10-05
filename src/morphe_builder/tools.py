from morphe_builder.log import setup
import os
import json
import logging
import platform
import re
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

from morphe_builder.config import MORPHE_TAG

logger = logging.getLogger(__name__)

BIN_DIR = Path("bin")
CURL_IMPERSONATE_VER = "v2.2.3"

ARCH = platform.machine().lower().replace("amd64", "x86_64").replace("arm64", "aarch64")
MORPHE_VERSION = re.compile(f"latest|dev|{MORPHE_TAG}")


@dataclass
class Exe:
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


def _gh(*args: str) -> str:
	return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def _download(repo: str, pattern: str, dir: Path, tag: str = "") -> None:
	subprocess.run(
		[
			"gh",
			"release",
			"download",
			tag,
			"--repo",
			repo,
			"--pattern",
			pattern,
			"--dir",
			str(dir),
		],
		check=True,
	)


@cache
def prebuilt(repo: str, version: str, kind: str) -> tuple[Path, str]:
	"""a patches bundle or cli jar in bin/, downloaded on first use, plus changelog notes"""
	if not MORPHE_VERSION.fullmatch(version):
		raise RuntimeError(
			f"'{version}' is not a valid option for {kind}-version: expected 'latest', 'dev' or a tag like v1.45.0"
		)
	if version == "dev":
		listing = json.loads(_gh("release", "list", "--repo", repo, "--json", "tagName"))
		tags = [release["tagName"] for release in listing]
		if not tags:
			raise RuntimeError(f"No releases found in '{repo}'")
		# a suffix never wins, same as bash's `sort -s -t- -k1,1Vr`
		version = max(
			tags,
			key=lambda tag: tuple(int(x) for x in tag.split("-")[0].removeprefix("v").split(".")),
		)
	# gh resolves an empty tag to the latest release
	tag = "" if version == "latest" else version
	pattern = "*" if version == "latest" else version.removeprefix("v")

	# keyed by repo, two sources can ship the same asset name
	directory = BIN_DIR / repo.replace("/", "-")
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

	release: dict[str, Any] = json.loads(_gh("release", "view", tag, "--repo", repo, "--json", "tagName,assets"))
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
		return bin_full

	install_dir.mkdir(parents=True, exist_ok=True)
	asset = f"{archive_dir}.zip"
	with tempfile.TemporaryDirectory() as scratch:
		_download("8LWXpg/apk-fetch", asset, Path(scratch))
		with (
			zipfile.ZipFile(Path(scratch) / asset) as archive,
			archive.open(f"{archive_dir}/{bin}") as unpacked,
		):
			bin_full.write_bytes(unpacked.read())
	bin_full.chmod(0o755)
	logger.info("Installed '%s'", bin_full)
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
		return bin_full

	install_dir.mkdir(parents=True, exist_ok=True)
	asset = f"curl-impersonate-{CURL_IMPERSONATE_VER}.{ARCH}-{target}.tar.gz"
	with tempfile.TemporaryDirectory() as scratch:
		_download("lexiforest/curl-impersonate", asset, Path(scratch), CURL_IMPERSONATE_VER)
		subprocess.run(["tar", "-xvzf", f"{scratch}/{asset}", "-C", install_dir], stdout=subprocess.DEVNULL)

	bin_full.chmod(0o755)
	logger.info("Installed '%s'", bin_full)
	return bin_full


CURL = Exe(BIN_DIR.joinpath("curl-impersonate"), install_curl)
APK_FETCH = Exe(BIN_DIR.joinpath("apk-fetch"), install_apk_fetch)

if __name__ == "__main__":
	setup()
