default:
    @just --list

check:
    uv run ruff format --check
    uv run ruff check
    uv run pyrefly check

build *apps:
    uv run builder {{apps}}

clean:
    rm -rf temp build

install-apk-fetch:
    uv run python -c "from builder.scripts import APK_FETCH; print(APK_FETCH)"

install-curl:
    uv run python -c "from builder.scripts import CURL; print(CURL)"
