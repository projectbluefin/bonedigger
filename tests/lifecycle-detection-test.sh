#!/usr/bin/env bash
set -euo pipefail

workflow=".github/workflows/lifecycle.yml"
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

awk '
  /- name: Detect bonedigger flows/ { in_step = 1 }
  in_step && /run: \|/ { in_script = 1; next }
  in_script && /^      - name:/ { exit }
  in_script { sub(/^          /, ""); print }
' "$workflow" >"$tmp_dir/detect.sh"

mkdir "$tmp_dir/bin"
system_awk=$(command -v awk)
cat >"$tmp_dir/bin/gh" <<'EOF'
#!/usr/bin/env bash
if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
  printf '%s' "$ISSUE_DATA"
  exit 0
fi

exit 1
EOF
chmod +x "$tmp_dir/bin/gh"

cat >"$tmp_dir/bin/awk" <<EOF
#!/usr/bin/env bash
exec "$system_awk" --posix "\$@"
EOF
chmod +x "$tmp_dir/bin/awk"

detect_report() {
  : >"$tmp_dir/output"
  ISSUE_DATA=$1 \
    DONATION_WORKFLOW_MARKER='Workflow: Agent Donation' \
    GITHUB_OUTPUT="$tmp_dir/output" \
    PATH="$tmp_dir/bin:$PATH" \
    bash "$tmp_dir/detect.sh"
  sed -n 's/^is_ujust_report=//p' "$tmp_dir/output"
}

blank_report_form='{"body":"### ujust report gist URL\n\n\n### What happened?\n\nThe screen went blank.","labels":[]}'
actual=$(detect_report "$blank_report_form")

if [ "$actual" != "false" ]; then
  printf 'expected a blank report form to be rejected, got %s\n' "$actual" >&2
  exit 1
fi

gist_report_form='{"body":"### ujust report gist URL\n\nhttps://gist.github.com/projectbluefin/0123456789abcdef\n\n### What happened?\n\nThe screen went blank.","labels":[]}'
actual=$(detect_report "$gist_report_form")

if [ "$actual" != "true" ]; then
  printf 'expected a report form with a Gist URL to be accepted, got %s\n' "$actual" >&2
  exit 1
fi

source_labeled_issue='{"body":"### What happened?\n\nThe screen went blank.","labels":[{"name":"source:ujust-report"}]}'
actual=$(detect_report "$source_labeled_issue")

if [ "$actual" != "true" ]; then
  printf 'expected a source-labeled report to be accepted, got %s\n' "$actual" >&2
  exit 1
fi
