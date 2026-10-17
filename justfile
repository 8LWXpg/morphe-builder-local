_default:
    @just --list

build *args:
    @just check
    uv run -m morphe_builder {{ args }}

check:
    uv run lint-imports --no-logo
    uv run pyrefly check
    uv run ruff format --check
    uv run ruff check

ipython:
    uv run ipython

clean:
    rm -rf temp build

tools:
    uv run -m morphe_builder.tools
