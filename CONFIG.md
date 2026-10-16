# Config

Configuration is loaded from `config.toml`. Extra keys are not allowed.

## Global Options

```toml
parallel-jobs = 1
cli-version   = "latest"
```

- `parallel-jobs` (int, default: `1`) — Number of CPU cores to use for parallel patching.
- `cli-version` (string, default: `"latest"`) — Morphe CLI version. Accepted values: `"latest"`, `"dev"`, or a specific version like `"v5.0.0"`/`"5.0.0"`. Must match `latest`, `dev`, or `v?X.Y.Z(-dev.N)`.

## App Options

Each app is defined as a TOML table (e.g. `[Some-App]`). Any table in the config is treated as an app. Top-level scalar keys are treated as global options. For each app table, `app-name` defaults to the table name if not specified.

```toml
[Some-App]
app-name          = "SomeApp"  # default: table name ("Some-App")
enabled           = true       # default: true
package-id        = "com.spotify.music"  # required
patch-source      = "MorpheApp/morphe-patches"  # default: "MorpheApp/morphe-patches"
patch-version     = "latest"   # default: "latest"
version           = "latest"     # default: "latest"
archive-dlurl     = ""         # default: ""
included-patches  = ["Some Patch"]  # default: []
excluded-patches  = ["Some Patch", "Some Other Patch"]  # default: []
exclusive-patches = false      # default: false
patcher-args      = ["-OdarkThemeBackgroundColor=#FF0F0F0F" "-Oanother-option=value"]
```

- `enabled` (bool, default: `true`) — Whether to build this app.
- `package-id` (string, required) — Android package ID of the app.
- `app-name` (string, default: table name) — Display/release name used for this app. If omitted, it defaults to the table name.
- `patch-source` (string, default: `"MorpheApp/morphe-patches"`) — Repository to fetch the patches bundle from.
- `patch-version` (string, default: `"latest"`) — Patches bundle version. Accepted: `"latest"`, `"dev"`, or `v?X.Y.Z` (optionally `-dev.N`), e.g. `"v2.160.0"`.
- `version` (string, default: `"latest"`) — Base APK version to use. Accepted: `"latest"`, `"dev"` or a specific version number (e.g. `"17.40.41"`, may include suffixes like `"-release.0"`).
- `archive-dlurl` (string, default: `""`) — Optional `archive.org` download URL. If set, this source is tried first before fallback APK sources (`dl-apk.sh`: archive-dlurl → apk-fetch: apkcombo → apkpure → apkmirror).
- `included-patches` (list[str], default: `[]`) — List of non-default patches to include.
- `excluded-patches` (list[str], default: `[]`) — List of patches to exclude.
- `exclusive-patches` (bool, default: `false`) — If `true`, exclude all patches by default (only patches listed in `included-patches` are applied).
- `patcher-args` (list[str], default: `[]`) — Additional arguments passed to the Morphe CLI patcher.

## Notes

- `version` and `patch-version`/`cli-version` are validated against their allowed patterns. Invalid values will fail config validation.
- Unknown keys are forbidden in the config (and per-app tables).
