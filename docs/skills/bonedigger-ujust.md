# bonedigger — ujust report tool

Load when working on the client-side diagnostic reporting tool: `just/report.just`, `ujust-report-config.yaml`, or the OTel deep metrics capture.

## Commands

```bash
ujust report         # collect diagnostics, review locally, upload to gist, open issue
ujust confirm 42     # add a confirm comment to issue #42
ujust verify 42      # add a verify comment to issue #42 after an update
```

## What `ujust report` collects

| Field | Source |
|-------|--------|
| Image name, tag, flavor, ref | `/usr/share/ublue-os/image-info.json` |
| Booted image + digest | `bootc status --json` |
| Staged image | `bootc status --json` |
| Kernel version, architecture | `uname -r`, `uname -m` |
| GNOME version | `gnome-shell --version` |
| Active GNOME extensions | `gnome-extensions list --enabled` |
| Installed Flatpaks | `flatpak list --columns=application,version` |
| Load average | `/proc/loadavg` |
| Memory usage | `free -h --si` |
| Failed systemd units | `systemctl list-units --state=failed` |
| Groups (membership only) | `groups` (username redacted) |
| GPU info | `nvidia-smi -q` (NVIDIA), DRM sysfs (AMD), `lspci` (all) |
| Optional: deep hardware metrics | OpenTelemetry (35s sample) |

## PII scrubbing

All scrubbing happens on-device before any upload. Nothing identifying leaves the machine raw.

| Data | Scrubbed to |
|------|-------------|
| `/home/<username>/` paths | `/home/[REDACTED]/` |
| `/var/home/<username>/` paths | `/var/home/[REDACTED]/` |
| `groups` leading username | `[REDACTED] : group1 group2 ...` |
| NVIDIA GPU UUID | `[REDACTED]` |
| NVIDIA Serial Number | `[REDACTED]` |
| NVIDIA PCIe Bus Id | `[REDACTED]` |
| NVIDIA Minor Number | `[REDACTED]` |
| `USER=`, `LOGNAME=` env vars in logs | `[REDACTED]` |
| Email addresses in logs | `[REDACTED-email]` |
| `machine-id` | Hashed to 8-char anonymous `HOST_ID` (SHA256, not reversible) |
| `host.id`, `host.name`, `host.ip`, `host.mac` | Deleted by OTel resource/privacy processor |
| `_MACHINE_ID`, `_BOOT_ID`, `_UID`, `_GID`, `_CMDLINE`, `_EXE`, `_COMM` | Deleted from journald log attributes |
| `process.owner`, `process.command_line`, `process.executable.path` | Deleted by OTel processor |

## Optional deep hardware metrics (OTel)

Gated on `/usr/share/ublue-os/otel/ujust-report-config.yaml` existing in the image. If present, the user is offered a 35-second hardware telemetry capture. Outputs two spec-compliant OTLP NDJSON files (one signal type per file, per OTel spec):

- `metrics.otlp.jsonl` — CPU, memory, disk, filesystem, network, paging, processes, Podman containers
- `logs.otlp.jsonl` — journald service errors/warnings (gnome-shell, gdm, bluetooth, NetworkManager, systemd-coredump) + kernel dmesg (warning+)

**OTel collector config highlights:**
- `memory_limiter` first (512 MiB limit) — OTel best practice
- `batch` last before exporters — OTel best practice
- `host.id` disabled (machine-id derived)
- Process scraper: `command_line` and `executable.path` metrics disabled at source
- Filesystem exclusion regexes use proper anchors (`^/proc(/|$)` not `/proc/*`)
- `hostname_sources: [os]` — no DNS lookup

**Binary resolution order:**
1. `$HOME/.local/bin/otelcol-contrib`
2. `/usr/local/bin/otelcol-contrib`
3. `$(command -v otelcol-contrib)`
4. Fallback: `podman run docker.io/otel/opentelemetry-collector-contrib` (privileged, 45s timeout, no `--network=host`)

**Podman fallback mounts:** `/proc`, `/sys`, `/var/log/journal`, `/run/log/journal`, substituted config, output dir, and the Podman socket (dynamic `id -u`).

**Config path substitution** uses `python3` (not `sed`) to safely replace `/output/` with `$REPORT_DIR/` — handles `&` and `\` in paths.

## Upload flow

1. Show rendered report via `glow` + `gum pager` for local review
2. Confirm upload with `gum confirm`
3. If `gh auth status --active` fails → copy to clipboard (wl-copy or xclip), show issue URL
4. If auth OK → `gh gist create --public` with `summary.md` (+ `metrics.otlp.jsonl` + `logs.otlp.jsonl` if captured)
5. Offer to `xdg-open` issue URL with gist URL pre-filled as query param

## Environment variable overrides

| Variable | Default | Purpose |
|----------|---------|---------|
| `IMAGE_INFO_FILE` | `/usr/share/ublue-os/image-info.json` | Image metadata path |
| `BONEDIGGER_ISSUE_URL` | `https://github.com/projectbluefin/common/issues/new?template=bug-report.yml` | Issue URL base |
| `BONEDIGGER_BRAND` | `🫐 Bluefin Bug Report` | Brand name shown in gum header |

## Dependencies

- `gum` — TUI prompts and styling
- `gh` — GitHub CLI for gist upload and auth check
- `bootc` — reads booted image status
- `jq` — parses JSON from bootc and image-info
- `gnome-shell`, `gnome-extensions`, `flatpak` — collects system info
- `glow` (optional) — renders markdown in terminal
- `wl-copy` / `xclip` (optional) — clipboard fallback when not authenticated
- `otelcol-contrib` or `podman` (optional) — deep hardware metrics

## Report output structure

```
$XDG_RUNTIME_DIR/ujust-report/report-XXXXXX/
  summary.md           — Markdown report (always)
  metrics.otlp.jsonl   — OTel host/container metrics (if OTel captured)
  logs.otlp.jsonl      — OTel journald + kernel logs (if OTel captured)
```

Temp directory is cleaned up on EXIT trap. Use `trap - EXIT; exit 0` to preserve files when user cancels.

## Consumer context (read before proposing design changes)

- **Bluefin, Aurora, and Dakota all use GitHub as their backend.** They upload reports as GitHub Gists and file GitHub Issues. They do NOT use external paste services.
- `BUG_REPORT_URL` in `/etc/os-release` is the canonical source for the distro's issue tracker — no env var needed for this.
- If adding non-GitHub paste support (e.g. for Fedora, Debian, Ubuntu), use a small hardcoded lookup table keyed on the `BUG_REPORT_URL` domain. Do not add custom `os-release` fields or new env vars for this.
