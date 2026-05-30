# bonedigger — lifecycle workflow

Load when working on the GitHub Actions pipeline, pipeline widget, issue state machine, slash commands, or label management.

## Pipeline stages

```
filed → approved → queued → claimed → done
```

The pipeline widget lives in the issue body, updated in-place on every transition. **Zero comment spam** — one edit per stage.

### Stage transitions

| Trigger | Transition | Who |
|---------|-----------|-----|
| Issue opened | → filed | GitHub Actions |
| Maintainer `/approve` or `/lgtm` | filed → approved + queued | Maintainer (write access) |
| Contributor `/claim` | queued → claimed | Any contributor |
| `/unclaim` | claimed → queued | Claimant or maintainer |
| Issue closed | claimed → done | Anyone who can close |
| Stale claim (7 days) | claimed → queued | Scheduled sweep |

## Slash commands

| Command | Permission | Effect |
|---------|-----------|--------|
| `/claim` | Any | Assign self, add `queue/claimed`, update widget |
| `/unclaim` | Claimant or maintainer | Remove assignment, return to `queue/agent-ready` |
| `/approve` | Maintainer (write) | Add `status/approved` + `queue/agent-ready`, update widget |
| `/lgtm` | Maintainer (write) | Alias for `/approve` |
| `/wontfix [reason]` | Maintainer (write) | Close as not planned with reason comment |

## Labels

| Label | Color | Meaning |
|-------|-------|---------|
| `needs-triage` | purple | Needs human review — set kind, priority, and area |
| `status/discussing` | blue | Under discussion — not yet approved |
| `status/approved` | green | Approved — ready for contributors |
| `queue/agent-ready` | purple | Has spec, ready to claim |
| `queue/claimed` | gold | In active work |
| `priority/high` | red | Affects 3+ users (confirmed reproductions) |
| `priority/critical` | dark red | Affects 5+ users |
| `stale-digest` | yellow | Filed against outdated image digest |
| `lgtm` | green | Maintainer approved |
| `agent/blocked` | red | Blocked — needs human input |
| `needs-human/agent-oops` | pink | Agent error — humans only |
| `kind:agent-donation` | teal | Donated agent time issue |
| `flow/project-report` | green | Agent flow: project report |
| `flow/issue-review` | purple | Agent flow: issue review |
| `flow/pr-review` | yellow | Agent flow: PR review |
| `hold` | gray | Do not touch — intentionally held |
| `do-not-merge` | dark red | Do not merge or automate |

## Priority escalation (automatic)

Triggered at `/claim`, `/approve`, and issue open:
- 3+ `ujust confirm` comments → add `priority/high`
- 5+ `ujust confirm` comments → add `priority/critical`

## Pipeline widget anatomy

```
<!-- bonedigger-pipeline -->
```
Brand Name Emoji  ·  issue pipeline
─────────────────────────────────────────────────
  ▶  filed      report received
  ·  approved   —
  ·  queued     —
  ·  claimed    —
  ·  done       —
─────────────────────────────────────────────────
  report:       attached    ·  confirms: 0
  area:         gnome       ·  priority: high
  next action:  same bug? ujust confirm 42
```
```

The widget is stripped and rebuilt from scratch on every update using an awk block that matches from the `pipeline_marker` HTML comment to `---`.

## Stale sweeps (daily schedule)

- **Stale claims**: after 7 days with `queue/claimed` and no update, auto-unclaim and notify claimant
- **Stale triage**: after 14 days with `needs-triage` and no update, comment nudging maintainers

## Reusable workflow inputs

| Input | Default | Description |
|-------|---------|-------------|
| `brand_name` | `Bluefin` | Brand name in widget header |
| `brand_emoji` | `🦖` | Emoji in widget header |
| `pipeline_marker` | `<!-- bonedigger-pipeline -->` | HTML comment used to locate/replace widget |
