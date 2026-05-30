# bonedigger — overview

Client-server bug reporting for Project Bluefin, using GitHub Issues as the only backend. No central server. User owns their data.

## Architecture

```
USER'S MACHINE                    GITHUB (bonedigger)
─────────────────                 ──────────────────────────────
ujust report                      lifecycle action (server)
  └─ collects diagnostics           └─ on issue open:
  └─ PII scrub on-device               └─ parse diagnostic gist
  └─ user reviews locally              └─ post diagnosis card
  └─ uploads to user's gist            └─ auto-label from data
  └─ opens issue w/ gist link          └─ pipeline: filed→approved→queued→claimed→done
                                     └─ /claim /unclaim /approve /lgtm /wontfix
ujust confirm <issue#>               └─ confirm count → priority escalation
ujust verify <issue#>                └─ new image ships → auto-close old-digest issues
```

## User commands

Run on a Bluefin machine:
```bash
ujust report         # collect diagnostics, upload to gist, open issue
ujust confirm 42     # confirm you hit issue #42 too
ujust verify 42      # verify issue #42 is fixed after an update
```

## Repository structure

| Path | Purpose |
|------|---------|
| `just/report.just` | canonical `ujust report` recipe (shipped via projectbluefin/common) |
| `just/ujust-report-config.yaml` | OpenTelemetry config for deep hardware metrics |
| `templates/` | canonical GitHub issue templates (synced to all org repos) |
| `.github/workflows/lifecycle.yml` | reusable lifecycle workflow |
| `.github/workflows/sync-templates.yml` | auto-syncs templates to downstream repos |
| `action.yml` | composite action entrypoint (points to reusable workflow) |

## Adopting bonedigger in a repo

Add `.github/workflows/bonedigger.yml`:
```yaml
name: bonedigger
on:
  issues:
    types: [opened, labeled, closed]
  issue_comment:
    types: [created]
  schedule:
    - cron: '0 9 * * *'

permissions:
  issues: write
  contents: read

jobs:
  bonedigger:
    uses: projectbluefin/bonedigger/.github/workflows/lifecycle.yml@main
    with:
      brand_name: "Bluefin"
      brand_emoji: "🫐"
    secrets: inherit
```

Inputs: `brand_name`, `brand_emoji`, `pipeline_marker` (default: `<!-- bonedigger-pipeline -->`).

## Privacy model

- All PII scrubbing happens on the user's machine before any upload
- Diagnostic gists belong to the user — bonedigger only reads them, never creates its own
- `machine-id` is hashed to an 8-char anonymous device ID — not reversible

## Related repos

- [projectbluefin/common](https://github.com/projectbluefin/common) — ships `ujust report` to all variants
- [projectbluefin/dakota](https://github.com/projectbluefin/dakota) — reference implementation
- [ublue-os/bluefin](https://github.com/ublue-os/bluefin) — downstream template recipient
- [ublue-os/bluefin-lts](https://github.com/ublue-os/bluefin-lts) — downstream template recipient
