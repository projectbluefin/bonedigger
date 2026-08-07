# bonedigger — lifecycle workflow

Load when working on the GitHub Actions reporting workflow, confirm priority escalation, or agent donation fast-tracking.

## Current responsibility

bonedigger no longer owns the full issue lifecycle state machine.

**bonedigger keeps:**
- `ujust report` issue detection on `issues.opened`
- queue-preference recovery for reporters without label permissions
- confirm-count priority escalation on `issue_comment.created`
- agent donation fast-track label application on `issues.opened`

**Moved to `projectbluefin/common/.github/workflows/lifecycle.yml`:**
- slash commands (`/claim`, `/unclaim`, `/approve`, `/lgtm`, `/wontfix`, `/hold`)
- pipeline widget rendering
- label creation / synchronization
- stale sweeps and queue transitions

## Priority escalation (automatic)

Triggered on issue open for `ujust report` issues and on matching confirm comments:
- `3+` matching `ujust confirm <issue#>` comments → add `priority/p1`
- `5+` matching `ujust confirm <issue#>` comments → add `priority/p0`

Matching is scoped to the current issue number so a mistyped confirm comment on the wrong issue is ignored.

## Queue preferences

The Common client writes one validated hidden marker into every report body:

```text
<!-- bonedigger-queue-preference: 3-clanker-queue -->
<!-- bonedigger-queue-preference: 3-human-queue -->
<!-- bonedigger-queue-preference: none -->
```

GitHub silently drops labels requested during issue creation when the reporter
does not have repository triage access. On `issues.opened`, Bonedigger treats
the marker and the visible ``_Created with `ujust report`._`` signature as intake
evidence. If neither queue label is already present, it applies the requested
human or Clanker label with the workflow's `issues: write` permission. `none`
leaves the issue for normal triage. An existing queue label wins over the body
marker so automation does not overwrite a maintainer decision.

## Agent donation fast-track

If the issue body contains:

```
Workflow: Agent Donation
```

bonedigger applies:
- `status/approved`
- `status/queued`
- `flow/agent-donation`
- one of `flow/project-report`, `flow/issue-review`, or `flow/pr-review`

The downstream/common lifecycle workflow can then pick up the issue from there.

## Reusable workflow inputs

| Input | Default | Description |
|-------|---------|-------------|
| `brand_name` | `Bluefin` | Backward-compatibility input; ignored |
| `brand_emoji` | `🦖` | Backward-compatibility input; ignored |
| `pipeline_marker` | `<!-- bonedigger-pipeline -->` | Backward-compatibility input; ignored |
