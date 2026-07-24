# bonedigger — lifecycle workflow

Load when working on the GitHub Actions reporting workflow, confirm priority escalation, label sync, or agent donation fast-tracking.

## Current responsibility

bonedigger owns the reusable lifecycle surface for the clanker-queue rollout.

**bonedigger keeps:**
- `ujust report` issue detection on `issues.opened`
- confirm-count priority escalation on `issue_comment.created`
- agent donation fast-track label application on `issues.opened`
- label creation / synchronization via `labels.json`

**During the rollout, bonedigger dual-writes legacy labels and `clanker-queue/*`:**
- `status/triage` + `clanker-queue/triage`
- `status/queued` + `clanker-queue/ready`
- `priority/p1` + `clanker-queue/p1`
- `priority/p0` + `clanker-queue/p0`

## Priority escalation (automatic)

Triggered on issue open for `ujust report` issues and on matching confirm comments:
- `3+` matching `ujust confirm <issue#>` comments → add `priority/p1` and `clanker-queue/p1`
- `5+` matching `ujust confirm <issue#>` comments → add `priority/p0` and `clanker-queue/p0`

Matching is scoped to the current issue number so a mistyped confirm comment on the wrong issue is ignored.

## Agent donation fast-track

If the issue body contains:

```
Workflow: Agent Donation
```

bonedigger applies:
- `status/approved`
- `status/queued`
- `clanker-queue/ready`
- `flow/agent-donation`
- one of `flow/project-report`, `flow/issue-review`, or `flow/pr-review`

The downstream lifecycle compatibility layer can then pick up the issue from there during the soak.

## Reusable workflow inputs

| Input | Default | Description |
|-------|---------|-------------|
| `brand_name` | `Bluefin` | Backward-compatibility input; ignored |
| `brand_emoji` | `🦖` | Backward-compatibility input; ignored |
| `pipeline_marker` | `<!-- bonedigger-pipeline -->` | Backward-compatibility input; ignored |
