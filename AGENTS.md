# AGENTS.md — bonedigger

Skill index for AI agents working in this repo. Load the skills relevant to your task; skills are in [`docs/skills/`](docs/skills/).

## STOP — before you write a single line of code

1. Read `bonedigger-overview.md` (architecture, repo layout, what bonedigger actually is).
2. Read every skill doc that matches your task area (see Skills table below). No skimming — the answers to common mistakes are in those docs.
3. Identify the exact scope of your change. If it touches more than one logical area, stop and split the work.
4. Do not proceed until you can answer: what files change, why, and how will you verify the result?
5. Read current `origin/main` in an isolated worktree if the checkout is stale or contains user WIP. Never review retired code as if it were deployed.

## Verification — you are not done until you verify

**Done means verified, not "I believe this should work."**

| Change type | Required verification |
|-------------|----------------------|
| Any workflow change | `actionlint .github/workflows/*.yml` — inspect output, fix all errors |
| Any file change | `pre-commit run --all-files` — must pass clean |
| Any commit pushed | Inspect `gh run list --repo projectbluefin/bonedigger --limit 5` and runs for that commit; wait for applicable runs and inspect failures. Missing CI is not a passing check. |
| Issue/PR edit | Re-fetch and verify the intended body, state, type, and labels; preserve human content |
| Template change | Verify the declared consumer roster, App-token scope, destination branches, and chooser-config diff |

Never report success before running these checks and reading the output.

The configured pre-commit hooks cover YAML parsing, whitespace, merge conflicts,
private keys, file size, workflow linting, and action-reference policy. They do not
validate the GitHub issue-form schema or run unit tests. The `pr-validate`
workflow (`.github/workflows/pr-validate.yml`) runs on pull requests to `main`
and merge-queue groups: it executes `python3 -m unittest discover -s tests` and
then `pre-commit run --all-files`. It still does not validate the issue-form
schema. Report the actual coverage rather than inferring it.

`.github/copilot-setup-steps.yml` is outside `.github/workflows/`, so GitHub does
not execute it as a setup workflow. Do not assume it installed local tools.

For docs-only work, render/read the Markdown and verify links and implementation
claims. Local checks do not prove downstream template delivery. When modifying
executable code, reproduce the affected path and run its complete test file.

## Anti-patterns — these are mistakes, not shortcuts

- **Do not claim done without verifying.** "I've updated the file" is not done. Run the checks. Read the output.
- **Do not post extra comments to narrate your actions.** Hive owns lifecycle; bonedigger has no slash-command or widget workflow. Use in-place edits where appropriate and preserve human content.
- **Do not mix unrelated changes in one branch.** One branch = one logical fix. If you find something else broken, file a separate issue.
- **Do not skip reading the skill docs.** The docs exist because agents made these mistakes. The answers are already there.
- **Do not guess at workflow patterns.** Cross-repo automation uses mergeraptor App tokens, not PATs. Bonedigger changes target `main`; template-sync PRs target `testing` for Dakota and `main` for other declared consumers. Inspect labels before using them.
- **Do not push with `--no-verify`.** Ever.

## Skills

| Skill | Load when… |
|-------|-----------|
| [`bonedigger-overview`](docs/skills/bonedigger-overview.md) | Starting any work in this repo — architecture, user commands, repo layout |
| [`bonedigger-ujust`](docs/skills/bonedigger-ujust.md) | Current `report`, `--confirm`, and `--resume` behavior, smart logs, privacy, and client ownership |
| [`bonedigger-qrcode`](docs/skills/bonedigger-qrcode.md) | Proposed URL-only console QR output; not shipped client behavior |
| [`bonedigger-templates`](docs/skills/bonedigger-templates.md) | Adding, editing, or syncing GitHub issue templates; working on `sync-templates.yml` |
| [`bonedigger-screenshots`](docs/skills/bonedigger-screenshots.md) | Proposed on-device screenshot/OCR extension and its privacy requirements; not shipped client behavior |

## Quick orientation

- **bonedigger owns reporting specifications and privacy contracts**, canonical intake templates, and their synchronization workflow.
- **common owns the executable client.** `60-bonedigger.just` invokes `/usr/libexec/bonedigger-report`; shared image changes go there.
- **Issue lifecycle is Hive-managed.** No lifecycle workflow or composite action is shipped here.
- **GitHub Issues is the only state backend.** The client creates issues directly; selected smart-log gists are optional.
- **Template delivery is branch → PR → merge.** Check every consumer's result; a configured matrix is not evidence of successful delivery.

## Ownership rules — read before making changes

**bonedigger owns the reporting frameworks, intake templates, and template sync.**
bonedigger's scope: `templates/`, `sync-templates.yml`, skill docs, and `ujust report` diagnostic specifications.

**Image content ships through `common`.**
Just recipes, system binaries, and any collector configuration are packaged in `projectbluefin/common`. The current reporting client does not run an OTel collector. Bonedigger maintains specifications, documentation, and intake contracts, not duplicate client implementations.

**Sync workflows between repos are always the wrong answer for image content.**
If you find yourself writing a workflow to copy a file from bonedigger to common (or to dakota), stop — the file is in the wrong place. Put it directly in the repo that ships it.

**Map the factory delivery pipeline before moving files.**
Inspect the consumer's build element (`*.bst`) or container build step to identify
what installs a shared file. Shared client behavior belongs in common; Dakota-only
overrides belong in Dakota. Do not assume every consumer has identical packaging.

Keep the declared five-consumer roster in the template guide aligned with the
workflow and its token scope. Check whether destinations are archived or otherwise
unwritable before attempting delivery; changing the roster requires a maintainer
decision, not an agent silently deleting a target.

## Key files

```
.github/workflows/sync-templates.yml    template sync to downstream repos
templates/                              canonical issue templates
docs/skills/                            agent skill docs (this directory)
```
