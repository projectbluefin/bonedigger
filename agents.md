# agents.md — bonedigger

Skill index for AI agents working in this repo. Load the skills relevant to your task; skills are in [`docs/skills/`](docs/skills/).

## Skills

| Skill | Load when… |
|-------|-----------|
| [`bonedigger-overview`](docs/skills/bonedigger-overview.md) | Starting any work in this repo — architecture, user commands, repo layout, how to adopt bonedigger |
| [`bonedigger-lifecycle`](docs/skills/bonedigger-lifecycle.md) | Working on the GitHub Actions pipeline, pipeline widget, slash commands (`/claim` `/approve` etc.), labels, or stale sweeps |
| [`bonedigger-ujust`](docs/skills/bonedigger-ujust.md) | Working on `just/report.just`, the OTel deep metrics config, PII scrubbing, or the gist upload flow |
| [`bonedigger-agent-donation`](docs/skills/bonedigger-agent-donation.md) | Working with the agent donation fast-track, `flow/` labels, `kind:agent-donation` issues, or agent-specific labels (`agent/blocked`, `hold`) |
| [`bonedigger-templates`](docs/skills/bonedigger-templates.md) | Adding, editing, or syncing GitHub issue templates; working on `sync-templates.yml` |

## Quick orientation

- **bonedigger is a reusable workflow**, not a standalone app. Consumers call `lifecycle.yml@main` from their own repo.
- **GitHub Issues is the only backend.** No database, no central server.
- **The pipeline widget lives in the issue body** — edited in-place, never via comments.
- **Templates are mastered here** and synced to `common`, `dakota`, `bluefin`, and `bluefin-lts` automatically.
- **Agent donation issues** skip triage and land directly in the queue — look for `Workflow: Agent Donation` in the issue body.

## Key files

```
action.yml                              composite action entrypoint (→ lifecycle.yml)
.github/workflows/lifecycle.yml         issue pipeline state machine
.github/workflows/sync-templates.yml    template sync to downstream repos
just/report.just                        ujust report recipe
just/ujust-report-config.yaml           OTel config for deep hardware metrics
templates/                              canonical issue templates
docs/skills/                            agent skill docs (this directory)
```
