_default:
    @just --list

build:
    uv run builder

check:
    uv run ruff format --check
    uv run ruff check
    uv run pyrefly check
    uv run lint-imports --no-logo

ipython:
    uv run ipython

clean:
    rm -rf temp build

install_tools:
    uv run -m morphe_builder.tools
