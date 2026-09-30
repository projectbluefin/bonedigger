---
name: bonedigger-screenshots
description: Use when adding screenshot capture, on-device screenshot analysis, or screenshot privacy rules to the `ujust report` diagnostics flow.
---
# bonedigger — screenshot capture & analysis

## When to Use

- Extending `ujust report` to capture or analyze a screenshot / screen photo
- Adding privacy rules for image data in the report pipeline
- Deciding what screenshot-related fields go in the canonical issue templates
- Answering the question behind issue #2 ("Analyze screenshots?")

## When NOT to Use

- Editing `ujust report`, OTel config, or other image content — that belongs in `projectbluefin/common`
- Editing downstream template copies directly in `common`, `dakota`, `bluefin`, `bluefin-lts`, or `knuckle`
- Building a server-side image-analysis service — bonedigger has no backend; everything runs on the user's machine

## The Problem (issue #2)

Some bugs cannot be captured with a normal screenshot:

- The bug is in the login / lock screen, KMS, or a TTY — Wayland and most screenshot tools are unavailable.
- The system crashed or hung before the user could capture anything.
- The display is external, high-DPI, or multi-monitor, and screenshot tools mis-capture.

In those cases the user photographs the monitor with a phone. The result is angled, glare-ridden, and full of context a maintainer needs (exact error text, dialog contents, visual glitches) but cannot reliably read. Maintainers get a photo and still have to ask follow-up questions.

The opportunity: `ujust report` can turn that poor input into structured, useful signal — **on the user's machine, before anything leaves the box**.

## Design Goals

1. **On-device, always.** A screenshot is the one data type that inherently contains PII — open documents, browser tabs, chat windows, personal files. Nothing about the screenshot may leave the machine raw. Any analysis, OCR, and PII scrubbing happen locally.
2. **Supplement, don't replace.** The gist URL from the normal flow is still primary. The screenshot path is an optional enhancement for users who cannot produce a clean capture.
3. **Extract text, not pixels.** The highest-value, lowest-privacy-risk output is extracted and scrubbed *text* (error messages, dialog labels, version strings from the image), not the image itself.
4. **Tell the user what happened.** If the provided image is a photo-of-screen, warn the user and offer to re-capture; never silently ingest a blurry phone photo as if it were clean.

## What `ujust report` Collects

Add an optional step, gated on user consent (`gum confirm`), after the normal diagnostics capture:

| Field | Source | Notes |
|-------|--------|-------|
| Clean screenshot (if capturable) | xdg-desktop-portal `org.freedesktop.portal.Screenshot` | One mechanism on both desktops: GNOME (Bluefin) and KDE (Aurora) each back the portal with their own shell capture. The call is **asynchronous** — see below. Skip silently if the portal call fails, no portal is running, or the user dismisses the portal dialog |
| User-provided image (photo-of-screen) | `gum file` picker or drag-drop | Any image file the user supplies |
| Screenshot type | On-device analysis | `clean-screenshot` / `photo-of-screen` / `unusable` / `unknown` (detection unavailable — see below) |
| Extracted text | On-device OCR | See below; folded into `summary.md`, never uploaded raw |
| Problem classification | On-device heuristic | `error-dialog` / `blank-screen` / `visual-glitch` / `color-issue` / `unknown` |

### Portal capture is asynchronous

`org.freedesktop.portal.Screenshot.Screenshot()` does **not** return the image. It returns a `Request` object path, then shows an interactive portal dialog; the file URI arrives later in the `org.freedesktop.portal.Request::Response` signal on that path. A bare `gdbus call` therefore yields an object path and no image — the recipe must wait for the signal.

Required shape:

1. Compute the expected `Request` path from the sender's unique bus name plus a caller-chosen `handle_token`, and start listening **before** calling, e.g. `gdbus monitor --session --dest org.freedesktop.portal.Desktop` filtered to that path (or a `dbus-monitor` / `busctl monitor` equivalent), so the response cannot be missed in the race window.
2. Call `Screenshot()` with `handle_token` and `interactive` options.
3. Wait for `Response(u response, a{sv} results)`, with a timeout (the dialog is user-driven — 60s is reasonable) and a cancel path.
4. `response == 0` ⇒ success, take `results['uri']` (a `file://` URI) and strip the scheme. `response == 1` ⇒ user cancelled, `2` ⇒ other error — in both cases skip the screenshot step silently and continue the report.

If implementing the monitor/parse dance in shell proves fragile, a short `python3` + `dbus`/`Gio` helper is acceptable — `python3` is already a dependency of the recipe (it performs the OTel config-path substitution). Do not busy-poll a guessed output path.

