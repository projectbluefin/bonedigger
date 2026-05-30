# bonedigger — agent donation flow

Load when working on the agent donation fast-track: the special issue flow that auto-approves agent work requests without requiring manual triage.

## What it is

The agent donation flow is a fast-track path for submitting AI agent work requests via GitHub Issues. An issue tagged with the donation marker bypasses standard triage (filed → approved) and lands directly in the queue (queued), ready to claim.

Use it to request agent work against any repo, issue, or PR in the Bluefin ecosystem.

## How to trigger it

Create a GitHub Issue in a bonedigger-enabled repo with this line anywhere in the body:

```
Workflow: Agent Donation
```

The lifecycle action detects this marker on `issues: opened` and applies the fast-track path.

## Flow detection and label assignment

The lifecycle action parses the issue body for URLs to determine the flow type:

| Issue body contains | Flow label applied |
|--------------------|-------------------|
| `Workflow: Agent Donation` only | `flow/project-report` |
| `Workflow: Agent Donation` + a PR URL (`/pull/N`) | `flow/pr-review` |
| `Workflow: Agent Donation` + an issue URL (`/issues/N`) | `flow/issue-review` |

## Labels applied automatically

On detection, the action applies:
- `status/approved`
- `queue/agent-ready`
- `kind:agent-donation`
- One of `flow/project-report`, `flow/pr-review`, `flow/issue-review`

The pipeline widget is set to **queued** (stage 2) immediately — skipping the filed/triage stage.

## Pipeline widget at donation

```
Brand Name Emoji  ·  issue pipeline
─────────────────────────────────────────────────
  ✓  filed      report received
  ✓  approved   signed off by a maintainer
  ▶  queued     waiting for a contributor to claim
  ·  claimed    —
  ·  done       —
─────────────────────────────────────────────────
  report:       missing     ·  confirms: 0
  area:         —           ·  priority: —
  next action:  comment /claim to take this
```

## Claiming donated work

Comment `/claim` on the issue to assign yourself and move to stage 3 (claimed). Standard lifecycle rules apply from that point on.

## Agent labels reference

| Label | Meaning |
|-------|---------|
| `agent/blocked` | Blocked — needs human input before work can continue |
| `needs-human/agent-oops` | Agent error — do not touch; humans only |
| `hold` | Intentionally held — do not automate |
| `do-not-merge` | Do not merge or automate this item |

## Notes for agents working donated issues

- The `flow/` label tells the agent what kind of work is expected (project report, PR review, issue review)
- Always check for `agent/blocked` or `hold` labels before starting work
- When stuck, add `agent/blocked` and leave a comment explaining what human input is needed
- Do not remove `do-not-merge` or `hold` labels — these are set by humans intentionally
