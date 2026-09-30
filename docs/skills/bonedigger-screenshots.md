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
| Clean screenshot (if capturable) | `gnome-screenshot` (Bluefin GNOME Wayland, via the xdg-desktop-portal Screenshot API) / `spectacle` (Aurora) | Detect which exists; skip silently if none installed |
| User-provided image (photo-of-screen) | `gum file` picker or drag-drop | Any image file the user supplies |
| Screenshot type | On-device analysis | `clean-screenshot` vs `photo-of-screen` vs `unusable` |
| Extracted text | On-device OCR | See below; folded into `summary.md`, never uploaded raw |
| Problem classification | On-device heuristic | `error-dialog` / `blank-screen` / `visual-glitch` / `color-issue` / `unknown` |

### Photo-of-screen detection

Cheap, local heuristics before committing to OCR:

- **Sharpness** — Laplacian variance of a cropped region; low variance ⇒ likely out-of-focus phone photo.
- **Aspect / geometry** — Non-standard aspect ratio or strong perspective distortion ⇒ likely a photo.
- **Phone UI overlays** — Status-bar clock / battery / notch regions ⇒ photo.

If the image is classified `unusable`, tell the user and stop — do not upload garbage. If `photo-of-screen`, warn the user and prefer extracted text over the image.

### On-device OCR and extraction

- Use an on-device OCR engine already present or installable via Flatpak/rpm — `tesseract` (RPM) or the `com.github.tesseract_ocr.Tesseract` Flatpak. Do not add a network OCR API, and do not rely on a generic "app finder" as the OCR engine.
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
| Scrub extracted text | OCR text passes through the existing `scrub_*` functions before it lands in `summary.md` or is attached. |
| User consent + disclosure | The user is told the image will be analyzed locally and what will be attached. Consent is explicit (`gum confirm`), reversible, and remembered via the same env-var/override pattern as other optional steps. |
| Ephemeral intermediates | OCR working files are written under `$XDG_RUNTIME_DIR/ujust-report/report-XXXXXX/` and removed on the EXIT trap, exactly like `summary.md` and `journal.txt`. |

This keeps the screenshot path consistent with the rest of the repo: scrubbing happens on-device, before upload, and the user owns their data.

## Integration With the Report Flow

```
diagnostics capture  →  summary.md + journal.txt rendered
        │
        ▼
gum confirm "Attach a screenshot / photo?"
        │  (no)  →  skip, continue to upload
        ▼  (yes)
classify image (clean vs photo-of-screen vs unusable)
        │  unusable → warn, offer re-capture, then continue
        ▼
OCR on-device → scrub extracted text → fold into summary.md
        │
        ▼
upload (gh gist) summary.md + journal.txt [+ extracted text] → open issue
```

The screenshot step sits between rendering and upload so the extracted text is part of the reviewed `summary.md`.

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
| Consent / override env vars | same recipe, alongside `IMAGE_INFO_FILE` / `BONEDIGGER_BRAND` |
| Screenshot template field | `templates/bug-report.yml` (mastered here, synced downstream) |

This doc is the spec. The recipe and any new env vars live in `common`; Dakota and bluefin inherit the recipe automatically — do not add copies to those repos. **Sync workflows are the wrong answer** — edit the recipe directly in `common`.

## Verification

- [ ] No raw screenshot is ever uploaded; on-device analysis is a hard gate.
- [ ] OCR output passes through the existing `scrub_*` functions.
- [ ] Extracted text and OCR intermediates are removed on the EXIT trap.
- [ ] Consent is explicit and reversible; the user is told what is attached.
- [ ] `pre-commit run --all-files` passes.
- [ ] `actionlint .github/workflows/*.yml` passes (only if a workflow changes).

## Sources

- Issue #2 — "Analyze screenshots?" (the brainstorm this spec answers)
- `bonedigger-ujust.md` — the existing `ujust report` collection, scrubbing, and upload flow this extends
- `bonedigger-overview.md` — the on-device, no-backend privacy model
