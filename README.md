# bonedigger 🦴

> `ujust report` filing + confirm-driven priority escalation, using GitHub as the message bus.

## Current scope

Issue lifecycle management is Hive-managed across the factory.

**bonedigger handles:**
- Canonical GitHub issue templates (`templates/`) synced to factory repos
- Documentation for `ujust report` intake and diagnostic tooling
## How it works

```
USER'S MACHINE                    GITHUB
─────────────────                 ─────────────────────────────────────────
ujust report                      GitHub Issues + Hive
  └─ collects diagnostics           └─ intake structured issue reports
  └─ PII scrub on-device            └─ issue lifecycle managed by Hive
  └─ user reviews locally
  └─ uploads to user's gist
  └─ opens issue w/ gist link
```
GitHub Issues is the only backend. No central server. User owns their data.

## Usage

### As a user
Run on your Bluefin machine:
```bash
ujust report       # file a bug report
ujust confirm 42   # confirm you hit issue #42 too
ujust verify 42    # verify issue #42 is fixed after an update
```

### Downstream repos

Issue templates in `templates/` are automatically synced to downstream repos via `.github/workflows/sync-templates.yml`.
## Repository structure
- `templates/` — canonical GitHub issue templates (synced to all org repos)
- `.github/workflows/sync-templates.yml` — auto-syncs templates to downstream repos
- `docs/skills/` — agent skill docs
## Privacy
- All PII scrubbing happens on the user's machine before any upload
- Diagnostic gists belong to the user — bonedigger only reads them, never creates its own
- No central server, no telemetry infrastructure required

## Roadmap

### Planned: crash/panic detection in `ujust report`

The diagnostic collector currently captures a live system snapshot but has no awareness of what happened in the *previous* boot. A full class of bugs — kernel panics during sleep, hard lockups, abrupt reboots — leave zero trace in the current session.

Planned work:
- **[#11](https://github.com/projectbluefin/bonedigger/issues/11) — crash/panic detection section**: unclean boot classifier (4 buckets: clean shutdown / suspend-no-resume / abrupt end / journal unavailable), panic keyword scan of previous boot, crash artifact status (pstore, kdump, coredumps)
- **[#12](https://github.com/projectbluefin/bonedigger/issues/12) — PII scrubbing for kernel log excerpts**: IPv4/IPv6, UUIDs, disk serials, MAC addresses

## Part of Project Bluefin
- [projectbluefin/common](https://github.com/projectbluefin/common) — ships `ujust report` and owns lifecycle management
- [projectbluefin/dakota](https://github.com/projectbluefin/dakota) — reference implementation
