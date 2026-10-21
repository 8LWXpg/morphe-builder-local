import json
from pathlib import Path

from .config import AppConfig, Config


def build_schema() -> dict[str, object]:
    cfg = Config.model_json_schema()
    app = AppConfig.model_json_schema()

    defs = {**cfg.get("$defs", {}), **app.pop("$defs", {})}
    defs.pop("AppConfig", None)

    # app-name defaults to the table name, so it's not required in the file
    app["required"] = [r for r in app.get("required", []) if r != "app-name"]
    app.pop("title", None)

    props = {k: v for k, v in cfg["properties"].items() if k != "apps"}
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "morphe-builder config",
        "type": "object",
        "properties": props,
        "additionalProperties": app,
        "$defs": defs,
    }


if __name__ == "__main__":
    Path("config.schema.json").write_text(json.dumps(build_schema(), indent=2) + "\n")
