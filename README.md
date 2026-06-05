# bonedigger 🦴

> `ujust report` filing + confirm-driven priority escalation, using GitHub as the message bus.

## Current scope

Lifecycle management moved to [`projectbluefin/common/.github/workflows/lifecycle.yml`](https://github.com/projectbluefin/common/blob/main/.github/workflows/lifecycle.yml).

**bonedigger now handles only:**
- `ujust report` issue detection on open
- confirm-count priority escalation (`3+` → `priority/p1`, `5+` → `priority/p0`)
- bonedigger-specific **agent donation** fast-track labels on issue open

**Owned by `common` now:**
- slash commands like `/approve`, `/claim`, `/unclaim`, `/wontfix`, `/hold`
- issue body widget rendering
- label creation / sync
- stale sweeps and lifecycle transitions

## How it works

```
USER'S MACHINE                    GITHUB
─────────────────                 ─────────────────────────────────────────
ujust report                      bonedigger lifecycle workflow
  └─ collects diagnostics           └─ detect `ujust report` issue bodies
  └─ PII scrub on-device            └─ keep confirm-based priority labels in sync
  └─ user reviews locally           └─ fast-track agent donation issues
  └─ uploads to user's gist
  └─ opens issue w/ gist link     common lifecycle workflow
                                   └─ slash commands + widget + queue state
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

If you also want lifecycle widgets, slash commands, and queue management, wire the caller from `projectbluefin/common/.github/workflows/lifecycle.yml` too.

## Repository structure
- `just/` — canonical `ujust report` recipe (shipped via projectbluefin/common)
- `templates/` — canonical GitHub issue templates (shipped to all org repos)
- `.github/workflows/lifecycle.yml` — reusable reporting workflow
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
- [projectbluefin/common](https://github.com/projectbluefin/common) — ships `ujust report` and owns lifecycle management
- [projectbluefin/dakota](https://github.com/projectbluefin/dakota) — reference implementation
