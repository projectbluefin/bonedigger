# clanker-queue — lifecycle migration

Load when working on the queue-label consolidation in Project Bluefin:
`clanker-queue/*`, label sync, or the bonedigger reusable workflow that dual-writes
legacy labels during the migration.

## When to Use

- Updating `.github/workflows/lifecycle.yml`
- Updating `.github/workflows/sync-labels.yml`
- Adding or changing labels in `labels.json`
- Migrating issues from `status/queued`, `queue/agent-ready`, `copilot-ready`,
  `status/triage`, `priority/p0`, `priority/p1`, or `hive/*`

## When NOT to Use

- Editing issue templates or `ujust report` collection logic
- Changing image content in `projectbluefin/common`
- Writing one-off label fixes directly in the GitHub UI without updating the
  sync source

## Core Process

1. Update `labels.json` first. It is the canonical label source for the rollout.
2. Keep the workflow dual-writing the legacy labels and `clanker-queue/*`
   until the migration is complete.
3. Sync labels to every factory repo with the label sync workflow.
4. Migrate open issues with a single mapping file or script, one label family at
   a time.
5. Only delete the legacy labels after the new namespace is active everywhere.

## Red Flags

- Updating repo labels manually without changing `labels.json`
- Deleting legacy queue labels before the migration is complete
- Shipping a workflow change that only writes the new labels and drops the old
  ones during the soak
- Forgetting to update the docs in the same PR as the workflow change

## Verification

- [ ] `labels.json` includes the new `clanker-queue/*` labels
- [ ] `sync-labels.yml` still targets every factory repo
- [ ] The lifecycle workflow dual-writes the old labels and the new namespace
- [ ] `pre-commit run --all-files` passes
- [ ] `actionlint .github/workflows/*.yml` passes