The portal writes its image somewhere of its own choosing, **outside** `report-XXXXXX/`. Copy it into `report-XXXXXX/` and delete the portal-produced file immediately — see "Privacy Model".

### Photo-of-screen detection

Cheap, local heuristics before committing to OCR. These are pixel operations and need an image library — the recipe may use `python3` with `python3-pillow` and `python3-numpy`. `python3` is already required by `ujust report`; `python3-pillow` and `python3-numpy` are **new** optional dependencies this spec introduces (both are Fedora RPMs) and must be added to the recipe's dependency list as optional. No OpenCV, no network service. **If those modules are absent, skip detection entirely**, classify the image as `unknown`, tell the user, and continue — detection is an enhancement, never a hard requirement.

- **Sharpness** — Laplacian variance of a cropped region; low variance ⇒ likely out-of-focus phone photo. Thresholds are TBD and must be tuned against real submissions before the heuristic is trusted.
- **Aspect / geometry** — Non-standard aspect ratio ⇒ likely a photo. Full perspective-distortion estimation is out of scope for a Pillow/numpy implementation; aspect ratio and edge-angle sanity checks only.
- **Phone UI overlays** — Status-bar clock / battery / notch regions ⇒ photo. Best-effort, low confidence.

If the image is classified `unusable`, tell the user and stop — do not upload garbage. If `photo-of-screen`, warn the user and prefer extracted text over the image.

### On-device OCR and extraction

- Use the `tesseract` RPM as the on-device OCR engine — it is the only *OCR* engine this spec sanctions (the Pillow/numpy dependency above is for pixel heuristics, not OCR). There is no Flatpak OCR engine to fall back to: do not substitute a Flathub app, do not add a network OCR API, and do not rely on a generic "app finder" as the OCR engine. If `tesseract` is absent, skip the OCR step and say so.
- Extract text, then run it through the **same** `scrub_*` pipeline used for journal logs (`scrub_kernel_log()` + general scrubbing): IPs, MACs, emails, home paths, UUIDs, serials. OCR output is text and is subject to the same PII rules.
- Attach extracted text to `summary.md` under a "Screenshot context" section. The gist is text-only, so only scrubbed extracted text is attached here — not the image (see "No raw image upload").

### Problem classification

Lightweight, heuristic, and clearly labeled as *not diagnostic*:

- Error-dialog keywords (`error`, `failed`, `cannot`, `unable`, `cannot open`, `no response`, window title `×` buttons) ⇒ `error-dialog`.
- Near-uniform dark/gray region with no text ⇒ `blank-screen`.
- Detecting repeated/tearing patterns is unreliable on a phone photo — classify conservatively and flag low confidence.

Classification is advisory only; it never suppresses or overrides the user's own "What happened?" description.

## Privacy Model

Screenshots break the normal PII-scrubbing contract because the PII is *in the pixels*, not in structured fields. The rules:

| Rule | Requirement |
|------|-------------|
| No raw image upload | A screenshot is never uploaded to a gist as-is. This is a hard gate, not a default. |
| On-device analysis only | OCR, classification, and geometry checks run locally. No image is ever sent to an external service. |
| Scrub extracted text | OCR text passes through the existing `scrub_*` functions before it lands in `summary.md` or is attached. `scrub_*` is regex-only and cannot catch window titles, filenames, or chat/terminal text — see "Integration With the Report Flow" for the mandatory user-review ordering. |
| User consent + disclosure | The user is told the image will be analyzed locally and what will be attached. Consent is explicit (`gum confirm`) and reversible. There is no existing remembered-consent mechanism — today's overrides (`IMAGE_INFO_FILE`, `BONEDIGGER_ISSUE_URL`, `BONEDIGGER_BRAND`) are path/URL/brand knobs only. This spec introduces one new variable, `BONEDIGGER_SCREENSHOT` (`ask` (default) / `never` / `always`), to skip or pre-answer the prompt. |
| Ephemeral intermediates | OCR working files are written under `$XDG_RUNTIME_DIR/ujust-report/report-XXXXXX/` and removed on the EXIT trap, exactly like `summary.md` and `journal.txt`. |
| Unconditional image deletion | **Every image intermediate is deleted on every exit path**, including the cancel path. This is stronger than the EXIT-trap rule above and is not optional. Covered: the portal-produced file at `results['uri']` (which lives *outside* `report-XXXXXX/` and is therefore untouched by the trap), the user-supplied image if it was copied into the report dir, and any cropped/downscaled derivatives written by the heuristics or OCR step. Requirements: (a) delete the portal file as soon as it is copied into `report-XXXXXX/`, not at exit; (b) register a dedicated cleanup for image files that runs even when the recipe takes the `trap - EXIT; exit 0` cancel-preserve path (`bonedigger-ujust.md`, "Report output structure") — that path preserves `summary.md`/`journal.txt` for the user, but must never preserve pixels; (c) if the user declines consent or aborts mid-flow, delete the images before returning. Withdrawn consent must leave no image on disk. |

