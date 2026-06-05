# bonedigger — agent donation flow

Load when working on the agent donation fast-track: the special issue flow that auto-approves agent work requests without requiring manual triage.

## What it is

The agent donation flow is a fast-track path for submitting AI agent work requests via GitHub Issues. An issue tagged with the donation marker bypasses standard triage and lands directly in the queue with the labels needed for downstream lifecycle automation.

Use it to request agent work against any repo, issue, or PR in the Bluefin ecosystem.

## How to trigger it

Create a GitHub Issue in a bonedigger-enabled repo with this line anywhere in the body:

```
Workflow: Agent Donation
```

The bonedigger workflow detects this marker on `issues: opened` and applies the fast-track labels.

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
- `status/queued`
- `flow/agent-donation`
- one of `flow/project-report`, `flow/pr-review`, `flow/issue-review`

bonedigger only performs the fast-track labeling. Any follow-on widget rendering, queue movement, or slash-command handling is now owned by `projectbluefin/common/.github/workflows/lifecycle.yml`.

## Agent labels reference

| Label | Meaning |
|-------|---------|
| `agent/blocked` | Blocked — needs human input before work can continue |
| `needs-human/agent-oops` | Agent error — humans only |
| `hold` | Intentionally held — do not automate |
| `do-not-merge` | Do not merge or automate this item |

## Notes for agents working donated issues

- The `flow/` label tells the agent what kind of work is expected (project report, PR review, issue review)
- Always check for `agent/blocked` or `hold` labels before starting work
- When stuck, add `agent/blocked` and leave a comment explaining what human input is needed
- Do not remove `do-not-merge` or `hold` labels — these are set by humans intentionally
