---
name: bonedigger-templates
description: Use when adding, editing, or syncing GitHub issue templates in bonedigger, or when changing `.github/workflows/sync-templates.yml`.
metadata:
  context7-sources:
    - /websites/github_en_actions
---

# bonedigger — issue templates

## When to Use

- Updating files under `templates/`
- Changing `.github/workflows/sync-templates.yml`
- Verifying which downstream repos receive bonedigger-managed templates
- Debugging why a template sync branch or PR was not created

## When NOT to Use

- Editing `ujust report`, OTel config, or other image content — that belongs in `projectbluefin/common`
- Changing lifecycle queue logic or confirm escalation — use the lifecycle skill instead
- Editing downstream template copies directly in `common`, `dakota`, `bluefin`, `bluefin-lts`, or `knuckle`

## Core Process

1. Edit the canonical templates in `templates/` only.
2. Confirm the sync workflow still targets every downstream consumer:
   - `projectbluefin/bluefin`
   - `projectbluefin/bluefin-lts`
   - `projectbluefin/common`
   - `projectbluefin/dakota`
   - `projectbluefin/knuckle`
3. Keep the sync workflow on the mergeraptor GitHub App token pattern (`actions/create-github-app-token`), not a PAT.
4. Preserve the branch-then-PR flow in `sync-templates.yml`:
   1. check out bonedigger and the downstream repo
   2. copy `templates/*.yml` into `downstream/.github/ISSUE_TEMPLATE/`
   3. commit and push `bonedigger/sync-templates-<sha8>`
   4. open the downstream PR
5. Do **not** set `cancel-in-progress: true` for the per-repo concurrency group. The workflow pushes the branch before opening the PR, so cancellation between those steps can orphan a remote branch with no PR.
6. Keep external GitHub Actions pinned to full SHAs with inline version comments. Internal `projectbluefin/actions/*` and `projectbluefin/bonedigger/*` refs may stay on version tags, including subpath refs such as `projectbluefin/actions/sync@v3`.
7. Validate with:
   - `pre-commit run --all-files`
   - `actionlint .github/workflows/*.yml`

## Template Files

| File | Type | Label |
|------|------|-------|
| `bug-report.yml` | Bug | `type/bug` |
| `feature-request.yml` | Feature | check file |
| `help-this-project.yml` | Help request | check file |
| `config.yml` | Template chooser config | n/a |

### bug-report.yml structure

- **ujust report gist URL** (optional input) — pre-fills from `ujust report` query param `?report-link=<encoded-url>`
- **What happened?** (required textarea) — what was seen vs. expected, hardware model, exact error
- **Extra context** (optional textarea) — upstream bug links, regression narrowing

## Common Rationalizations

- “I can edit the downstream template copy directly.” → The next bonedigger sync PR will overwrite it.
- “`cancel-in-progress: true` keeps things tidy.” → Not for this workflow; it can cancel after `git push` and before `gh pr create`.
- “A major tag like `@v5` is pinned enough.” → Factory policy here is full SHA pins for external actions.
- “Only `projectbluefin/actions@vN` needs the regex exemption.” → Subpath actions like `projectbluefin/actions/sync@v3` must also be exempted.

## Red Flags

- A sync run can push a branch but never open a PR
- The workflow references a PAT instead of the mergeraptor app token
- Downstream repo lists in the skill and workflow do not match
- A pre-commit regex flags `projectbluefin/actions/<subpath>@vN`
- A workflow or copilot setup file uses floating external action tags like `@main` or `@v5`

## Verification

- [ ] Templates were edited only in `templates/`
- [ ] `sync-templates.yml` still targets bluefin, bluefin-lts, common, dakota, and knuckle
- [ ] Workflow concurrency does **not** cancel in-progress runs for the same downstream repo
- [ ] External actions are pinned to 40-character SHAs with inline version comments
- [ ] `pre-commit run --all-files` passes
- [ ] `actionlint .github/workflows/*.yml` passes

## Sources

- Context7: `/websites/github_en_actions` for GitHub Actions concurrency behavior