This keeps the screenshot path consistent with the rest of the repo: scrubbing happens on-device, before upload, and the user owns their data.

## Integration With the Report Flow

```
diagnostics capture  →  summary.md + journal.txt rendered
        │
        ▼
gum confirm "Attach a screenshot / photo?"
        │  (no)  →  skip
        ▼  (yes)
classify image (clean vs photo-of-screen vs unusable)
        │  unusable → warn, offer re-capture, then continue
        ▼
OCR on-device → scrub extracted text → fold into summary.md
        │
        ▼
glow + gum pager local review of summary.md   ← user sees OCR text here
        │
        ▼
gum confirm upload
        │
        ▼
upload (gh gist) summary.md + journal.txt → open issue
```

**Ordering is a privacy requirement, not a preference.** The existing flow (`bonedigger-ujust.md`, "Upload flow" steps 1–2) shows the rendered report in `glow` + `gum pager` *first*, then asks `gum confirm` to upload. The whole screenshot step — capture, classification, OCR, scrub — must run **before** that pager review, so the extracted text is in the `summary.md` the user actually reads.

`scrub_*` is regex-only (IPs, MACs, emails, home paths, UUIDs, serials). OCR pulls in window titles, filenames, and chat/terminal text that no regex catches, so the user's own eyes on the pager are the real mitigation. If an implementation cannot fold the screenshot step in before the first render, it must re-render and re-show the pager after OCR and before `gum confirm`. Uploading OCR text the user has not seen paged is a bug.

## Template Changes

`templates/bug-report.yml` gains an **optional** screenshot field so users who file manually (not via `ujust report`) can attach a capture:

```yaml
- type: textarea
  id: screenshot
  attributes:
    label: "Screenshot (optional)"
    description: "Optional — paste or drag a screenshot. If you had to photograph your screen, `ujust report` can extract and scrub the text for you."
  validations:
    required: false
```

Keep it optional and non-blocking. The gist URL remains the required field.

## Where the Code Lives

The implementation is **image content**, so it ships in `projectbluefin/common`, not here:

| Artifact | Path in common |
|----------|----------------|
| Screenshot capture + OCR + scrub logic | `system_files/bluefin/usr/share/ublue-os/just/60-bonedigger.just` |
| Consent / override env var | same recipe — add `BONEDIGGER_SCREENSHOT` to the override table alongside `IMAGE_INFO_FILE` / `BONEDIGGER_BRAND` |
| Screenshot template field | `templates/bug-report.yml` (mastered here, synced downstream) |

This doc is the spec. The recipe and any new env vars live in `common`; Dakota and bluefin inherit the recipe automatically — do not add copies to those repos. **Sync workflows are the wrong answer** — edit the recipe directly in `common`.

## Verification

- [ ] No raw screenshot is ever uploaded; on-device analysis is a hard gate.
- [ ] OCR output passes through the existing `scrub_*` functions.
- [ ] The screenshot/OCR step completes **before** the `glow` + `gum pager` review, so no OCR text reaches the gist unreviewed.
- [ ] The portal capture waits on the `Request::Response` signal and handles cancel/timeout.
- [ ] Missing `tesseract` or `python3-pillow`/`python3-numpy` degrades gracefully instead of failing the report.
- [ ] Extracted text and OCR intermediates are removed on the EXIT trap.
- [ ] All image intermediates — including the portal-produced file outside `report-XXXXXX/` — are deleted on every exit path, including the `trap - EXIT; exit 0` cancel-preserve path and declined consent.
- [ ] Consent is explicit and reversible; the user is told what is attached.
- [ ] `pre-commit run --all-files` passes.
- [ ] `actionlint .github/workflows/*.yml` passes (only if a workflow changes).

## Sources

- Issue #2 — "Analyze screenshots?" (the brainstorm this spec answers)
- `bonedigger-ujust.md` — the existing `ujust report` collection, scrubbing, and upload flow this extends
- `bonedigger-overview.md` — the on-device, no-backend privacy model
