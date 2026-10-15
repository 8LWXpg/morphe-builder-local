_default:
    @just --list

build:
    uv run builder

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
