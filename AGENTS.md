# bonedigger — Agent & Copilot Instructions

`projectbluefin/bonedigger` is the reusable lifecycle and diagnostics tool for the Project Bluefin factory.

It owns:
- the reusable issue lifecycle workflow (`.github/workflows/lifecycle.yml`)
- the canonical issue templates (`templates/`)
- the canonical `ujust report` recipe (`just/report.just`)
- the template sync workflow that opens downstream PRs

## Start here

Read the repo skill docs before changing behavior:
- `docs/skills/bonedigger-overview.md` — architecture, adoption, repo layout
- `docs/skills/bonedigger-lifecycle.md` — issue state machine, slash commands, labels
- `docs/skills/bonedigger-templates.md` — template sync and downstream targets
- `docs/skills/bonedigger-ujust.md` — client-side data collection and scrubbing

## Factory role

bonedigger is factory infrastructure. It serves these repos directly:
- `projectbluefin/common` — ships `ujust report` to all variants
- `projectbluefin/dakota` — reference implementation and consumer
- `projectbluefin/bluefin`
- `projectbluefin/bluefin-lts`
- `projectbluefin/knuckle`

Any repo that adopts `projectbluefin/bonedigger/.github/workflows/lifecycle.yml@main` is also a bonedigger consumer.

## Issue lifecycle

Queue state machine:

`filed → approved → queued → claimed → done`

| Stage | Trigger |
|---|---|
| `filed` | Issue opened; bonedigger inserts the pipeline widget |
| `approved` | Maintainer applies `status/approved` or comments `/approve` or `/lgtm` |
| `queued` | `queue/agent-ready` applied automatically |
| `claimed` | Contributor comments `/claim`; assignee + widget update |
| `done` | Fix shipped; issue closed and awaits `ujust verify` confirmations |

## Claiming work

- Claim a queued issue with `/claim`
- Return it with `/unclaim` if you stop working on it
- Maintainers approve work with `/approve` or `/lgtm`
- Use `agent/blocked` only when human input is required

## Labels

Factory labels expected here:
- `hive/p0`, `hive/p1`
- `priority/p0`, `priority/p1`
- `queue/agent-ready`, `queue/claimed`
- `agent/blocked`

Lifecycle labels managed by the workflow:
- `needs-triage`, `status/discussing`, `status/approved`
- `priority/high`, `priority/critical`, `stale-digest`, `lgtm`
- `needs-human/agent-oops`, `kind:agent-donation`
- `flow/project-report`, `flow/issue-review`, `flow/pr-review`
- `hold`, `do-not-merge`

## Local validation

Use the lightest checks that match the change:

```bash
actionlint .github/workflows/*.yml
```

For doc-only changes, read the rendered Markdown and verify links/targets manually.

For template changes, confirm the sync workflow still targets the factory repos listed above.

## CI/CD integration points

- `lifecycle.yml` is a reusable workflow triggered by downstream repos on `issues`, `issue_comment`, and `schedule`
- `sync-templates.yml` opens PRs against downstream repos when `templates/` changes on `main`
- Cross-repo writes must use the `mergeraptor` GitHub App token pattern; PATs are not allowed
- Repo settings should stay factory-aligned: squash merge, auto-merge, and delete-branch-on-merge enabled

## PR rules

- Use Conventional Commits for commits and PR titles
- No WIP PRs
- Keep scope tight; bonedigger changes can affect the whole factory
- Prefer one branch per logical fix
