"""Check templates/ against GitHub's issue-form syntax before it is synced.

GitHub does not reject an invalid issue form on push: the consumer repository's
template chooser drops it and shows an error banner instead. Every form here is
copied into each consumer listed in sync-templates.yml, so one malformed form
breaks bug reporting everywhere at once. These are the rules GitHub documents in
"Syntax for issue forms" and "Syntax for GitHub's form schema".
"""

from pathlib import Path
import re
import unittest

import yaml

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
FORM_KEYS = {"name", "description", "body", "assignees", "labels", "title", "projects", "type"}
ELEMENT_KEYS = {"type", "id", "attributes", "validations"}
INPUT_TYPES = {"input", "textarea", "dropdown", "checkboxes"}
ATTRIBUTES = {
    "markdown": ({"value"}, {"value"}),
    "input": ({"label"}, {"label", "description", "placeholder", "value"}),
    "textarea": ({"label"}, {"label", "description", "placeholder", "value", "render"}),
    "dropdown": ({"label", "options"}, {"label", "description", "options", "multiple", "default"}),
    "checkboxes": ({"label", "options"}, {"label", "description", "options"}),
}
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def forms():
    return sorted(path for path in TEMPLATES.glob("*.yml") if path.name != "config.yml")


def load(path):
    with path.open() as handle:
        return yaml.safe_load(handle)


def problems(form):
    """Return every schema violation in one parsed issue form."""
    found = []
    if not isinstance(form, dict):
        return ["form is not a mapping"]
    for key in sorted(set(form) - FORM_KEYS):
        found.append(f"unknown top-level key {key!r}")
    for key in ("name", "description"):
        if not isinstance(form.get(key), str) or not form[key].strip():
            found.append(f"{key} must be a non-empty string")
    body = form.get("body")
    if not isinstance(body, list) or not body:
        return found + ["body must be a non-empty list"]

    ids, labels = set(), set()
    has_input = False
    for index, element in enumerate(body):
        where = f"body[{index}]"
        if not isinstance(element, dict):
            found.append(f"{where} is not a mapping")
            continue
        for key in sorted(set(element) - ELEMENT_KEYS):
            found.append(f"{where}: unknown key {key!r}")
        kind = element.get("type")
        if kind not in ATTRIBUTES:
            found.append(f"{where}: unknown type {kind!r}")
            continue
        has_input |= kind in INPUT_TYPES

        attributes = element.get("attributes")
        if not isinstance(attributes, dict):
            found.append(f"{where}: attributes must be a mapping")
            continue
        required, allowed = ATTRIBUTES[kind]
        for key in sorted(required - set(attributes)):
            found.append(f"{where}: {kind} requires attributes.{key}")
        for key in sorted(set(attributes) - allowed):
            found.append(f"{where}: {kind} does not accept attributes.{key}")

        if kind == "markdown":
            if "id" in element or "validations" in element:
                found.append(f"{where}: markdown takes neither id nor validations")
            continue

        element_id = element.get("id")
        if element_id is not None:
            if not isinstance(element_id, str) or not ID_PATTERN.match(element_id):
                found.append(f"{where}: id {element_id!r} may only use letters, digits, '-' and '_'")
            elif element_id in ids:
                found.append(f"{where}: duplicate id {element_id!r}")
            ids.add(element_id)

        label = attributes.get("label")
        if not isinstance(label, str) or not label.strip():
            found.append(f"{where}: label must be a non-empty string")
        elif label in labels:
            found.append(f"{where}: duplicate label {label!r}")
        else:
            labels.add(label)

        validations = element.get("validations", {})
        if not isinstance(validations, dict) or set(validations) - {"required"}:
            found.append(f"{where}: validations only accepts 'required'")
        elif not isinstance(validations.get("required", False), bool):
            found.append(f"{where}: validations.required must be a boolean")

        options = attributes.get("options")
        if kind == "dropdown" and "options" in attributes:
            if not isinstance(options, list) or not options:
                found.append(f"{where}: dropdown options must be a non-empty list")
            elif not all(isinstance(option, str) and option.strip() for option in options):
                found.append(f"{where}: dropdown options must be non-empty strings")
            else:
                if len(set(options)) != len(options):
                    found.append(f"{where}: dropdown options must be unique")
                if "None" in options:
                    found.append(f"{where}: 'None' is a reserved dropdown option")
                default = attributes.get("default")
                if default is not None and not (isinstance(default, int) and 0 <= default < len(options)):
                    found.append(f"{where}: dropdown default must index into options")
        if kind == "checkboxes" and "options" in attributes:
            if not isinstance(options, list) or not options:
                found.append(f"{where}: checkboxes options must be a non-empty list")
            else:
                for option in options:
                    if not isinstance(option, dict) or not isinstance(option.get("label"), str) or set(option) - {"label", "required"}:
                        found.append(f"{where}: each checkbox option needs a string label and only label/required")

    if not has_input:
        found.append("body needs at least one non-markdown field")
    return found


def config_problems(config):
    found = []
    if not isinstance(config, dict):
        return ["config.yml is not a mapping"]
    for key in sorted(set(config) - {"blank_issues_enabled", "contact_links"}):
        found.append(f"unknown key {key!r}")
    if "blank_issues_enabled" in config and not isinstance(config["blank_issues_enabled"], bool):
        found.append("blank_issues_enabled must be a boolean")
    links = config.get("contact_links", [])
    if not isinstance(links, list):
        return found + ["contact_links must be a list"]
    for index, link in enumerate(links):
        if not isinstance(link, dict) or set(link) != {"name", "url", "about"}:
            found.append(f"contact_links[{index}] needs exactly name, url and about")
        elif not str(link["url"]).startswith("https://"):
            found.append(f"contact_links[{index}].url must be an https URL")
    return found


