#!/usr/bin/env bats
# Regression tests for just/report.just — focussed on the cleanup trap and
# exit-code correctness after a successful gist upload.
#
# Run: bats tests/test_report_cleanup.bats

bats_require_minimum_version 1.5.0

REPORT_JUST="${BATS_TEST_DIRNAME}/../just/report.just"
WORKDIR=""

setup() {
    local safe_test_name="${BATS_TEST_NAME//[^[:alnum:]]/_}"
    WORKDIR="${BATS_TEST_DIRNAME}/.bats-work/${safe_test_name}-$$"
    mkdir -p "${WORKDIR}"
}

teardown() {
    rm -rf "${WORKDIR}"
}

# ---------------------------------------------------------------------------
# cleanup() helper — extract and unit-test the cleanup function in isolation
# ---------------------------------------------------------------------------

# Extract the cleanup() function body from report.just into a standalone script
# that: defines the function with the same body, calls it, and exits with its
# return value.  We can then run it under bats and inspect the exit status.
_make_cleanup_harness() {
    local harness="$1"
    local report_dir="$2"
    local otel_config="${3:-}"
    local otel_stderr="${4:-}"

    cat > "${harness}" <<HARNESS
#!/usr/bin/env bash
set -euo pipefail

REPORT_DIR="${report_dir}"
OTEL_CONFIG="${otel_config}"
OTEL_STDERR="${otel_stderr}"

cleanup() {
$(awk '/^    cleanup\(\) \{/{in_c=1; next} in_c && /^    \}/{in_c=0; next} in_c{sub(/^    /,""); print}' "${REPORT_JUST}")
}

cleanup
HARNESS
    chmod +x "${harness}"
}

@test "cleanup: exits 0 when OTEL_CONFIG and OTEL_STDERR are empty (no telemetry path)" {
    local report_dir="${WORKDIR}/report-dir"
    mkdir -p "${report_dir}"
    touch "${report_dir}/summary.md"

    local harness="${WORKDIR}/harness.sh"
    _make_cleanup_harness "${harness}" "${report_dir}" "" ""

    run bash "${harness}"

    [ "${status}" -eq 0 ]
    # cleanup should have removed the report dir
    [ ! -d "${report_dir}" ]
}

@test "cleanup: exits 0 when OTEL_CONFIG is set to a real file" {
    local report_dir="${WORKDIR}/report-dir"
    mkdir -p "${report_dir}"
    local otel_cfg="${WORKDIR}/otel.yaml"
    touch "${otel_cfg}"

    local harness="${WORKDIR}/harness.sh"
    _make_cleanup_harness "${harness}" "${report_dir}" "${otel_cfg}" ""

    run bash "${harness}"

    [ "${status}" -eq 0 ]
    [ ! -f "${otel_cfg}" ]
}

@test "cleanup: exits 0 when both OTEL files are set and exist" {
    local report_dir="${WORKDIR}/report-dir"
    mkdir -p "${report_dir}"
    local otel_cfg="${WORKDIR}/otel.yaml"
    local otel_log="${WORKDIR}/otel.log"
    touch "${otel_cfg}" "${otel_log}"

    local harness="${WORKDIR}/harness.sh"
    _make_cleanup_harness "${harness}" "${report_dir}" "${otel_cfg}" "${otel_log}"

    run bash "${harness}"

    [ "${status}" -eq 0 ]
    [ ! -f "${otel_cfg}" ]
    [ ! -f "${otel_log}" ]
}

@test "cleanup: exits 0 even when OTEL files have already been removed" {
    local report_dir="${WORKDIR}/report-dir"
    mkdir -p "${report_dir}"

    # otel paths that don't actually exist on disk
    local harness="${WORKDIR}/harness.sh"
    _make_cleanup_harness "${harness}" "${report_dir}" \
        "${WORKDIR}/gone.yaml" "${WORKDIR}/gone.log"

    run bash "${harness}"

    [ "${status}" -eq 0 ]
}
