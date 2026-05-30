# bonedigger — issue templates

Load when adding, editing, or syncing GitHub issue templates across the Bluefin ecosystem.

## Template files

Located in `templates/` in this repo. Synced automatically to downstream repos on push to `main`.

| File | Type | Label |
|------|------|-------|
| `bug-report.yml` | Bug | `type/bug` |
| `feature-request.yml` | Feature | (check file) |
| `help-this-project.yml` | Help request | (check file) |
| `config.yml` | Template config | n/a |

### bug-report.yml structure

- **ujust report gist URL** (optional input) — pre-fills from `ujust report` query param `?report-link=<encoded-url>`
- **What happened?** (required textarea) — what was seen vs. expected, hardware model, exact error
- **Extra context** (optional textarea) — upstream bug links, regression narrowing

## Template sync workflow

`sync-templates.yml` automatically syncs `templates/*.yml` to downstream repos when `templates/` changes on `main`.

**Downstream repos:**
- `projectbluefin/common`
- `projectbluefin/dakota`
- `ublue-os/bluefin`
- `ublue-os/bluefin-lts`

**Mechanism:**
1. Checkout bonedigger + downstream repo
2. Copy `templates/*.yml` → `downstream/.github/ISSUE_TEMPLATE/`
3. If diff exists, open a PR on the downstream repo

**Required secret:** `BONEDIGGER_SYNC_TOKEN` — PAT with write access to all downstream repos.

**PR branch naming:** `bonedigger/sync-templates-<sha8>`

## ⚠ Edit templates in bonedigger only

Downstream repos receive templates via automated PR. Do **not** edit template files directly in `common`, `dakota`, `bluefin`, or `bluefin-lts` — changes will be overwritten on the next bonedigger push.

## config.yml

Controls GitHub's issue template chooser UI (blank issue permission, contact links, etc.). Check `templates/config.yml` for current settings.