class TestIssueForms(unittest.TestCase):
    def test_templates_directory_has_forms(self):
        self.assertTrue(forms(), "templates/ has no issue forms to sync")

    def test_every_form_follows_github_schema(self):
        for path in forms():
            with self.subTest(form=path.name):
                self.assertEqual(problems(load(path)), [])

    def test_form_names_are_unique(self):
        names = [load(path)["name"] for path in forms()]
        self.assertEqual(len(names), len(set(names)), f"duplicate form names: {names}")

    def test_chooser_config_follows_github_schema(self):
        self.assertEqual(config_problems(load(TEMPLATES / "config.yml")), [])

    def test_only_yml_files_are_shipped(self):
        # The sync step copies templates/*.yml; anything else would never reach consumers.
        strays = sorted(path.name for path in TEMPLATES.iterdir() if path.suffix != ".yml")
        self.assertEqual(strays, [])


class TestSchemaRulesCatchBreakage(unittest.TestCase):
    """Each rule must reject the mistake it exists for, or a green run proves nothing."""

    def valid(self):
        return {
            "name": "Form",
            "description": "A form",
            "body": [
                {"type": "markdown", "attributes": {"value": "Intro"}},
                {"type": "textarea", "id": "what", "attributes": {"label": "What?"}, "validations": {"required": True}},
                {"type": "dropdown", "id": "pick", "attributes": {"label": "Pick", "options": ["a", "b"]}},
            ],
        }

    def assertRejected(self, form, fragment):
        found = problems(form)
        self.assertTrue(any(fragment in problem for problem in found), f"{fragment!r} not in {found}")

    def test_valid_form_passes(self):
        self.assertEqual(problems(self.valid()), [])

    def test_rejects_missing_description(self):
        form = self.valid()
        del form["description"]
        self.assertRejected(form, "description must be")

    def test_rejects_unknown_top_level_key(self):
        form = self.valid()
        form["lables"] = ["typo"]
        self.assertRejected(form, "unknown top-level key 'lables'")

    def test_rejects_markdown_only_body(self):
        form = self.valid()
        form["body"] = form["body"][:1]
        self.assertRejected(form, "at least one non-markdown field")

    def test_rejects_unknown_element_type(self):
        form = self.valid()
        form["body"][1]["type"] = "text"
        self.assertRejected(form, "unknown type 'text'")

    def test_rejects_duplicate_ids(self):
        form = self.valid()
        form["body"][2]["id"] = "what"
        self.assertRejected(form, "duplicate id 'what'")

    def test_rejects_invalid_id_characters(self):
        form = self.valid()
        form["body"][1]["id"] = "what happened"
        self.assertRejected(form, "may only use letters")

    def test_rejects_duplicate_labels(self):
        form = self.valid()
        form["body"][2]["attributes"]["label"] = "What?"
        self.assertRejected(form, "duplicate label")

    def test_rejects_missing_label(self):
        form = self.valid()
        del form["body"][1]["attributes"]["label"]
        self.assertRejected(form, "requires attributes.label")

    def test_rejects_markdown_without_value(self):
        form = self.valid()
        form["body"][0]["attributes"] = {}
        self.assertRejected(form, "markdown requires attributes.value")

    def test_rejects_validations_on_markdown(self):
        form = self.valid()
        form["body"][0]["validations"] = {"required": True}
        self.assertRejected(form, "markdown takes neither")

    def test_rejects_string_required_flag(self):
        form = self.valid()
        form["body"][1]["validations"]["required"] = "true"
        self.assertRejected(form, "required must be a boolean")

    def test_rejects_attribute_foreign_to_type(self):
        form = self.valid()
        form["body"][1]["attributes"]["options"] = ["x"]
        self.assertRejected(form, "textarea does not accept attributes.options")

    def test_rejects_empty_and_duplicate_dropdown_options(self):
        form = self.valid()
        form["body"][2]["attributes"]["options"] = []
        self.assertRejected(form, "non-empty list")
        form["body"][2]["attributes"]["options"] = ["a", "a"]
        self.assertRejected(form, "must be unique")

    def test_rejects_reserved_none_option(self):
        form = self.valid()
        form["body"][2]["attributes"]["options"] = ["a", "None"]
        self.assertRejected(form, "reserved")

    def test_rejects_out_of_range_dropdown_default(self):
        form = self.valid()
        form["body"][2]["attributes"]["default"] = 2
        self.assertRejected(form, "default must index")

    def test_rejects_malformed_checkbox_option(self):
        form = self.valid()
        form["body"].append({"type": "checkboxes", "id": "ok", "attributes": {"label": "OK", "options": ["yes"]}})
        self.assertRejected(form, "checkbox option needs")

    def test_config_rules(self):
        self.assertEqual(config_problems({"blank_issues_enabled": True}), [])
        self.assertIn("blank_issues_enabled must be a boolean", config_problems({"blank_issues_enabled": "true"}))
        self.assertIn(
            "contact_links[0] needs exactly name, url and about",
            config_problems({"contact_links": [{"name": "Docs", "url": "https://x"}]}),
        )
        self.assertIn(
            "contact_links[0].url must be an https URL",
            config_problems({"contact_links": [{"name": "Docs", "url": "http://x", "about": "y"}]}),
        )


if __name__ == "__main__":
    unittest.main()
