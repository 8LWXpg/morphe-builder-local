# Architecture

Port of `build.sh` / `utils.sh` / `dl-apk.sh` to Python. Bash files stay until sign-off.

## 1. Function map

| bash | python |
| --- | --- |
| `toml_prep`, `toml_get*` | `config.py: load()` (pydantic) |
| `vtf` | deleted, pydantic `bool` |
| `pr`, `epr` | `log.py: setup()`, one `logging.getLogger("builder")` per module |
| `abort` | `__main__.py: abort()` (raises `SystemExit`) |
| `_clean_tmp` | `tempfile.TemporaryDirectory` + delete `<out>.apkm` leftovers |
| `get_prebuilts` | `scripts.py: prebuilt()` (cached, downloads into `bin/`) |
| `get_highest_ver` | `patch.py: highest()` (a `max` with a key, no sort) |
| `get_patch_last_supported_ver` | `patch.py: resolve_version()` |
| `cli` | `patch.py: run_cli()` |
| `patch_apk` | `patch.py: patch_apk()` |
| `check_sig`, `APKSIGNER` | deleted, see signatures below |
| `build_rv` | `__main__.py: build_app()` |
| `log` | `__main__.py:` joins returned strings into `build.md` |
| `list_args`, `join_args` | deleted, TOML lists are real lists |
| `dl-apk.sh` `place()` | `download.py: download()` |
| workflow install steps | `scripts.py: install_apk_fetch()`, `install_curl()` |

## 2. Decisions

**One lazy `bin/`.** `bin/` is the single tool cache. Everything external
resolves through `scripts.py` and lands there: cli jar, patches jar, apk-fetch,
the curl shim. Each accessor is `@cache`d, so it downloads once per
run and reuses the file on every later run. No `sudo`, no `/usr/local/bin`, no
workflow install steps. `__main__` prepends `bin/` to `PATH` so apk-fetch picks
up the curl shim, and calls `bin/apk-fetch` by full path. `just install-curl`
and `just install-apk-fetch` stay for local runs. Prebuilt jars live in
`bin/<owner>-<repo>/`, because two patch sources can both ship
`patches-4.3.0.mpp`. Still validated as a zip, still deleted and refetched if
it is not one.

**Logging.** `logging`, `logger = logging.getLogger(__name__)` per module.
`log.py: setup()` is called once from `main` and does a `basicConfig` with a
single handler. The formatter prints `[+] msg` green for INFO and `[-] msg`
red for WARNING and above, matching `pr` / `epr`. On an error it appends
`::error::builder [-] msg` as a second line when `GITHUB_REPOSITORY` is set,
so the workflow keeps its annotations. Nothing else uses `print`.

**cli output.** No JSON option. `list-versions --help` on 1.18.0 has only
`-f`, `-x`, `-u`, `--prerelease`, `--patches`. Parse text. `list-patches`
records split on blank lines; a record starts with `Name: `. Compatible
versions are the indented lines after `Compatible versions:`, stopping at
blank or `Version codes:`. `list-versions`: find
`Most common compatible versions:`, match `^\s+(\S+) \((\d+) patch`. No lines
under the header means `Any`. Verified against four real patch bundles.

**Version sorting.** No sort, no dependency. The output is *not* reliably
ordered: `anddea/revanced-patches` prints `8.12.54, 8.28.54, 8.30.54` for
YouTube Music, so "take the first" would pick `8.12.54`. `max()` is enough,
and it is what `sort -s | head -1` did. The key is two lines: strip `v`, cut at
the first `-`, compare int tuples. `max` returns the first of equal versions,
same as the stable sort. `packaging` was rejected because it refuses
`12.19.1-release.0`, a real version in `crimera/piko`. `semver` was rejected
because it refuses `1.2`, which the bash regex allows.

**Parallel.** `parallel-jobs` stays, model default 1, `config.toml` sets 1.
`ThreadPoolExecutor(max_workers=parallel-jobs)`, so 1 is plain sequential.

**build.md.** `build_app()` returns a string, or `None` if the app failed.
`__main__` joins the non-`None` results and writes `build.md` once at the end.
No lock, no truncation race. `prebuilt()` appends its patch / CLI notes to that
same string, so they land next to the app that fetched them instead of at the
very end as in bash. Release-note cosmetics only.

**Signatures.** Dropped, as decided. `check_sig`, `sig.txt` and
`bin/apksigner.jar` are not ported. Bash only ever checked the 3 packages
listed in `sig.txt`, the other 7 returned early, so this removes a code path
that was already inert for most apps. Cost: a mirror serving a re-signed or
pre-patched APK for those 3 packages is no longer caught. `sig.txt` stays in
the repo, unused, until you say otherwise.

**Errors.** One `try/except Exception` per future in the loop. Log, continue.
Fatal before the loop: unreadable config, missing `package-id`, and the
no-patches-found case in `resolve_version`.

**Temp files.** `temp/` holds only the downloaded apks now, so it can be wiped
between runs without losing the tool cache. The patcher `-t` dir is a
`TemporaryDirectory` inside `temp/`, so it cleans itself per app instead of the
`_clean_tmp` glob sweep. `just clean` is `rm -rf temp build`.

**Other.** `gh --json --jq '...'` becomes `gh --json` plus `json.loads`.
`patcher-args` stays a raw config string, `shlex.split`, because users may
quote an argument. The `.ver` sidecar is gone, `download()` returns the
version. A cached `.apkm` is handed to the patcher as-is, no unzip step. The
archive.org listing and download use `urllib`, that host has no bot check.
Keystore password is a list arg, never logged.

## 3. Risks

1. `@cache` is not atomic, so two threads can miss and both download the same
   jar. Pre-existing in bash. One `threading.Lock` if it ever bites; it cannot
   at `parallel-jobs = 1`.
2. The version key raises on a non-numeric segment such as `1.2.beta`. That
   fails only that app, and only if such a version is ever published.
3. `resolve_version` aborts the whole run when the package is in no patch list.
   Kept fatal, as agreed. It means a typo in `package-id`, not a flaky build.
4. No signature check anymore. That is the one real behavior loss, accepted on
   purpose. A mirror serving a re-signed or pre-patched APK for the 3 packages
   that `sig.txt` used to cover now gets patched silently.
5. `list-patches` first line is localized (`資訊: Index: 0` on this machine).
   Only `Name:` and `Compatible versions:` matter, and those come from the
   patch bundle, not the CLI locale.

## 4. Build order

1. `pyproject.toml`, `justfile`, `log.py`, `config.py`, `config.toml` as lists.
2. `scripts.py`: lazy `bin/` accessors and the two installers.
3. `download.py`.
4. `patch.py`: `highest`, `resolve_version`, `run_cli`, `patch_apk`.
5. `__main__.py`: loop, thread pool, `build.md`, summary, exit code.
6. Workflow: `uv run builder config.toml`, install steps and `tomlq` deleted.
