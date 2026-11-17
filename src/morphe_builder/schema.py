import json
from pathlib import Path

from .config import FileConfig


def build_schema() -> dict[str, object]:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "morphe-builder config",
        **FileConfig.model_json_schema(),
    }


if __name__ == "__main__":
    Path("config.schema.json").write_text(json.dumps(build_schema(), indent=2) + "\n")
