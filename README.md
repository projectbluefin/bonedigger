# bonedigger 🦴

> `ujust report` filing + confirm-driven priority escalation, using GitHub as the message bus.

## Current scope

Lifecycle management is owned here again, with the new `clanker-queue/*`
migration namespace layered on top of the legacy labels during the soak.

**bonedigger handles:**
- `ujust report` issue detection on open
- confirm-count priority escalation (`3+` → `priority/p1` + `clanker-queue/p1`, `5+` → `priority/p0` + `clanker-queue/p0`)
- bonedigger-specific **agent donation** fast-track labels on issue open

**Legacy labels remain during the soak:**
- `status/*`, `queue/*`, `priority/*`, and `hive/*`
- they are dual-written with the new namespace until the migration completes

## How it works

```
USER'S MACHINE                    GITHUB
─────────────────                 ─────────────────────────────────────────
ujust report                      bonedigger lifecycle workflow
  └─ collects diagnostics           └─ detect `ujust report` issue bodies
  └─ PII scrub on-device            └─ keep confirm-based priority + clanker labels in sync
  └─ user reviews locally           └─ fast-track agent donation issues
  └─ uploads to user's gist
  └─ opens issue w/ gist link     bonedigger label sync workflow
                                   └─ propagates labels.json to factory repos
ujust confirm <issue#>            └─ bonedigger re-counts confirms
                                     and escalates priority labels
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

### As a repo maintainer
Add to `.github/workflows/bonedigger.yml`:
```yaml
name: bonedigger
on:
  issues:
    types: [opened]
  issue_comment:
    types: [created]

permissions:
  issues: write
  contents: read

jobs:
  bonedigger:
    uses: projectbluefin/bonedigger/.github/workflows/lifecycle.yml@main
    secrets: inherit
```

If you also want lifecycle widgets, slash commands, and queue management, wire the downstream compatibility workflow that consumes the same labels.

## Repository structure
- `just/` — canonical `ujust report` recipe (shipped via projectbluefin/common)
- `templates/` — canonical GitHub issue templates (shipped to all org repos)
- `.github/workflows/lifecycle.yml` — reusable reporting workflow
- `.github/workflows/sync-labels.yml` — syncs the canonical labels.json to factory repos
- `action.yml` — composite action entrypoint

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
- [projectbluefin/common](https://github.com/projectbluefin/common) — ships `ujust report`; image content lives there
- [projectbluefin/dakota](https://github.com/projectbluefin/dakota) — reference implementation
