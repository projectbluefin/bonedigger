#!/usr/bin/env python3
"""Unit tests for tests/validate_templates.py and the shipped templates."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_templates import (  # noqa: E402
    EXPECTED_SYNC_REPOS,
    collect_errors,
    validate_config,
    validate_issue_form,
    validate_sync_contract,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def form(**overrides):
    base = {
        "name": "Bug report",
        "description": "Something is broken.",
        "labels": ["type/bug"],
        "body": [
            {"type": "markdown", "attributes": {"value": "Run `ujust report` first."}},
            {
                "type": "input",
                "id": "report-link",
                "attributes": {"label": "ujust report gist URL"},
                "validations": {"required": True},
            },
        ],
    }
    base.update(overrides)
    return base


def workflow(**overrides):
    job = {
        "concurrency": {"group": "sync-templates-x", "cancel-in-progress": False},
        "strategy": {"matrix": {"repo": sorted(EXPECTED_SYNC_REPOS)}},
        "steps": [
            {
                "id": "app-token",
                "uses": "actions/create-github-app-token@deadbeef",
                "with": {"repositories": "bluefin,bluefin-lts,common,dakota,knuckle"},
            }
        ],
    }
    job.update(overrides)
    return {"jobs": {"sync": job}}


class IssueFormTests(unittest.TestCase):
    def test_valid_form_has_no_errors(self):
        self.assertEqual(validate_issue_form("bug-report.yml", form()), [])

    def test_top_level_must_be_a_mapping(self):
        self.assertIn("must be a mapping", validate_issue_form("x.yml", ["body"])[0])

    def test_missing_name_and_description_are_reported(self):
        data = form()
        del data["name"]
        data["description"] = "   "
        errors = validate_issue_form("x.yml", data)
        self.assertTrue(any("'name'" in e for e in errors))
        self.assertTrue(any("'description'" in e for e in errors))

    def test_unknown_top_level_key_is_reported(self):
        errors = validate_issue_form("x.yml", form(titel="typo"))
        self.assertIn("unknown top-level key 'titel'", errors[0])

    def test_labels_must_be_non_empty_strings(self):
        self.assertTrue(any("non-empty list" in e for e in validate_issue_form("x.yml", form(labels=[]))))
        self.assertTrue(any("must be a non-empty string" in e for e in validate_issue_form("x.yml", form(labels=[""]))))

    def test_body_must_be_a_non_empty_list(self):
        for value in ([], None, {"type": "input"}):
            with self.subTest(value=value):
                errors = validate_issue_form("x.yml", form(body=value))
                self.assertEqual(len(errors), 1)
                self.assertIn("'body' is required", errors[0])

    def test_unsupported_element_type_is_reported(self):
        errors = validate_issue_form("x.yml", form(body=[{"type": "slider", "attributes": {}}]))
        self.assertIn("unsupported type 'slider'", errors[0])

    def test_element_needs_attributes_mapping(self):
        errors = validate_issue_form("x.yml", form(body=[{"type": "input", "id": "a"}]))
        self.assertIn("missing an 'attributes' mapping", errors[0])

    def test_markdown_requires_value_and_rejects_id_and_validations(self):
        errors = validate_issue_form(
            "x.yml",
            form(body=[{"type": "markdown", "id": "intro", "attributes": {"value": ""}, "validations": {}}]),
        )
        self.assertTrue(any("must not set an 'id'" in e for e in errors))
        self.assertTrue(any("non-empty 'attributes.value'" in e for e in errors))
        self.assertTrue(any("must not set 'validations'" in e for e in errors))

    def test_input_requires_label(self):
        errors = validate_issue_form("x.yml", form(body=[{"type": "textarea", "attributes": {"description": "d"}}]))
        self.assertIn("non-empty 'attributes.label'", errors[0])

    def test_duplicate_and_malformed_ids_are_reported(self):
        body = [
            {"type": "input", "id": "dup", "attributes": {"label": "A"}},
            {"type": "input", "id": "dup", "attributes": {"label": "B"}},
            {"type": "input", "id": "bad id!", "attributes": {"label": "C"}},
        ]
        errors = validate_issue_form("x.yml", form(body=body))
        self.assertTrue(any("reuses id 'dup'" in e for e in errors))
        self.assertTrue(any("invalid id 'bad id!'" in e for e in errors))

    def test_dropdown_options_must_be_non_empty_strings(self):
        self.assertTrue(
            any(
                "non-empty 'attributes.options'" in e
                for e in validate_issue_form(
                    "x.yml", form(body=[{"type": "dropdown", "attributes": {"label": "L", "options": []}}])
                )
            )
        )
        errors = validate_issue_form(
            "x.yml", form(body=[{"type": "dropdown", "attributes": {"label": "L", "options": [{"label": "a"}]}}])
        )
        self.assertIn("option[0] must be a non-empty string", errors[0])

    def test_checkbox_options_must_carry_labels(self):
        errors = validate_issue_form(
            "x.yml", form(body=[{"type": "checkboxes", "attributes": {"label": "L", "options": ["plain"]}}])
        )
        self.assertIn("option[0] must be a mapping with a 'label'", errors[0])

    def test_validations_required_must_be_boolean(self):
        body = [{"type": "input", "attributes": {"label": "L"}, "validations": {"required": "yes"}}]
        errors = validate_issue_form("x.yml", form(body=body))
        self.assertIn("non-boolean 'validations.required'", errors[0])


class ConfigTests(unittest.TestCase):
    def test_minimal_config_is_valid(self):
        self.assertEqual(validate_config({"blank_issues_enabled": True}), [])

    def test_unknown_key_is_reported(self):
        self.assertIn("unknown key 'blank_issues'", validate_config({"blank_issues": True})[0])

    def test_blank_issues_enabled_must_be_boolean(self):
        self.assertIn("must be a boolean", validate_config({"blank_issues_enabled": "true"})[0])

    def test_contact_link_keys_are_checked(self):
        errors = validate_config(
            {"contact_links": [{"name": "Chat", "url": "https://example.test", "abuot": "typo"}]}
        )
        self.assertTrue(any("is missing 'about'" in e for e in errors))
        self.assertTrue(any("unknown key 'abuot'" in e for e in errors))

    def test_contact_links_must_be_a_non_empty_list(self):
        self.assertIn("non-empty list", validate_config({"contact_links": []})[0])


class SyncContractTests(unittest.TestCase):
    def test_documented_contract_passes(self):
        self.assertEqual(validate_sync_contract(workflow()), [])

    def test_missing_sync_job_is_reported(self):
        self.assertIn("'sync' job is missing", validate_sync_contract({"jobs": {}})[0])

    def test_dropped_downstream_repo_is_reported(self):
        wf = workflow()
        wf["jobs"]["sync"]["strategy"]["matrix"]["repo"] = [
            r for r in sorted(EXPECTED_SYNC_REPOS) if r != "projectbluefin/knuckle"
        ]
        errors = validate_sync_contract(wf)
        self.assertTrue(any("projectbluefin/knuckle is not synced" in e for e in errors))

    def test_undocumented_downstream_repo_is_reported(self):
        wf = workflow()
        wf["jobs"]["sync"]["strategy"]["matrix"]["repo"].append("projectbluefin/website")
        errors = validate_sync_contract(wf)
        self.assertTrue(any("projectbluefin/website is synced but undocumented" in e for e in errors))

    def test_repo_missing_from_token_scope_is_reported(self):
        wf = workflow()
        wf["jobs"]["sync"]["steps"][0]["with"]["repositories"] = "bluefin,common,dakota,knuckle"
        errors = validate_sync_contract(wf)
        self.assertTrue(any("bluefin-lts" in e and "app token" in e for e in errors))

    def test_cancel_in_progress_must_be_false(self):
        wf = workflow()
        wf["jobs"]["sync"]["concurrency"]["cancel-in-progress"] = True
        self.assertTrue(any("cancel-in-progress: false" in e for e in validate_sync_contract(wf)))

        wf = workflow()
        del wf["jobs"]["sync"]["concurrency"]
        self.assertTrue(any("per-repo concurrency group" in e for e in validate_sync_contract(wf)))

    def test_missing_app_token_step_is_reported(self):
        wf = workflow()
        wf["jobs"]["sync"]["steps"] = [{"uses": "actions/checkout@deadbeef"}]
        self.assertIn("'app-token' step is missing", validate_sync_contract(wf)[0])


class ShippedTemplateTests(unittest.TestCase):
    """The templates and workflow actually in this repo must pass the validator."""

    def test_repository_is_clean(self):
        self.assertEqual(collect_errors(REPO_ROOT), [])

    def test_every_template_is_yml_so_the_sync_copy_picks_it_up(self):
        names = {p.name for p in (REPO_ROOT / "templates").iterdir() if p.is_file()}
        self.assertTrue(names)
        self.assertTrue(all(name.endswith(".yml") for name in names), names)

    def test_bug_report_keeps_the_report_link_input_required(self):
        data = yaml.safe_load((REPO_ROOT / "templates" / "bug-report.yml").read_text(encoding="utf-8"))
        element = next(e for e in data["body"] if e.get("id") == "report-link")
        self.assertEqual(element["type"], "input")
        self.assertTrue(element["validations"]["required"])

    def test_a_corrupted_copy_of_a_shipped_template_is_caught(self):
        data = yaml.safe_load((REPO_ROOT / "templates" / "bug-report.yml").read_text(encoding="utf-8"))
        broken = copy.deepcopy(data)
        broken["body"][1]["attributes"].pop("label")
        self.assertNotEqual(validate_issue_form("bug-report.yml", broken), [])


if __name__ == "__main__":
    unittest.main()
