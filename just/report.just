# vim: set ft=make :

# Collect a privacy-respecting diagnostic report and offer to attach it to a new bug report.
[group('System')]
report:
    #!/usr/bin/bash
    set -euo pipefail

    IMAGE_INFO_FILE="${IMAGE_INFO_FILE:-/usr/share/ublue-os/image-info.json}"
    ISSUE_URL_BASE="${BONEDIGGER_ISSUE_URL:-https://github.com/projectbluefin/common/issues/new?template=bug-report.yml}"
    BONEDIGGER_BRAND="${BONEDIGGER_BRAND:-🫐 Bluefin Bug Report}"
    OTEL_CONFIG_SOURCE="/usr/share/ublue-os/otel/ujust-report-config.yaml"
    REPORT_ROOT="${XDG_RUNTIME_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}}/ujust-report"
    mkdir -p "$REPORT_ROOT"
    REPORT_DIR="$(mktemp -d "${REPORT_ROOT}/report-XXXXXX")"
    OTEL_CONFIG=""
    HAS_OTEL=0

    cleanup() {
        rm -rf "$REPORT_DIR"
        [[ -n "$OTEL_CONFIG" ]] && rm -f "$OTEL_CONFIG"
    }
    trap cleanup EXIT

    echo ""
    gum style \
        --border rounded --border-foreground 99 \
        --padding "1 3" --margin "0 1" \
        --bold --foreground 212 \
        "$BONEDIGGER_BRAND"
    echo ""
    gum style --foreground 245 --margin "0 2" \
        "Collect system details, review them locally, then upload to your own GitHub gist."
    gum style --foreground 245 --margin "0 2" \
        "Nothing leaves your machine until you confirm it."
    echo ""

    gum style --foreground 214 --margin "0 2" \
        "→ Reading your booted image (you may be prompted for your password):"
    echo ""

    BOOTC_JSON="$(sudo bootc status --json 2>/dev/null || echo '{}')"
    BOOTC_STATUS="$(sudo bootc status 2>/dev/null || echo 'Unavailable')"

    IMAGE_NAME="$(jq -r '."image-name" // "unknown"' "$IMAGE_INFO_FILE" 2>/dev/null || echo unknown)"
    IMAGE_REF="$(jq -r '."image-ref" // "unknown"' "$IMAGE_INFO_FILE" 2>/dev/null || echo unknown)"
    IMAGE_TAG="$(jq -r '."image-tag" // "unknown"' "$IMAGE_INFO_FILE" 2>/dev/null || echo unknown)"
    IMAGE_FLAVOR="$(jq -r '."image-flavor" // "unknown"' "$IMAGE_INFO_FILE" 2>/dev/null || echo unknown)"
    BOOTED_IMAGE="$(printf '%s' "$BOOTC_JSON" | jq -r '.status.booted.image.image.image // empty' 2>/dev/null || true)"
    BOOTED_DIGEST="$(printf '%s' "$BOOTC_JSON" | jq -r '.status.booted.imageDigest // empty' 2>/dev/null || true)"
    STAGED_IMAGE="$(printf '%s' "$BOOTC_JSON" | jq -r '.status.staged.image.image.image // empty' 2>/dev/null || true)"
    GNOME_VERSION="$(gnome-shell --version 2>/dev/null || echo unknown)"
    GNOME_EXTENSIONS="$(gnome-extensions list --enabled 2>/dev/null || true)"
    FLATPAK_LIST="$(flatpak list --columns=application,version 2>/dev/null || echo unavailable)"
    LOAD_AVG="$(awk '{print $1", "$2", "$3}' /proc/loadavg)"
    MEM_INFO="$(free -h --si | awk '/^Mem:/{print $3" used / "$2" total"}')"
    FAILED_UNITS="$(systemctl list-units --state=failed --no-legend --plain 2>/dev/null | awk '{print $1}' | head -20 || true)"
    GROUPS_OUT="$(groups 2>/dev/null || echo unavailable)"
    KERNEL_VER="$(uname -r)"
    ARCH="$(uname -m)"

    FLATPAK_LIST="$(printf '%s' "$FLATPAK_LIST" | sed -E 's|/home/[^/[:space:]]+/|/home/<redacted>/|g')"
    GNOME_EXTENSIONS="$(printf '%s' "$GNOME_EXTENSIONS" | sed -E 's|/home/[^/[:space:]]+/|/home/<redacted>/|g')"
    GROUPS_OUT="$(printf '%s' "$GROUPS_OUT" | sed -E 's|/home/[^/[:space:]]+/|/home/<redacted>/|g')"

    if [[ -z "$BOOTED_IMAGE" ]]; then
        BOOTED_IMAGE="${IMAGE_REF}:${IMAGE_TAG}"
    fi
    if [[ -z "$BOOTED_DIGEST" ]]; then
        BOOTED_DIGEST="unknown"
    fi
    if [[ -z "$STAGED_IMAGE" ]]; then
        STAGED_IMAGE="none"
    fi

    if [[ -f "$OTEL_CONFIG_SOURCE" ]]; then
        echo ""
        gum style --foreground 245 --margin "0 2" \
            "Deep metrics capture 35 seconds of hardware telemetry and journal logs."
        gum style --foreground 245 --margin "0 2" \
            "Useful when a bug is hard to reproduce. Skip it for quick reports."
        echo ""

        if gum confirm " Include deep hardware metrics? (~35 seconds)" --default=false; then
            OTELCOL_BINARY=""
            OTEL_CONFIG="$(mktemp "${REPORT_ROOT}/otel-config-XXXXXX.yaml")"
            sed "s|/output/|${REPORT_DIR}/|g" "$OTEL_CONFIG_SOURCE" > "$OTEL_CONFIG"

            for candidate in \
                "$HOME/.local/bin/otelcol-contrib" \
                "/usr/local/bin/otelcol-contrib" \
                "$(command -v otelcol-contrib 2>/dev/null || true)"; do
                if [[ -n "$candidate" && -x "$candidate" ]]; then
                    OTELCOL_BINARY="$candidate"
                    break
                fi
            done

            if [[ -n "$OTELCOL_BINARY" ]]; then
                gum spin --spinner globe \
                    --title " Collecting deep hardware metrics..." \
                    -- timeout 35 "$OTELCOL_BINARY" --config "$OTEL_CONFIG" 2>/dev/null || true
            elif command -v podman &>/dev/null; then
                gum spin --spinner globe \
                    --title " Collecting deep hardware metrics..." \
                    -- timeout 45 podman run --rm --privileged \
                        --network=host \
                        -v /proc:/proc:ro \
                        -v /sys:/sys:ro \
                        -v /var/log/journal:/var/log/journal:ro \
                        -v /run/log/journal:/run/log/journal:ro \
                        -v "${OTEL_CONFIG_SOURCE}:/etc/otelcol/config.yaml:ro" \
                        -v "${REPORT_DIR}:/output" \
                        docker.io/otel/opentelemetry-collector-contrib@sha256:a2a52e43c1a80aa94120ad78c2db68780eb90e6d11c8db5b3ce2f6a0cc6b5029 \
                        2>/dev/null || true
            else
                gum style --foreground 214 --margin "0 2" \
                    "⚠ otelcol-contrib not found — deep metrics skipped."
            fi

            if [[ -f "$REPORT_DIR/report.otlp.json" ]]; then
                HAS_OTEL=1
                gum style --foreground 82 --margin "0 2" "✓ Hardware metrics captured."
            fi
        fi
    fi

    TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    if [[ -r /etc/machine-id ]]; then
        HOST_ID="$(printf 'ujust-report:%s' "$(cat /etc/machine-id)" | sha256sum | cut -c1-8)"
    else
        HOST_ID="unknown"
    fi

    {
        printf '## %s\n\n' "$BONEDIGGER_BRAND"
        printf 'Generated: %s  \n' "$TIMESTAMP"
        printf 'Device ID: `%s` (anonymised — derived from machine-id, not reversible)  \n\n' "$HOST_ID"
        printf '### System\n\n'
        printf '| Field | Value |\n|-------|-------|\n'
        printf '| Image name | `%s` |\n' "$IMAGE_NAME"
        printf '| Image tag | `%s` |\n' "$IMAGE_TAG"
        printf '| Image flavor | `%s` |\n' "$IMAGE_FLAVOR"
        printf '| Kernel | `%s` |\n' "$KERNEL_VER"
        printf '| Architecture | `%s` |\n' "$ARCH"
        printf '| Load (1m / 5m / 15m) | %s |\n' "$LOAD_AVG"
        printf '| Memory | %s |\n' "$MEM_INFO"
        printf '| GNOME | %s |\n' "$GNOME_VERSION"
        printf '\n### Booted Image\n\n'
        printf '| Field | Value |\n|-------|-------|\n'
        printf '| Image | `%s` |\n' "$BOOTED_IMAGE"
        printf '| Digest | `%s` |\n' "$BOOTED_DIGEST"
        printf '| Staged | `%s` |\n' "$STAGED_IMAGE"
        printf '\n### Output of `groups`\n\n```\n%s\n```\n' "$GROUPS_OUT"
        printf '\n### Failed Systemd Units\n\n'
        if [[ -n "$FAILED_UNITS" ]]; then
            printf '%s\n' "$FAILED_UNITS" | sed 's/^/- /'
        else
            printf '_None_ ✓\n'
        fi
        if [[ -n "$GNOME_EXTENSIONS" ]]; then
            printf '\n### Active GNOME Extensions\n\n'
            printf '%s\n' "$GNOME_EXTENSIONS" | sed 's/^/- /'
        fi
        printf '\n### Installed Flatpaks\n\n```\n%s\n```\n' "$FLATPAK_LIST"
        printf '\n### Output of `bootc status`\n\n```\n%s\n```\n' "$BOOTC_STATUS"
        if [[ $HAS_OTEL -eq 1 ]]; then
            printf '\n### Deep Hardware Metrics\n\n'
            printf 'See `report.otlp.json` in this gist — structured metrics and journal logs (35-second sample).\n'
        fi
    } > "$REPORT_DIR/summary.md"

    echo ""
    gum style --foreground 99 --bold --margin "0 2" \
        "Review everything before it leaves your machine:"
    echo ""

    if [[ -t 0 && -t 1 ]]; then
        if command -v glow &>/dev/null; then
            glow "$REPORT_DIR/summary.md" | gum pager
        else
            gum pager < "$REPORT_DIR/summary.md"
        fi
    else
        command -v glow &>/dev/null && glow "$REPORT_DIR/summary.md" || cat "$REPORT_DIR/summary.md"
    fi

    echo ""
    gum style --foreground 245 --margin "0 2" "What will be uploaded to your GitHub gist:"
    SIZE_SUMMARY="$(ls -lh "$REPORT_DIR/summary.md" 2>/dev/null | awk '{print $5}')"
    gum style --margin "0 4" "  summary.md  (${SIZE_SUMMARY})"
    if [[ -f "$REPORT_DIR/report.otlp.json" ]]; then
        SIZE_OTEL="$(ls -lh "$REPORT_DIR/report.otlp.json" 2>/dev/null | awk '{print $5}')"
        gum style --margin "0 4" "  report.otlp.json  (${SIZE_OTEL})"
    fi
    echo ""

    if ! gum confirm " Upload this report to your GitHub gist?"; then
        echo ""
        gum style --foreground 245 --margin "0 2" "Cancelled. Files kept at: $REPORT_DIR/"
        trap - EXIT
        exit 0
    fi

    if ! gh auth status --active &>/dev/null; then
        echo ""
        gum style --foreground 214 --bold --margin "0 2" \
            "gh is not signed in — copy the report into a bug report instead:"
        if command -v wl-copy &>/dev/null; then
            wl-copy < "$REPORT_DIR/summary.md"
            gum style --foreground 82 --margin "0 4" "✓ Copied to clipboard. Paste it into your issue."
        elif command -v xclip &>/dev/null; then
            xclip -selection clipboard < "$REPORT_DIR/summary.md"
            gum style --foreground 82 --margin "0 4" "✓ Copied to clipboard. Paste it into your issue."
        else
            gum style --foreground 245 --margin "0 4" "Clipboard support not available."
        fi
        gum style --foreground 245 --margin "0 4" "Open: $ISSUE_URL_BASE"
        gum style --foreground 245 --margin "0 4" "Report saved at: $REPORT_DIR/summary.md"
        if [[ -f "$REPORT_DIR/report.otlp.json" ]]; then
            gum style --foreground 245 --margin "0 4" "Telemetry saved at: $REPORT_DIR/report.otlp.json"
        fi
        trap - EXIT
        exit 0
    fi

    GIST_FILES=("$REPORT_DIR/summary.md")
    if [[ -f "$REPORT_DIR/report.otlp.json" ]]; then
        GIST_FILES+=("$REPORT_DIR/report.otlp.json")
    fi

    if ! GIST_URL="$(gh gist create --public --desc "Diagnostic report $(date -I)" "${GIST_FILES[@]}")"; then
        echo ""
        gum style --foreground 196 --margin "0 2" "Upload failed. Files kept at: $REPORT_DIR/"
        trap - EXIT
        exit 1
    fi

    echo ""
    gum style \
        --border rounded --border-foreground 82 \
        --padding "1 3" --margin "0 1" \
        --bold --foreground 82 \
        "✓ Report uploaded"
    gum style --margin "0 2" "$GIST_URL"
    echo ""

    ENCODED_URL="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$GIST_URL" 2>/dev/null || printf '%s' "$GIST_URL" | sed 's|:|%3A|g; s|/|%2F|g; s|@|%40|g')"
    ISSUE_JOINER='&'
    if [[ "$ISSUE_URL_BASE" != *\?* ]]; then
        ISSUE_JOINER='?'
    fi
    ISSUE_URL="${ISSUE_URL_BASE}${ISSUE_JOINER}report-link=${ENCODED_URL}"
    if gum confirm " Open a new issue in your browser with this report attached?"; then
        xdg-open "$ISSUE_URL" 2>/dev/null || gum style --foreground 245 --margin "0 2" "Visit: $ISSUE_URL"
    else
        gum style --foreground 245 --margin "0 2" "Open later: $ISSUE_URL"
    fi
