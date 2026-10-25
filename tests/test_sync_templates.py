"""Run the real sync steps against local Git repositories, without GitHub writes."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]


def step(name):
    lines = (ROOT / ".github/workflows/sync-templates.yml").read_text().splitlines()
    start = lines.index(f"      - name: {name}")
    run = lines.index("        run: |", start)
    end = next(
        (i for i in range(run + 1, len(lines)) if lines[i].startswith("      - name:")),
        len(lines),
    )
    return textwrap.dedent("\n".join(lines[run + 1 : end]))


def prepare(workspace):
    """Build a downstream clone, a bonedigger checkout, and a recording `gh` stub."""
    downstream = workspace / "downstream"
    downstream.mkdir()

    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=downstream, text=True, stderr=subprocess.STDOUT
        ).strip()

    subprocess.run(["git", "init", "--bare", "-q", str(workspace / "origin")], check=True)
    git("init", "-q", "-b", "main")
    git("config", "user.name", "Sync test")
    git("config", "user.email", "sync-test@example.invalid")
    (downstream / "README.md").write_text("downstream\n")
    git("add", ".")
    git("commit", "--no-verify", "-qm", "chore: initial downstream state")
    git("remote", "add", "origin", str(workspace / "origin"))

    source = workspace / "bonedigger/templates"
    source.mkdir(parents=True)
    (source / "bug-report.yml").write_text("name: Canonical bug form\n")

    binaries = workspace / "bin"
    binaries.mkdir()
    log = workspace / "gh-invocations"
    # Record every argument vector so the PR contract can be asserted.
    (binaries / "gh").write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"log = {str(log)!r}\n"
        "with open(log, 'a') as handle:\n"
        "    handle.write(json.dumps(sys.argv[1:]) + '\\n')\n"
    )
    (binaries / "gh").chmod(0o755)
    return git, source, binaries, log


def invocations(log):
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines()]


def flag(argv, name):
    return argv[argv.index(name) + 1]


class TestSyncPullRequestContract(unittest.TestCase):
    """The `gh pr create` call is the sync's only externally visible product."""

    def run_sync(self, workspace, repo):
        git, source, binaries, log = prepare(workspace)
        environment = dict(
            os.environ,
            PATH=f"{binaries}:{os.environ['PATH']}",
            REPO=repo,
            SHA="abcdef0123456789" + "0" * 24,
        )
        for name in ("Copy templates", "Open PR if changed"):
            subprocess.run(
                ["bash", "-euo", "pipefail", "-c", step(name)],
                cwd=workspace,
                env=environment,
                check=True,
            )
        return git, invocations(log)

    def test_base_branch_is_chosen_per_downstream_repo(self):
        expected = {
            "projectbluefin/common": "main",
            "projectbluefin/dakota": "testing",
            "projectbluefin/knuckle": "main",
        }
        for repo, base in expected.items():
            with self.subTest(repo=repo), tempfile.TemporaryDirectory() as directory:
                git, calls = self.run_sync(Path(directory), repo)
                self.assertEqual(len(calls), 1, "one PR per downstream repo")
                argv = calls[0]
                self.assertEqual(flag(argv, "--repo"), repo)
                self.assertEqual(flag(argv, "--base"), base)
                self.assertEqual(flag(argv, "--head"), "bonedigger/sync-templates-abcdef01")
                self.assertEqual(
                    flag(argv, "--head"),
                    git("rev-parse", "--abbrev-ref", "HEAD"),
                    "the pushed branch must be the branch offered as --head",
                )
                self.assertEqual(
                    flag(argv, "--title"),
                    "chore(templates): sync issue templates from bonedigger",
                )
                self.assertNotIn(
                    "--label", argv, "downstream repos may lack any label; never request one"
                )
                self.assertIn("projectbluefin/bonedigger", flag(argv, "--body"))
                self.assertIn("abcdef01", flag(argv, "--body"))

    def test_no_pull_request_is_opened_when_templates_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            git, source, binaries, log = prepare(workspace)
            environment = dict(
                os.environ,
                PATH=f"{binaries}:{os.environ['PATH']}",
                REPO="projectbluefin/dakota",
                SHA="1" * 40,
            )
            for name in ("Copy templates", "Open PR if changed"):
                subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", step(name)],
                    cwd=workspace,
                    env=environment,
                    check=True,
                )
            self.assertEqual(len(invocations(log)), 1)
            environment["SHA"] = "2" * 40
            for name in ("Copy templates", "Open PR if changed"):
                subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", step(name)],
                    cwd=workspace,
                    env=environment,
                    check=True,
                )
            self.assertEqual(
                len(invocations(log)), 1, "an unchanged re-run must not open a second PR"
            )
            self.assertEqual(
                git("ls-remote", "origin", "refs/heads/bonedigger/sync-templates-22222222"),
                "",
                "an unchanged re-run must not push a branch",
            )


