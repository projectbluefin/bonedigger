# bonedigger — QR code for reports

Load when adding console QR output to `ujust report`: a way for a user on
their phone to scan a code printed in the terminal and open the report so they
can voice-dictate into it.

## Status

This is a **proposal**, not shipped behavior. The current
[`bonedigger-report` script](https://github.com/projectbluefin/common/blob/528189efc699d5ac43f427fe672f1f9550f8e96d/system_files/bluefin/usr/libexec/bonedigger-report)
does not render QR codes or read `BONEDIGGER_ISSUE_URL`. The rendering,
fallback, and self-check requirements below apply to a future implementation
in `projectbluefin/common`.

## Why

The report flow ends with the user staring at a terminal. This feature lets the
same user pick up their phone, scan a QR code, and open the issue form (or their
uploaded gist) in a mobile browser — where voice dictation is far easier than
typing a bug report on a phone keyboard.

Issue: projectbluefin/bonedigger#10 "QR codes for stuff".

## What the QR encodes

Two QR opportunities in the existing upload flow — neither carries PII:

1. **Pre-upload — issue form.** Encodes the canonical issue-report URL for the
   image's tracker, using the repository selected by `route_issue_repo()`.
   Opening it on a phone presents the bug-report form the user can voice-dictate into. Optionally append `?body=` with a short prompt so
   the first field is pre-seeded; keep the seeded body free of PII.
2. **Post-upload — gist.** After `gh gist create --public`, print a second QR
   encoding the public gist URL so the user can open their uploaded report on any
   device.

Because both values are URLs, the QR payload contains no diagnostic data and no
PII — consistent with the on-device scrubbing model.

## Where it fits in the flow

Proposed insertion points in the current script (see `bonedigger-ujust.md`):

- After `preview_draft`, before submission confirmation: show the issue-form QR.
- After `publish_smart_logs` successfully publishes selected profiles: show the
  gist QR. No gist QR is needed when no profiles were selected.

The implementation belongs in
`system_files/bluefin/usr/libexec/bonedigger-report` in `projectbluefin/common`;
`60-bonedigger.just` is the recipe entry point. Both are image content shipped
by `common`. This document only specifies the proposed feature.

## Rendering

- **Primary: `qrencode` CLI.** `qrencode -t ANSIUTF8 -s <size> -m 4 "<url>"`
  prints a scan-friendly UTF-8 block. The `qrencode` package ships on Fedora /
  Bluefin. Use `-m 4` for a wide quiet zone and `-s` (module size) large enough to
  scan from arm's length — terminals are viewed close, phones scan from a
  distance.
- **Fallback: bundled pure-bash generator.** If `qrencode` is absent, fall back
  to a dependency-free bash QR generator so the feature works on minimal installs.
  Do not require a new system dependency for a core reporting step.

Wrap rendering in a helper (`print_qrcode <url>`) so the terminal backend is a
single choke point — both flow points call it, and the primary/fallback choice
lives in one place.

## Guard / self-check

The QR helper must round-trip: the bytes it prints must decode back to the input
URL. Verify with a tiny self-check — pipe the helper output through a QR decoder
(e.g. `zbarimg --raw -` if present, or the fallback's own decoder) and assert the
decoded text equals the input URL. Add this as a `--selftest` on the helper or a
one-line check in the recipe's test harness.

## Dependencies

- `qrencode` (primary renderer; available on Bluefin)
- `zbarimg` (optional; only for the round-trip self-check)

No new env vars. Reuse the script's routed repository and the URL returned by
`gh gist create`; `BONEDIGGER_ISSUE_URL` is not a supported override.
