_default:
    @just --list

check:
    uv run ruff format --check
    uv run ruff check
    uv run pyrefly check

ipython:
    uv run ipython

clean:
    rm -rf temp build

install_tools:
    uv run -m morphe_builder.tools
