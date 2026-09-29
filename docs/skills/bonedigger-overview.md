# bonedigger — overview

Client-server bug reporting for Project Bluefin, using GitHub Issues as the only backend. No central server. User owns their data.

## Architecture

```
USER'S MACHINE                    GITHUB
─────────────────                 ─────────────────────────────────────────
ujust report                      GitHub Issues + Hive
  └─ collects diagnostics           └─ intake structured issue reports
  └─ PII scrub on-device            └─ issue lifecycle managed by Hive
  └─ user reviews locally
  └─ uploads to user's gist
  └─ opens issue w/ gist link
```

## User commands

Run on a Bluefin machine:
```bash
ujust report         # collect diagnostics, upload to gist, open issue
```

## Repository structure

| Path | Purpose |
|------|---------|
| `templates/` | canonical GitHub issue templates (synced to all org repos) |
| `.github/workflows/sync-templates.yml` | auto-syncs templates to downstream repos |
| `docs/skills/` | agent skill docs |

## Template sync

- `projectbluefin/bluefin`
- `projectbluefin/bluefin-lts`
- `projectbluefin/common`
- `projectbluefin/dakota`
- `projectbluefin/knuckle`
## Privacy model

- All PII scrubbing happens on the user's machine before any upload
- Diagnostic gists belong to the user under their own GitHub account
- `machine-id` is hashed to an 8-char anonymous device ID — not reversible

## Related repos

- [projectbluefin/common](https://github.com/projectbluefin/common) — ships `ujust report` and system files; image content lives here
- [projectbluefin/dakota](https://github.com/projectbluefin/dakota) — inherits from common via `common.bst`; only dakota-specific overrides go in `default.just`
- [projectbluefin/bluefin](https://github.com/projectbluefin/bluefin) — downstream template recipient
- [projectbluefin/bluefin-lts](https://github.com/projectbluefin/bluefin-lts) — downstream template recipient
- [projectbluefin/knuckle](https://github.com/projectbluefin/knuckle) — downstream template recipient

## Ownership rules

**bonedigger owns the reporting frameworks, intake templates, and template sync.** Just recipes, OTel configs, and system binaries are image content packaged and shipped via `projectbluefin/common`. Bonedigger maintains the specifications, documentation, and intake contracts.

**Sync workflows are always the wrong answer.** If you find yourself writing a workflow to copy a file from bonedigger to common or dakota, the file is in the wrong repo. Put it where it ships.

**Map the delivery pipeline before moving files.** Check which repo's build element (`*.bst` or container build step) installs the file. That repo owns it. For shared files: common. For dakota-only overrides: dakota's `files/just-overrides/`.
