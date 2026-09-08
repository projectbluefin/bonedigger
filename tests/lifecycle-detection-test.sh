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

if [ "$1" = "issue" ] && [ "$2" = "edit" ]; then
  printf '%s\n' "$*" >>"$GH_CALLS"
  exit 0
fi

exit 1
EOF
chmod +x "$tmp_dir/bin/gh"

cat >"$tmp_dir/bin/awk" <<EOF
#!/usr/bin/env bash
exec env POSIXLY_CORRECT=1 "$system_awk" "\$@"
EOF
chmod +x "$tmp_dir/bin/awk"

detect_report() {
  : >"$tmp_dir/output"
  ISSUE_DATA=$1 \
    DONATION_WORKFLOW_MARKER='Workflow: Agent Donation' \
    GITHUB_OUTPUT="$tmp_dir/output" \
    GH_CALLS="$tmp_dir/gh-calls" \
    PATH="$tmp_dir/bin:$PATH" \
    bash "$tmp_dir/detect.sh"
  sed -n 's/^is_ujust_report=//p' "$tmp_dir/output"
}

awk '
  /- name: Sync priority labels from confirm count/ { in_step = 1 }
  in_step && /run: \|/ { in_script = 1; next }
  in_script && /^      - name:/ { exit }
  in_script { sub(/^          /, ""); print }
' "$workflow" >"$tmp_dir/sync-priority.sh"

sync_priority() {
  : >"$tmp_dir/gh-calls"
  ISSUE_DATA=$1 \
    COMMENT_BODY='ujust confirm 1527' \
    ISSUE_NUMBER=1527 \
    ISSUE_URL='https://github.com/projectbluefin/dakota/issues/1527' \
    GH_CALLS="$tmp_dir/gh-calls" \
    PATH="$tmp_dir/bin:$PATH" \
    bash "$tmp_dir/sync-priority.sh"
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

invalid_gist_report_form='{"body":"### ujust report gist URL\n\nhttps://gist.github.com/_/0123456789abcdef\n\n### What happened?\n\nThe screen went blank.","labels":[]}'
actual=$(detect_report "$invalid_gist_report_form")

if [ "$actual" != "false" ]; then
  printf 'expected a report form with an invalid Gist owner to be rejected, got %s\n' "$actual" >&2
  exit 1
fi

source_labeled_issue='{"body":"### What happened?\n\nThe screen went blank.","labels":[{"name":"source:ujust-report"}]}'
actual=$(detect_report "$source_labeled_issue")

if [ "$actual" != "true" ]; then
  printf 'expected a source-labeled report to be accepted, got %s\n' "$actual" >&2
  exit 1
fi

standard_issue='{"body":"### What happened?\n\nThe screen went blank.","labels":[],"comments":[{"body":"ujust confirm 1527"},{"body":"ujust confirm 1527"},{"body":"ujust confirm 1527"}]}'
sync_priority "$standard_issue"

if [ -s "$tmp_dir/gh-calls" ]; then
  printf 'expected a standard issue confirm to skip report priority automation\n' >&2
  exit 1
fi

source_labeled_confirm_issue='{"body":"### What happened?\n\nThe screen went blank.","labels":[{"name":"source:ujust-report"}],"comments":[{"body":"ujust confirm 1527"},{"body":"ujust confirm 1527"},{"body":"ujust confirm 1527"}]}'
sync_priority "$source_labeled_confirm_issue"

if ! grep -Fq -- '--add-label priority/p1' "$tmp_dir/gh-calls"; then
  printf 'expected a source-labeled report confirm to update priority\n' >&2
  exit 1
fi
