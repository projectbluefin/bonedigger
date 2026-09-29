# bonedigger 🦴

> Client-side diagnostic reporting frameworks (`ujust report`) and canonical intake templates for Project Bluefin.

## Current scope

Bonedigger defines the client-side diagnostic reporting frameworks (`ujust report`), PII scrubbing standards, and canonical GitHub issue templates for Project Bluefin. Issue triage, labeling, and queue lifecycle are Hive-managed.

**bonedigger handles:**
- Specifications and architecture for the `ujust report` diagnostic tool
- Canonical GitHub issue templates (`templates/`) synced to factory repos
- Privacy models and PII scrubbing standards for bug reporting
## How it works

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

GitHub Issues is the only backend. No central server. The user owns their diagnostic data.

## Usage

### As a user

Run on your Bluefin machine:
```bash
ujust report       # collect diagnostics and open an issue
```

### Downstream repos

Issue templates in `templates/` are automatically synced to downstream repos via `.github/workflows/sync-templates.yml`.

## Repository structure

- `templates/` — canonical GitHub issue templates (synced to all org repos)
- `.github/workflows/sync-templates.yml` — auto-syncs templates to downstream repos
- `docs/skills/` — agent skill docs

## Privacy

- All PII scrubbing happens on the user's machine before any upload
- Diagnostic gists belong to the user under their own GitHub account
- No central server, no telemetry infrastructure required

## Part of Project Bluefin

- [projectbluefin/common](https://github.com/projectbluefin/common) — ships `ujust report` and common system files
- [projectbluefin/dakota](https://github.com/projectbluefin/dakota) — reference implementation
