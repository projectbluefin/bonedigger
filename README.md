# bonedigger 🦴

> Client-server bug reporting for using GitHub as the message bus.

## How it works
Telemetry sucks so we just make reporting issues to developers suck less. 


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
      brand_emoji: "🦖"
    secrets: inherit
```

## The pipeline widget

Every issue gets a pipeline widget embedded in its body, edited in-place on each transition. No comment spam — one edit per stage.

**Stage 1 — filed** (issue just opened, report attached)

```
Bluefin 🦖  ·  issue pipeline
─────────────────────────────────────────────────
  ▶  filed      report received
  ·  approved   —
  ·  queued     —
  ·  claimed    —
  ·  done       —
─────────────────────────────────────────────────
  report:       attached    ·  confirms: 0
  area:         —           ·  priority: —
  next action:  same bug? ujust confirm 42
```

**Stage 2 — approved + queued** (maintainer ran `/approve`, 2 users confirmed)
The more users confirm things the HIGHER it gets prioritized!

```
Bluefin 🦖  ·  issue pipeline
─────────────────────────────────────────────────
  ✓  filed      report received
  ✓  approved   signed off by a maintainer
  ▶  queued     waiting for a contributor to claim
  ·  claimed    —
  ·  done       —
─────────────────────────────────────────────────
  report:       attached    ·  confirms: 2
  area:         gnome       ·  priority: high
  next action:  comment /claim to take this
```

**Stage 3 — claimed** (contributor ran `/claim`)
```
This means volunteers can claim work, and if they give up, toss it back in the queue and grab another one.

Bluefin 🦖  ·  issue pipeline
─────────────────────────────────────────────────
  ✓  filed      report received
  ✓  approved   signed off by a maintainer
  ✓  queued     —
  ▶  claimed    @jeefy
  ·  done       —
─────────────────────────────────────────────────
  report:       attached    ·  confirms: 2
  area:         gnome       ·  priority: high
  next action:  /unclaim to return to queue if stuck
```

**Stage 4 — done** (issue closed, awaiting verification)
```
Bluefin 🦖  ·  issue pipeline
─────────────────────────────────────────────────
  ✓  filed      report received
  ✓  approved   signed off by a maintainer
  ✓  queued     —
  ✓  claimed    —
  ▶  done       fix shipped
─────────────────────────────────────────────────
  report:       attached    ·  verified: 1/3
  area:         gnome       ·  priority: high
  next action:  ujust verify 42 — three verifies closes the case
```

Three `ujust verify` calls from affected users closes the case completely.

## Repository structure
- `just/` — canonical `ujust report` recipe (shipped via projectbluefin/common)
- `templates/` — canonical GitHub issue templates (shipped to all org repos)
- `.github/workflows/lifecycle.yml` — reusable lifecycle workflow
- `action.yml` — composite action entrypoint

## Privacy
- All PII scrubbing happens on the user's machine before any upload
- Diagnostic gists belong to the user — bonedigger only reads them, never creates its own
- No central server, no telemetry infrastructure required

## Part of Project Bluefin
- [projectbluefin/common](https://github.com/projectbluefin/common) — ships `ujust report` to all variants
- [projectbluefin/dakota](https://github.com/projectbluefin/dakota) — reference implementation
