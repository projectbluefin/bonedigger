---
name: bonedigger-ujust
description: Use when documenting, supporting, or changing the shipped ujust report client in projectbluefin/common, including smart logs, privacy review, confirmation comments, and resumable drafts.
---

# Bonedigger — `ujust report`

The executable client belongs to **projectbluefin/common**; Bonedigger owns reporting specifications, privacy contracts, canonical templates, and template sync. Hive owns issue lifecycle. This guide describes the pinned implementation in [Sources](#sources), not proposed capabilities.

## When to Use

- Help a user report a bug, request a feature, resume a draft, or add deployment evidence to an existing issue.
- Check collection, consent, routing, or persistence claims against the shipped client before changing documentation.

## When NOT to Use

- Implement issue lifecycle automation here: that is Hive's responsibility.
- Treat [QR codes](bonedigger-qrcode.md) or [screenshots](bonedigger-screenshots.md) as shipped functionality. Both are proposed specifications, not current report steps or installed dependencies.

## Core Process

### Report and review

```bash
ujust report
ujust report --confirm https://github.com/projectbluefin/common/issues/123
ujust report --resume "$HOME/.local/state/ujust-report/drafts/draft-XXXXXX"
```

Use the actual preserved draft path, not the placeholder. `--confirm` and `--resume` are mutually exclusive.

1. Choose **Bug report**, **Feature request**, or **Get help**. Help prints the Bluefin Discussions URL without creating an issue; the confirmation menu item prints the `--confirm` usage.
2. A bug requires a title, description, and reproduction steps, then offers any of the five smart-log profiles (including none). A feature requires a title and description, goes to `projectbluefin/common`, and collects no diagnostic baseline or profiles.
3. Review `issue.md` and every selected profile: `gum pager` on an interactive terminal, plain output otherwise. Bug reports then ask for machine analysis (`3-clanker-queue`), human-only interaction (`3-human-queue`), or no queue preference. The choice is stored as a label and an HTML preference marker; it is not a lifecycle guarantee.
4. Explicitly consent to the public issue and, when selected, public smart logs. Only selected profile files become a public gist; the baseline is the issue body, and **a gist is not required**. The client appends the gist URL and creates the issue directly through `gh issue create`.
5. On success, the client attempts to save a local copy, removes the draft, prints the issue URL, and offers to open it in a browser on an interactive terminal.

### Actual collection

The bug baseline contains user description and reproduction text; image ref, tag, version, flavor, booted digest, kernel and architecture; up to 20 failed systemd unit names; and the last 40 current-boot journal errors (`err..emerg`). It does not collect a general hardware inventory.

| Selectable profile | Collected evidence | File |
| --- | --- | --- |
| Desktop / graphics | Enabled GNOME extensions, graphics-controller `lspci` lines, last 200 current-boot GDM/GNOME Shell warnings through alerts | `desktop-graphics.md` |
| Sleep / crash | Last 250 matching previous-boot kernel panic/oops/BUG/call-trace/sleep/resume/hung-task/lockup lines; last 50 coredump index entries from seven days | `sleep-crash.md` |
| Update / boot | Text `bootc status`; last 250 current-boot warnings through alerts for bootc update, rpm-ostreed, and systemd boot-update services | `update-boot.md` |
| Networking | Last 250 current-boot NetworkManager warnings through alerts; device/type/state from `nmcli` | `networking.md` |
| Flatpak / application | Installed Flatpak application IDs and versions; last 250 current-boot Flatpak helper/portal warnings through alerts | `flatpak-application.md` |

The sleep profile is a keyword excerpt, **not a boot-end classifier or proof of a crash**. No pstore or kdump artifacts are captured. Baseline content is capped at 60 KiB, with a 64 KiB cap after adding a gist link. Profiles are capped at 500 KiB each, reduced equally when needed to keep their combined allowance within 2 MiB. Truncation adds an omission marker.

### Privacy and consent

`scrub_kernel_log` matches MAC addresses before IPv6, IPv4/IPv6 patterns, UUID-shaped strings, `eui.`/`naa.`/`wwn.` hex identifiers, and home-directory path components. `scrub_journal_log` adds `USER=`/`LOGNAME=` assignments and email-pattern redaction. These filters cover collected failed-unit names and profile/log output, not every report field.

**Review remains necessary.** Title, description, reproduction, branding, and image metadata are not passed through these scrubbers. Regex matching is not comprehensive PII removal: hostnames, secrets, unusual addresses/identifiers, and sensitive prose can remain. No general NVIDIA UUID/serial inventory scrubber exists. No machine-id hash or persistent client machine-identity tracker is created; the deployed image digest is build/deployment evidence, not an anonymous device ID. Public issues and public gists expose their contents and associate submission with the GitHub account. Decline submission if review reveals sensitive material; edit the preserved local files and resume.

### Drafts and recovery

Drafts live under `${XDG_STATE_HOME:-$HOME/.local/state}/ujust-report/drafts/draft-XXXXXX`, not a runtime-directory report bundle. They store `issue.md`, `title.txt`, `repo.txt`, `queue-label.txt`, selected profile Markdown and `profile-files.txt`; bugs also have `bug-report.txt`, and a successful gist upload records `gist-url.txt`.

Declined submission or queue selection, dependency/authentication failure, gist failure, and issue-creation failure preserve the draft. Resume loads its saved repository, title, body and existing listed profiles, previews again, and asks bug queue preference and publication consent again; it does not recollect diagnostics. An existing `gist-url.txt` reuses the previously published gist. If gist publication succeeded but issue creation failed, the gist is already public: cancelling later does not retract it.

After successful issue creation, `persist_local_copy` replaces `${XDG_STATE_HOME:-$HOME/.local/state}/ujust-report/last/`: `issue.md` becomes `summary.md`, and other Markdown profiles are copied. It also copies `journal.txt` if present in a draft, although the current collector does not create it. A local-copy failure emits a warning; the submitted draft is still removed. The local `last` directory is a latest-copy convenience, not an archive.

### Confirmation is evidence, not resolution

`--confirm` accepts a positive issue number (using current image routing) or an HTTPS GitHub issue URL (using that URL's repository). It displays and posts an image ref/tag/version/digest, kernel, architecture, and up to ten failed units. It checks GitHub readiness; an interactive terminal also asks before posting. Noninteractive confirmation has no additional posting-consent prompt, so do not describe it as universally interactive.

The comment records the exact deployed fingerprint **when available**; unavailable values can be `unknown`. It does not test reproduction, compare fix versions, prove a fix shipped, or close the issue. A human must connect this deployment evidence to observed behavior and the proposed fix.

### Routing and dependencies

Image metadata starts at `IMAGE_INFO_FILE`. With `jq`, `read_boot_status` prefers the live booted ref from `bootc status --json`, falling back to `/run/ublue-os/booted-image` when no ref is available. It updates ref, tag (unless digest-pinned), and image name; version comes from `/etc/os-release`. The snapshot fallback supplies a ref, not a digest.

`route_issue_repo` delegates to **`ublue-image-repo`**, not `BUG_REPORT_URL`. In the pinned helper, `bluefin-lts*` names route to `projectbluefin/bluefin-lts`; plain `bluefin` uses that repository for `lts*` tags and `projectbluefin/bluefin` otherwise. Other `bluefin*` names route to Bluefin, and `dakota*` names to `projectbluefin/dakota`, regardless of tag. Unrecognized names use Bluefin LTS for `lts*` tags, otherwise the caller's default: `projectbluefin/common` for reports and confirmations by issue number. Feature requests always route to common. Keep this grammar in the shared helper, not a second client lookup table.

The Bluefin and Bluefin LTS destinations are archived, so reports routed there cannot currently be filed. [Common issue #1499](https://github.com/projectbluefin/common/issues/1499) tracks routing them to the caller's default instead; until a fix merges in common, do not describe that routing as shipped. Existing drafts keep their saved `repo.txt` destination on resume, and explicit GitHub issue URLs keep the repository in the URL. `ujust changelogs` also uses this helper with its explicit `projectbluefin/bluefin` default.

The Bash client calls `gum` without installing it. Missing `gh` triggers an offer to install it with Homebrew; missing/failed Homebrew leaves the draft intact. Failed active authentication offers `gh auth login --web --skip-ssh-key`. Missing `jq` yields unknown image fields/digest; bootc failures yield unavailable status. Diagnostic commands generally tolerate unavailable commands or inaccessible logs with empty output: that is not evidence that the system is healthy. Browser opening uses `xdg-open`, falling back to printing the URL. No dependency is promised installed by this guide.

Actual environment inputs are `IMAGE_INFO_FILE`, `BONEDIGGER_BRAND`, `XDG_STATE_HOME`, `HOME`, and `UBLUE_IMAGE_REPO_BIN` (helper override); command lookup uses `PATH`. The wrapper exports `BONEDIGGER_VERSION`, but the client does not read it. There is no client `BONEDIGGER_ISSUE_URL` override.

## Common Rationalizations

- “Scrubbed means safe to publish.” Pattern filters are incomplete and do not scrub user-authored text; review every payload.
- “Confirm means fixed.” A fingerprint comment is evidence for human verification, not a test result.
- “Resume starts over.” It submits saved evidence and can reuse an already-public gist.

## Red Flags

- Promising installed tools, automatic diagnosis, guaranteed anonymity, or mandatory gist upload.
- Editing this repository to change executable client behavior, or copying the routing grammar out of the shared helper.
- Publishing without preview and consent, or presenting proposal specs as shipped collection.

## Verification

- [ ] Check the current `main`, `submit_draft`, `confirm_report`, collection, scrub, persistence, and routing functions before making behavior claims.
- [ ] For client changes in common, exercise report-without-profiles, profile publication, declined consent, failed upload followed by resume, and confirmation using isolated fixtures and a nonpublishing GitHub CLI substitute.
- [ ] Run the affected complete test file; never publish real diagnostics merely to verify documentation.
- [ ] Verify Markdown links, keep proposals labelled, and run `pre-commit run --all-files` for changes here.

## Sources

Current implementation, pinned to common commit `cc6734876a6549340d2979d95771752d718f6f0f`:

- [Reporting client](https://github.com/projectbluefin/common/blob/cc6734876a6549340d2979d95771752d718f6f0f/system_files/bluefin/usr/libexec/bonedigger-report): `main`, `collect_baseline`, `profile_*`, `scrub_*`, `submit_draft`, `confirm_report`, `persist_local_copy`.
- [ujust wrapper](https://github.com/projectbluefin/common/blob/cc6734876a6549340d2979d95771752d718f6f0f/system_files/bluefin/usr/share/ublue-os/just/60-bonedigger.just).
- [Canonical routing helper](https://github.com/projectbluefin/common/blob/cc6734876a6549340d2979d95771752d718f6f0f/system_files/shared/usr/libexec/ublue-image-repo); the archived-destination fix is tracked in [common#1499](https://github.com/projectbluefin/common/issues/1499).
- GitHub CLI manual, verified through Context7 `/websites/cli_github_manual`: [issue creation](https://cli.github.com/manual/gh_issue_create), [issue comments](https://cli.github.com/manual/gh_issue_comment), [gist creation](https://cli.github.com/manual/gh_gist_create). These describe CLI semantics, not additional Bonedigger capabilities.
