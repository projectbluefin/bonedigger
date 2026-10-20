"""Keep the sync matrix, App-token scope, and documented consumer roster aligned.

A repository added to ``matrix.repo`` but not to the token's ``repositories``
fails at checkout with an authorization error; one added to the token but not
the matrix silently never receives templates. Both drifts are invisible until a
template change ships, so pin them here.
"""

from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/sync-templates.yml"
TEMPLATE_GUIDE = ROOT / "docs/skills/bonedigger-templates.md"
OWNER = "projectbluefin"


def sync_job():
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["sync"]


def matrix_repos(job):
    return job["strategy"]["matrix"]["repo"]


def token_step(job):
    steps = [step for step in job["steps"] if str(step.get("uses", "")).startswith("actions/create-github-app-token@")]
    if len(steps) != 1:
        raise AssertionError(f"expected exactly one create-github-app-token step, found {len(steps)}")
    return steps[0]


def token_repositories(step):
    return [name.strip() for name in str(step["with"]["repositories"]).split(",") if name.strip()]


def documented_roster(text):
    """Return the backticked repositories listed under the guide's roster step."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if "declared consumer roster" in line)
    roster = []
    for line in lines[start + 1 :]:
        match = re.fullmatch(r"\s+- `([^`]+)`", line)
        if not match:
            break
        roster.append(match.group(1))
    return roster


class TestConsumerRoster(unittest.TestCase):
    def setUp(self):
        self.job = sync_job()
        self.matrix = matrix_repos(self.job)
        self.token = token_step(self.job)

    def test_matrix_has_no_duplicates(self):
        self.assertEqual(len(self.matrix), len(set(self.matrix)), self.matrix)

    def test_matrix_targets_only_the_token_owner(self):
        # Without an explicit `owner`, the App token is minted for the workflow
        # repository's owner, so every destination must live in that org.
        self.assertNotIn("owner", self.token["with"])
        foreign = [repo for repo in self.matrix if repo.split("/", 1)[0] != OWNER]
        self.assertEqual(foreign, [])

    def test_token_scope_matches_matrix(self):
        scope = token_repositories(self.token)
        self.assertEqual(len(scope), len(set(scope)), scope)
        self.assertEqual(
            sorted(f"{OWNER}/{name}" for name in scope),
            sorted(self.matrix),
            "matrix.repo and the App-token `repositories` input must name the same repositories",
        )

    def test_downstream_checkout_uses_the_scoped_token(self):
        checkout = next(step for step in self.job["steps"] if step.get("with", {}).get("repository") == "${{ matrix.repo }}")
        self.assertEqual(checkout["with"]["token"], f"${{{{ steps.{self.token['id']}.outputs.token }}}}")

    def test_documented_roster_matches_matrix(self):
        roster = documented_roster(TEMPLATE_GUIDE.read_text())
        self.assertTrue(roster, "template guide no longer lists the declared consumer roster")
        self.assertEqual(sorted(roster), sorted(self.matrix))


class TestRosterParsers(unittest.TestCase):
    def test_documented_roster_stops_at_first_non_entry(self):
        text = "2. Preserve the declared consumer roster unless approved:\n   - `a/one`\n   - `a/two`\n   Keep aligned.\n   - `a/later`\n"
        self.assertEqual(documented_roster(text), ["a/one", "a/two"])

    def test_token_repositories_ignores_whitespace_and_empty_entries(self):
        self.assertEqual(token_repositories({"with": {"repositories": " one, two ,,three "}}), ["one", "two", "three"])

    def test_token_step_rejects_multiple_token_steps(self):
        job = {"steps": [{"uses": "actions/create-github-app-token@x"}, {"uses": "actions/create-github-app-token@y"}]}
        with self.assertRaises(AssertionError):
            token_step(job)


if __name__ == "__main__":
    unittest.main()
