# bonedigger — Agent & Copilot Instructions

`projectbluefin/bonedigger` is the reusable lifecycle and diagnostics tool for the Project Bluefin factory.

It owns:
- the reusable issue lifecycle workflow (`.github/workflows/lifecycle.yml`)
- the canonical issue templates (`templates/`)
- the canonical `ujust report` recipe (`just/report.just`)
- the template sync workflow that opens downstream PRs

## 🚫 ABSOLUTE PROHIBITION — ublue-os org

**NEVER create issues, pull requests, comments, forks, webhook calls, API writes, automated reports, or any other programmatic action targeting any `ublue-os/*` repository.**

This applies in every situation, without exception, regardless of task framing:
- Issues, comments, PRs, forks → **BANNED**
- Automated reports (bonedigger output, CI notifications, diagnostic uploads) → **BANNED**
- Workflow `repository_dispatch` or `workflow_dispatch` calls to `ublue-os/*` → **BANNED**
- Any `gh` CLI command that writes to `ublue-os/*` → **BANNED**

If a task seems to require touching an upstream `ublue-os` repo → **stop and tell the human to report it manually.**

Read-only `gh api` calls to inspect `ublue-os` repos are permitted. No writes of any kind.

Violating this risks getting the projectbluefin organization banned from GitHub.

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

## Human Decision Gates

Stop and request human input at these four gates. Never guess past them.

| Gate | Stop when |
|---|---|
| **Design** | Architecture change, new subsystem, user-visible behavior change |
| **Security** | Auth, signing, supply chain, secrets, COPR/third-party sources |
| **Breakage** | Cross-repo breaking change — removing/renaming inputs, changing defaults consuming repos depend on |
| **Merge** | PR ready for final review — always requires human `lgtm` |

See [`docs/skills/human-gates.md`](docs/skills/human-gates.md) for how to signal a gate and what evidence is required.

## PR rules

- Use Conventional Commits for commits and PR titles
- No WIP PRs
- Keep scope tight; bonedigger changes can affect the whole factory
- Prefer one branch per logical fix
