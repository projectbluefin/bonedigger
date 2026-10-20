---
name: bonedigger-overview
description: Use when starting work in bonedigger, identifying reporting ownership, or distinguishing shipped behavior from proposed extensions.
---

# bonedigger — overview

Bonedigger is Project Bluefin's shared reporting-contract and issue-template repo.
GitHub Issues is the state backend; there is no central diagnostic server.

## When to Use

- Starting work on reporting specifications, privacy requirements, or intake forms
- Identifying which repository owns a requested behavior or file
- Checking whether a feature is implemented or only described in a proposal

## When NOT to Use

- Implementing or packaging the reporting client — that belongs in `projectbluefin/common`
- Changing issue state machines, assignments, or queues — lifecycle is Hive-owned

## Architecture and ownership

| Concern | Owner |
|---------|-------|
| Reporting specifications and privacy contracts | bonedigger — `docs/skills/` |
| Canonical issue forms and template PR automation | bonedigger — `templates/`, `sync-templates.yml` |
| Executable client and image packaging | `projectbluefin/common` — `bonedigger-report`, `60-bonedigger.just` |
| Issue triage, labeling, assignments, and lifecycle | Hive |

The client collects baseline diagnostics and optional smart-log profiles, scrubs
system logs locally, previews the result, and asks for submission consent. It
creates the issue directly with GitHub CLI. Only selected smart-log profiles are
published to a gist; no profiles means no gist. Cancelled or failed submissions
preserve a draft for resumption.

```bash
ujust report
ujust report --confirm 42
ujust report --resume /path/to/draft
```

`--confirm` accepts a positive issue number or GitHub issue URL and posts a
system fingerprint. It does not identify a fixed build, assert the bug is fixed,
or trigger an escalation workflow in this repo. See the [client guide](bonedigger-ujust.md).

## Core Process

1. Read the current implementation and the guide matching the requested surface.
2. Put shared executable changes in common; do not duplicate client code here.
3. Edit canonical forms here, then follow the [template guide](bonedigger-templates.md)
   to verify downstream branch → PR → merge delivery.
4. Keep the workflow's declared consumer roster and App-token scope aligned.
   Check destination availability; do not silently change the roster.
5. Mark proposals as proposals. [QR output](bonedigger-qrcode.md) and
   [screenshot analysis](bonedigger-screenshots.md) are not shipped client features.
6. Inspect each consumer's build element or container build step before changing
   file ownership. Shared image content belongs in common, not a new copy workflow.

## Privacy model

- Issues and selected smart-log gists are public under the user's GitHub account.
- System-log scrubbing runs locally; regexes cannot guarantee removal of all PII.
- User-authored text is not automatically scrubbed; local review is essential.
- The current client does not derive a machine identifier, collect OTel telemetry,
  or upload images. Do not infer those behaviors from retired documentation.

## Common Rationalizations

- "The spec merged, so the feature ships." → Verify the client and image delivery.
- "The sync matrix exists, so consumers are synchronized." → Verify runs, PRs, and merges.
- "A shared client file can be copied from here." → Put it directly in common.

## Red Flags

- References to deleted lifecycle workflows or a composite action
- A mandatory gist, hashed machine-id, or unimplemented feature described as current
- Client code in bonedigger, or a workflow copying image content to common
- Claims of green CI or downstream delivery based only on local checks

## Verification

- [ ] Implementation claims match current common source; proposals are explicit.
- [ ] README, AGENTS, and the relevant guide agree on ownership and commands.
- [ ] Markdown links and targets resolve.
- [ ] `pre-commit run --all-files` passes; workflow changes also pass actionlint.
- [ ] Actual CI and delivery coverage is reported, not assumed.

## Sources

- [Reporting client in common](https://github.com/projectbluefin/common/blob/main/system_files/bluefin/usr/libexec/bonedigger-report)
- [Recipe entry point in common](https://github.com/projectbluefin/common/blob/main/system_files/bluefin/usr/share/ublue-os/just/60-bonedigger.just)
- [Template synchronization](../../.github/workflows/sync-templates.yml)
- [Contribution contract](../../AGENTS.md)