class TestSyncTemplates(unittest.TestCase):
    def test_sync_templates_lifecycle(self):
        self.run_sync_lifecycle()

    def test_pr_creation_failure_is_visible_and_not_retried(self):
        self.run_sync_lifecycle(pr_failure=True)

    def run_sync_lifecycle(self, pr_failure=False):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            downstream = workspace / "downstream"
            downstream.mkdir()

            def git(*args):
                return subprocess.check_output(
                    ["git", *args], cwd=downstream, text=True, stderr=subprocess.STDOUT
                ).strip()

            subprocess.run(["git", "init", "--bare", "-q", str(workspace / "origin")], check=True)
            git("init", "-q", "-b", "main")
            git("config", "user.name", "Sync test")
            git("config", "user.email", "sync-test@example.invalid")
            target = downstream / ".github/ISSUE_TEMPLATE"
            target.mkdir(parents=True)
            (target / "custom.yml").write_text("name: Downstream-only form\n")
            git("add", ".")
            git("commit", "--no-verify", "-qm", "chore: initial downstream state")
            git("remote", "add", "origin", str(workspace / "origin"))
            source = workspace / "bonedigger/templates"
            source.mkdir(parents=True)
            (source / "bug-report.yml").write_text("name: Canonical bug form\n")
            binaries = workspace / "bin"
            binaries.mkdir()
            # Only the external GitHub PR creation is replaced; commits and pushes are real.
            (binaries / "gh").write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "with open(os.environ['GH_LOG'], 'a') as log:\n"
                "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "if os.environ['GH_FAIL'] == '1':\n"
                "    print('PR creation failed', file=sys.stderr)\n"
                "    sys.exit(42)\n"
            )
            (binaries / "gh").chmod(0o755)
            environment = dict(os.environ, PATH=f"{binaries}:{os.environ['PATH']}", REPO="projectbluefin/common", GH_LOG=str(workspace / "gh.jsonl"), GH_FAIL=str(int(pr_failure)))
            for index, contents in enumerate(("name: Canonical bug form\n", "name: Updated bug form\n", "name: Updated bug form\n"), 1):
                (source / "bug-report.yml").write_text(contents)
                environment["SHA"] = f"{index:040x}"[::-1]
                subprocess.run(["bash", "-euo", "pipefail", "-c", step("Copy templates")], cwd=workspace, env=environment, check=True)
                before = git("rev-parse", "HEAD")
                result = subprocess.run(["bash", "-euo", "pipefail", "-c", step("Open PR if changed")], cwd=workspace, env=environment, capture_output=True, text=True)
                calls = [json.loads(line) for line in (workspace / "gh.jsonl").read_text().splitlines()]
                self.assertEqual(len(calls), min(index, 2))
                args = calls[-1]
                self.assertEqual(args[:2], ["pr", "create"])
                self.assertNotIn("--label", args)
                self.assertEqual(args[args.index("--repo") + 1], environment["REPO"])
                self.assertEqual(args[args.index("--base") + 1], "main")
                if pr_failure:
                    self.assertEqual(result.returncode, 42)
                    self.assertIn("PR creation failed", result.stderr)
                    return
                self.assertEqual(result.returncode, 0, result.stderr)
                after = git("rev-parse", "HEAD")
                self.assertEqual(after != before, index < 3, "New or modified templates must commit; unchanged templates must skip")
                self.assertEqual(git("show", "HEAD:.github/ISSUE_TEMPLATE/bug-report.yml"), contents.strip())
                self.assertEqual(git("show", "HEAD:.github/ISSUE_TEMPLATE/custom.yml"), "name: Downstream-only form")
                if index < 3:
                    self.assertEqual(git("ls-remote", "origin", f"refs/heads/bonedigger/sync-templates-{environment['SHA'][:8]}").split()[0], after)


if __name__ == "__main__":
    unittest.main()
