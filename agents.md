# agents.md — bonedigger

Skill index for AI agents working in this repo. Load the skills relevant to your task; skills are in [`docs/skills/`](docs/skills/).

## STOP — before you write a single line of code

1. Read `bonedigger-overview.md` (architecture, repo layout, what bonedigger actually is).
2. Read every skill doc that matches your task area (see Skills table below). No skimming — the answers to common mistakes are in those docs.
3. Identify the exact scope of your change. If it touches more than one logical area, stop and split the work.
4. Do not proceed until you can answer: what files change, why, and how will you verify the result?

## Verification — you are not done until you verify

**Done means verified, not "I believe this should work."**

| Change type | Required verification |
|-------------|----------------------|
| Any workflow change | `actionlint .github/workflows/*.yml` — inspect output, fix all errors |
| Any file change | `pre-commit run --all-files` — must pass clean |
| Any commit pushed | `gh run list --repo projectbluefin/bonedigger --limit 5` — wait for runs to complete, confirm green |
| Issue/PR body edit | Re-read the issue/PR body after the edit and confirm the widget or content is correct |
| Template change | Confirm `sync-templates.yml` still targets all 5 downstream repos after your edit |

Never report success before running these checks and reading the output.

## Anti-patterns — these are mistakes, not shortcuts

- **Do not claim done without verifying.** "I've updated the file" is not done. Run the checks. Read the output.
- **Do not post extra comments on issues or PRs.** The pipeline widget is edited in-place. Slash commands are processed by the workflow. You do not need to add comments to explain your actions.
- **Do not mix unrelated changes in one branch.** One branch = one logical fix. If you find something else broken, file a separate issue.
- **Do not skip reading the skill docs.** The docs exist because agents made these mistakes. The answers are already there.
- **Do not guess at workflow patterns.** Auth uses mergeraptor App tokens, not PATs. PRs target `main`. Labels have exact names. Check the docs.
- **Do not push with `--no-verify`.** Ever.

## Skills

| Skill | Load when… |
|-------|-----------|
| [`bonedigger-overview`](docs/skills/bonedigger-overview.md) | Starting any work in this repo — architecture, user commands, repo layout, how to adopt bonedigger |
| [`bonedigger-lifecycle`](docs/skills/bonedigger-lifecycle.md) | Working on the GitHub Actions reporting workflow, confirm priority escalation, or repo adoption |
| [`bonedigger-ujust`](docs/skills/bonedigger-ujust.md) | Working on the `ujust report` recipe in `projectbluefin/common`, the OTel config, PII scrubbing, or the gist upload flow |
| [`bonedigger-agent-donation`](docs/skills/bonedigger-agent-donation.md) | Working with the agent donation fast-track, `flow/` labels, `flow/agent-donation` issues, or agent-specific labels (`agent/blocked`, `hold`) |
| [`bonedigger-templates`](docs/skills/bonedigger-templates.md) | Adding, editing, or syncing GitHub issue templates; working on `sync-templates.yml` |

## Quick orientation

- **bonedigger is a reusable workflow**, not a standalone app. Consumers call `lifecycle.yml@main` from their own repo.
- **GitHub Issues is the only backend.** No database, no central server.
- **bonedigger now scopes to report intake + confirm-driven priority escalation.** Widget rendering, slash commands, label sync, and stale sweeps moved to `projectbluefin/common`.
- **Templates are mastered here** and synced to `common`, `dakota`, `bluefin`, and `bluefin-lts` automatically.
- **Agent donation issues** still skip triage and land directly in the queue — look for `Workflow: Agent Donation` in the issue body.

## Ownership rules — read before making changes

**bonedigger owns CI tooling only.**
bonedigger's scope: `lifecycle.yml`, `action.yml`, `templates/`, skill docs. That is all.

**Image content does NOT belong here.**
Just recipes, OTel configs, and system files are image content — they ship to users through `projectbluefin/common`. If a task involves editing a just recipe or a system config file, the work belongs in common, not bonedigger.

**Sync workflows between repos are always the wrong answer for image content.**
If you find yourself writing a workflow to copy a file from bonedigger to common (or to dakota), stop — the file is in the wrong place. Put it directly in the repo that ships it.

**The factory delivery pipeline:**
```
projectbluefin/common  (system_files/bluefin/)
  └─ ships to ALL images: bluefin, bluefin-lts, dakota, knuckle
       └─ via common.bst in each downstream repo

projectbluefin/dakota  (files/just-overrides/)
  └─ OVERRIDES common for dakota-specific files only
  └─ shared recipe changes go to common, not here
```

Before changing where a file lives, check which repo's build element installs it. The answer determines where edits belong.

## Key files

```
action.yml                              composite action entrypoint (→ lifecycle.yml)
.github/workflows/lifecycle.yml         reusable reporting + donation workflow
.github/workflows/sync-templates.yml    template sync to downstream repos
templates/                              canonical issue templates
docs/skills/                            agent skill docs (this directory)
```
