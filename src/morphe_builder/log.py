import logging
import os
from typing import override

GREEN = "\033[0;32m"
RED = "\033[0;31m"
RESET = "\033[0m"

ROOT = "morphe"


class _Formatter(logging.Formatter):
	@override
	def format(self, record: logging.LogRecord) -> str:
		msg = record.getMessage()
		if record.levelno < logging.WARNING:
			return f"{GREEN}[+] {msg}{RESET}"
		if os.environ.get("GITHUB_REPOSITORY"):
			msg += f"\n::error::builder [-] {record.getMessage()}"
		return f"{RED}[-] {msg}{RESET}"


def setup(level: int = logging.INFO) -> None:
	log = logging.getLogger(ROOT)
	log.handlers.clear()  # idempotent
	handler = logging.StreamHandler()
	handler.setFormatter(_Formatter())
	log.addHandler(handler)
	log.setLevel(level)
	log.propagate = False


def get(name: str) -> logging.Logger:
	return logging.getLogger(f"{ROOT}.{name}")
