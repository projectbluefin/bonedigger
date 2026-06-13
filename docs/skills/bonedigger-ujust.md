# bonedigger — ujust report tool

Load when working on the client-side diagnostic reporting tool in `projectbluefin/common`: `system_files/bluefin/usr/share/ublue-os/just/60-bonedigger.just`, `system_files/bluefin/usr/share/ublue-os/otel/ujust-report-config.yaml`, or the OTel deep metrics capture.

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
| Current boot kernel errors | `journalctl -b 0 -k -p err..emerg` (attached as `journal.txt`) |
| Current boot system errors | `journalctl -b 0 -p err..emerg` (attached as `journal.txt`) |
| Key service logs | `journalctl -b 0 -u <svc>` for gnome-shell, gdm, NetworkManager, bluetooth, rpm-ostree, systemd-coredump (attached as `journal.txt`) |
| Groups (membership only) | `groups` (username redacted) |
| GPU info | `nvidia-smi -q` (NVIDIA), DRM sysfs (AMD), `lspci` (all) |
| Crash / panic detection | Previous boot end state, panic keywords, kernel errors, hardware fingerprint, crash artifact status |
| Optional: deep hardware metrics | OpenTelemetry (35s sample) |

## PII scrubbing

All scrubbing happens on-device before any upload. Nothing identifying leaves the machine raw.

### General scrubbing (applied to all collected data)

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

### Kernel log scrubbing — `scrub_kernel_log()` (applied to all kernel excerpts)

Applied to every `journalctl -b -1 -k` excerpt. **Order matters** — MAC must run before IPv6 to get the right label.

| Data | Pattern | Scrubbed to |
|------|---------|-------------|
| MAC addresses | `([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}` | `[MAC-REDACTED]` |
| IPv4 addresses | `\b([0-9]{1,3}\.){3}[0-9]{1,3}\b` | `[IP-REDACTED]` |
| IPv6 full (≥4 groups) | `([0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{0,4}` | `[IP-REDACTED]` |
| IPv6 compressed (`::`) | `[0-9a-fA-F]{0,4}(:[0-9a-fA-F]{0,4})*::[0-9a-fA-F:]+` | `[IP-REDACTED]` |
| UUIDs / GUIDs | `[0-9a-fA-F]{8}-...-[0-9a-fA-F]{12}` | `[UUID-REDACTED]` |
| Disk/NVMe serials | `(eui\|naa\|wwn\.)[0-9a-fA-F]+` | `[SERIAL-REDACTED]` |
| Home paths | same as general scrubbing | `[REDACTED]` |

**IPv6 regex rationale:** The 4-group minimum (`{3,7}`) avoids false-positives on `HH:MM:SS` timestamps (only 3 groups). The `::` pattern is a separate pass to catch loopback (`::1`), link-local (`fe80::1`), etc.

**`Linux version` line is intentionally excluded** from the hardware fingerprint — it can contain build host strings (e.g. `builduser@buildhost`). Extract only `DMI: .* BIOS` lines.

## Crash / Panic Detection section

Implemented in `projectbluefin/common/system_files/bluefin/usr/share/ublue-os/just/60-bonedigger.just`. All data sourced from `journalctl -b -1` (previous boot). All kernel excerpts pass through `scrub_kernel_log()` before landing in `summary.md`.

### Boot end-state classifier (4 buckets — never assume)

| Status | Condition |
|--------|-----------|
| `previous boot journal unavailable` | `journalctl -b -1` returns no output |
| `clean shutdown` | Shutdown markers found in tail-200 of boot -1 full journal |
| `suspend entered — no resume recorded before next boot` | Last `PM: suspend (entry\|exit)` line in boot -1 kernel log is `entry` |
| `abrupt end — resumed from suspend, no clean shutdown recorded` | Last PM line is `exit` (resumed OK, then crashed) |
| `abrupt end — no shutdown or suspend markers found` | Neither shutdown nor any PM markers present |

**Shutdown grep is scoped to `tail -200`** (not the full journal). Rationale: shutdown markers always appear at the end of a clean boot; streaming the full journal on the crash path (when no marker is found) can drain hundreds of thousands of lines with no progress indicator to the user.

**Three PM buckets, not two.** A boot that resumed from suspend and then crashed must not be reported as "no suspend markers found" — it had suspend markers, just no clean shutdown after.

