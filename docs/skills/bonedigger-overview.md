# bonedigger — overview

Client-server bug reporting for Project Bluefin, using GitHub Issues as the only backend. No central server. User owns their data.

## Architecture

```
USER'S MACHINE                    GITHUB
─────────────────                 ─────────────────────────────────────────
ujust report                      bonedigger lifecycle workflow
  └─ collects diagnostics           └─ detect `ujust report` issue bodies
  └─ PII scrub on-device            └─ sync confirm-based priority labels
  └─ user reviews locally           └─ fast-track agent donation issues
  └─ uploads to user's gist
  └─ opens issue w/ gist link     common lifecycle workflow
                                   └─ slash commands, queue state, widget
ujust confirm <issue#>            └─ bonedigger re-counts confirms
                                     and escalates priority labels
```

## User commands

Run on a Bluefin machine:
```bash
ujust report         # collect diagnostics, upload to gist, open issue
ujust confirm 42     # confirm you hit issue #42 too
ujust verify 42      # verify issue #42 is fixed after an update
```

## Repository structure

| Path | Purpose |
|------|---------|
| `templates/` | canonical GitHub issue templates (synced to all org repos) |
| `.github/workflows/lifecycle.yml` | reusable reporting workflow |
| `.github/workflows/sync-templates.yml` | auto-syncs templates to downstream repos |
| `action.yml` | composite action entrypoint (points to reusable workflow) |

## Adopting bonedigger in a repo

Add `.github/workflows/bonedigger.yml`:
```yaml
name: bonedigger
on:
  issues:
    types: [opened]
  issue_comment:
    types: [created]

permissions:
  issues: write
  contents: read

jobs:
  bonedigger:
    uses: projectbluefin/bonedigger/.github/workflows/lifecycle.yml@main
    secrets: inherit
```

The legacy `brand_name`, `brand_emoji`, and `pipeline_marker` inputs are still accepted for backward compatibility, but the slim workflow ignores them.

If a repo also wants slash commands, queue management, or the issue-body widget, pair bonedigger with `projectbluefin/common/.github/workflows/lifecycle.yml`.

## Privacy model

- All PII scrubbing happens on the user's machine before any upload
- Diagnostic gists belong to the user — bonedigger only reads them, never creates its own
- `machine-id` is hashed to an 8-char anonymous device ID — not reversible

## Related repos

- [projectbluefin/common](https://github.com/projectbluefin/common) — ships `ujust report` and owns lifecycle management; image content lives here
- [projectbluefin/dakota](https://github.com/projectbluefin/dakota) — inherits from common via `common.bst`; only dakota-specific overrides go in `default.just`
- [ublue-os/bluefin](https://github.com/ublue-os/bluefin) — downstream template recipient
- [ublue-os/bluefin-lts](https://github.com/ublue-os/bluefin-lts) — downstream template recipient

## Ownership rules

**bonedigger owns CI tooling, not image content.** Just recipes, OTel configs, and system files are image content — they belong in `projectbluefin/common/system_files/`. If a task asks you to add or edit image content here, redirect to common instead.

**Sync workflows are always the wrong answer.** If you find yourself writing a workflow to copy a file from bonedigger to common or dakota, the file is in the wrong repo. Put it where it ships.

**Map the delivery pipeline before moving files.** Check which repo's build element (`*.bst` or container build step) installs the file. That repo owns it. For shared files: common. For dakota-only overrides: dakota's `files/just-overrides/`.
