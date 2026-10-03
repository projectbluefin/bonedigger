---
name: bonedigger-templates
description: Use when editing canonical issue forms, reviewing template synchronization, or verifying downstream intake contracts.
metadata:
  context7-sources:
    - /websites/github_en_actions
    - /github/docs
---

# bonedigger — issue templates

## When to Use

- Editing `templates/` or `.github/workflows/sync-templates.yml`
- Checking form fields, issue types, labels, or downstream delivery
- Investigating a failed sync or a branch pushed without a corresponding PR

## When NOT to Use

- Changing the executable reporting client or image packaging — those belong in common
- Changing issue lifecycle — Hive owns triage and queues
- Hand-editing synchronized downstream copies instead of their canonical source

## Core Process

1. Read the canonical forms and current workflow before changing their contract.
2. Preserve the declared consumer roster unless a maintainer approves a change:
   - `projectbluefin/bluefin`
   - `projectbluefin/bluefin-lts`
   - `projectbluefin/common`
   - `projectbluefin/dakota`
   - `projectbluefin/knuckle`
   Keep `matrix.repo` and the App-token `repositories` scope aligned. Check whether
   each destination is archived, writable, and still a consumer; a listed target
   is not proof it can receive changes. Do not silently drop archived destinations.
3. Use the mergeraptor GitHub App token pattern, not a PAT. The workflow reads
   `secrets.MERGERAPTOR_APP_ID` and `secrets.MERGERAPTOR_PRIVATE_KEY`; check secret
   availability and App installation permissions without exposing their values.
4. Follow the existing delivery path:
   - A push to `main` changing `templates/**` triggers synchronization.
   - Check out bonedigger and each downstream repository.
   - Copy all `templates/*.yml` into `downstream/.github/ISSUE_TEMPLATE/`.
   - Commit and push `bonedigger/sync-templates-<sha8>`.
   - Open a PR against `testing` for Dakota and `main` for the other consumers,
     without requesting labels that may not exist in the destination. PR creation
     failures remain visible and fail the sync step.
   - Review and merge downstream PRs before calling the forms deployed.
5. Keep per-repository `cancel-in-progress: false`. Cancellation after push but
   before PR creation can strand a remote branch. Serialization does not make
   reruns idempotent or preserve every pending run.
6. Pin external actions to full SHAs with version comments. Internal
   `projectbluefin/actions/*` and `projectbluefin/bonedigger/*` references may use
   version tags, including subpaths.
7. Validate local changes, then inspect the delivery run and downstream PRs for
   the exact revision. A YAML parse, a clean lint, or an absent CI check is not
   proof that GitHub renders the forms or consumers received them.

## Current form contract

| File | Issue type | Declared labels | Required inputs |
|------|------------|-----------------|-----------------|
| `bug-report.yml` | `Bug` | `type/bug` | `report-link`, `what-happened` |
| `feature-request.yml` | `Feature` | `type/feature`, `status/discussing` | `problem`, `solution` |
| `help-this-project.yml` | none | `kind:agent-donation` | `target-url`, `flow`, `goal` |
| `config.yml` | chooser configuration | none | `blank_issues_enabled: true` |

Labels are declarations, not label creation. GitHub omits a form's label if it
is absent from the destination repository. Inspect destination labels and enabled
organization issue types before relying on them for routing. This repository
ships no donation fast-track or approval workflow; the help form's text does not
prove Hive integration exists or that the request was admitted to a queue.

The bug form currently requires a gist URL, but the [shipped client](bonedigger-ujust.md)
creates an issue directly and uploads a gist only for selected smart-log profiles.
It does not open the form or prefill `report-link`. Do not tell a user that running
`ujust report` always produces a gist for this form, or recommend inventing a URL.
Correcting that mismatch requires a canonical template change, not documentation
that pretends the current field is optional.

## Delivery hazards to verify

- **New files:** the workflow's `git diff --quiet` does not see untracked additions.
  Exercise an added form, a changed form, and an unchanged copy when changing
  detection; test both destination bases, not only common's `main` path.
- **Chooser configuration:** copying `config.yml` replaces the destination file.
  The canonical file has no `contact_links`, so existing downstream links can be
  lost. Review the config diff before merging a sync PR.
- **Reruns:** a per-SHA branch may already exist after a partial failure. A fresh
  rerun can encounter a non-fast-forward push or an existing PR. Inspect both
  before retrying; do not describe the current workflow as idempotent.
- **Revisions and triggers:** the current workflow has no `workflow_dispatch`.
  Re-running a failed run retains its original commit/ref; it does not test a
  subsequent repair on `main`. A workflow-only change also does not match the
  `templates/**` push filter.

Use actual job logs to distinguish startup/token failure from shell-script or
PR-creation failure. Do not diagnose missing secrets merely from an old run's
failure when the source has changed.

## Common Rationalizations

- "The copied files exist, so the sync worked." → Verify the branch, PR, merge, and form.
- "A label in YAML will be created." → Labels must already exist downstream.
- "Re-running an old failure tests the latest fix." → Check the run's original revision.
- "Pre-commit runs every test." → Only configured hooks run; inspect their coverage.

## Red Flags

- A declared consumer is archived, unavailable, or omitted from the token scope.
- A new template is skipped, a config diff deletes contact links, or a push has no PR.
- Form instructions promise a required gist that the client may not create.
- Donation routing or lifecycle transitions attributed to a workflow this repo lacks.
- Floating external action tags or cancellation of in-progress sync jobs.

## Verification

- [ ] Canonical form IDs, required fields, types, and labels match their intended contract.
- [ ] Destination label/type availability and archived status have been checked.
- [ ] Workflow matrix and App-token scope match the declared five consumers.
- [ ] PR bases are `testing` for Dakota and `main` elsewhere.
- [ ] New, modified, and unchanged files are exercised when sync behavior changes.
- [ ] Chooser links and rerun behavior are reviewed before downstream merges.
- [ ] `pre-commit run --all-files` and `actionlint .github/workflows/*.yml` pass.
- [ ] Applicable checks and downstream delivery are verified for the actual revision.

Pre-commit currently checks YAML syntax and workflow policy, not GitHub issue-form
schema or unit tests. There is no PR-validation workflow or test directory on
`main`. Run any tests explicitly if introduced; merely adding pre-commit CI does
not run tests without a corresponding hook or job.

## Sources

- [Canonical templates](../../templates/) and [sync workflow](../../.github/workflows/sync-templates.yml)
- [Configured checks](../../.pre-commit-config.yaml)
- [Issue-form syntax](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
- [Actions concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [Workflow reruns](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs)
- Context7 `/github/docs` and `/websites/github_en_actions`; current repository files
  determine the configured behavior, not proposed workflow changes.