### Data collected (only when boot -1 is available)

| Sub-section | Command | Notes |
|-------------|---------|-------|
| Panic keyword scan | `journalctl -b -1 -k … \| grep -iE 'panic\|oops\|BUG:\|Call Trace\|RIP:\|…' \| tail -20` | `tail` not `head` — crash is at end |
| Last kernel errors | `journalctl -b -1 -k -p err..emerg … \| tail -30` | |
| Context window (last 30 kernel lines) | `journalctl -b -1 -k … \| tail -30` | Suppressed for clean shutdowns with no findings |
| Hardware fingerprint | `grep -E 'DMI: .* BIOS' \| head -1` | DMI model + BIOS version only |

### Crash artifact status (always collected, independent of boot -1)

| Artifact | How detected |
|----------|-------------|
| pstore | `mountpoint -q /sys/fs/pstore` + `find` file count; "empty" ≠ "no crash" — may have been cleared on boot |
| kdump | `systemctl is-enabled/is-active kdump.service` (service status, not `/var/crash` directory) |
| Userspace coredumps | `coredumpctl list --since "7 days ago" \| tail -10` (home paths scrubbed) |

### `set -euo pipefail` safety rules

- Every `journalctl … | grep … | tail` pipeline ends with `|| true` inside `$()` — grep exits 1 on no match
- Shutdown classification uses `if journalctl … | tail -200 | grep -qiE …` — safe in `if` conditions
- `systemctl is-enabled kdump.service &>/dev/null` — safe in `if` condition
- `${PSTORE_COUNT:-0}` — guards against empty find output

## Optional deep hardware metrics (OTel)

Gated on `/usr/share/ublue-os/otel/ujust-report-config.yaml` existing in the image. If present, the user is offered a 35-second hardware telemetry capture. Outputs two spec-compliant OTLP NDJSON files (one signal type per file, per OTel spec):

- `metrics.otlp.jsonl` — CPU, memory, disk, filesystem, network, paging, processes, Podman containers
- `logs.otlp.jsonl` — journald service errors/warnings (gnome-shell, gdm, bluetooth, NetworkManager, systemd-coredump) + kernel dmesg (warning+)

The definitive OTel config lives in `projectbluefin/common/system_files/bluefin/usr/share/ublue-os/otel/ujust-report-config.yaml`.

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
3. If `gh auth status --active` fails → copy to clipboard (wl-copy or xclip), show issue URL; `journal.txt` path shown separately
4. If auth OK → `gh gist create --public` with `summary.md` + `journal.txt` (always) + `metrics.otlp.jsonl` + `logs.otlp.jsonl` (if OTel captured)
5. `gum choose` "File a bug report / Request a feature / Skip" — bugs route to the image's own tracker, feature requests always go to common

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
  journal.txt          — Current boot system/service logs (always)
  metrics.otlp.jsonl   — OTel host/container metrics (if OTel captured)
  logs.otlp.jsonl      — OTel journald + kernel logs (if OTel captured)
```

Temp directory is cleaned up on EXIT trap. Use `trap - EXIT; exit 0` to preserve files when user cancels.

## Consumer context (read before proposing design changes)

- **Bluefin, Aurora, and Dakota all use GitHub as their backend.** They upload reports as GitHub Gists and file GitHub Issues. They do NOT use external paste services.
- `BUG_REPORT_URL` in `/etc/os-release` is the canonical source for the distro's issue tracker — no env var needed for this.
- If adding non-GitHub paste support (e.g. for Fedora, Debian, Ubuntu), use a small hardcoded lookup table keyed on the `BUG_REPORT_URL` domain. Do not add custom `os-release` fields or new env vars for this.

## Where the code lives — do not get this wrong

The recipe and OTel config are **image content**, not CI tooling. They live in `projectbluefin/common`:

| File | Path in common |
|------|----------------|
| `ujust report` recipe | `system_files/bluefin/usr/share/ublue-os/just/60-bonedigger.just` |
| OTel collector config | `system_files/bluefin/usr/share/ublue-os/otel/ujust-report-config.yaml` |

`common` ships both files to every image via `common.bst`. Dakota and bluefin inherit them automatically — do **not** add copies to those repos.

**Sync workflows are the wrong answer.** If you find yourself creating a workflow to copy these files from bonedigger to common (or anywhere else), stop: the file is in the wrong repo. Edit it directly in common.
