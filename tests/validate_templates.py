#!/usr/bin/env python3
"""Validate the canonical issue templates and the sync contract that ships them.

`templates/*.yml` is copied verbatim into `.github/ISSUE_TEMPLATE/` of every
downstream repo by `.github/workflows/sync-templates.yml`. GitHub rejects a
malformed issue form silently: the form disappears from the template chooser
and no error is reported anywhere. `check-yaml` only proves the file parses,
not that it is a usable issue form, so a structural mistake here reaches five
repositories before anyone notices.

Run standalone:

    python3 tests/validate_templates.py [repo-root]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ELEMENT_TYPES = frozenset({"markdown", "input", "textarea", "dropdown", "checkboxes"})
TOP_LEVEL_KEYS = frozenset(
    {"name", "description", "title", "labels", "type", "assignees", "projects", "body"}
)
CONFIG_KEYS = frozenset({"blank_issues_enabled", "contact_links"})
CONTACT_LINK_KEYS = frozenset({"name", "url", "about"})
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

# Downstream consumers of the template sync, per docs/skills/bonedigger-templates.md
# ("Core Process" step 2). Adding a repo to the matrix without adding it to the
# app-token `repositories:` list makes the downstream checkout fail.
EXPECTED_SYNC_REPOS = frozenset(
    {
        "projectbluefin/bluefin",
        "projectbluefin/bluefin-lts",
        "projectbluefin/common",
        "projectbluefin/dakota",
        "projectbluefin/knuckle",
    }
)


def _is_text(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def validate_issue_form(filename: str, data) -> list[str]:
    """Return every structural problem in one issue-form template."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"{filename}: top level must be a mapping, got {type(data).__name__}"]

    for key in sorted(set(data) - TOP_LEVEL_KEYS):
        errors.append(f"{filename}: unknown top-level key {key!r}")

    for key in ("name", "description"):
        if not _is_text(data.get(key)):
            errors.append(f"{filename}: {key!r} is required and must be a non-empty string")

    labels = data.get("labels")
    if labels is not None:
        if not isinstance(labels, list) or not labels:
            errors.append(f"{filename}: 'labels' must be a non-empty list")
        else:
            for label in labels:
                if not _is_text(label):
                    errors.append(f"{filename}: label {label!r} must be a non-empty string")

    body = data.get("body")
    if not isinstance(body, list) or not body:
        errors.append(f"{filename}: 'body' is required and must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, element in enumerate(body):
        errors.extend(_validate_element(filename, index, element, seen_ids))
    return errors


def _validate_element(filename: str, index: int, element, seen_ids: set[str]) -> list[str]:
    where = f"{filename}: body[{index}]"
    if not isinstance(element, dict):
        return [f"{where} must be a mapping, got {type(element).__name__}"]

    errors: list[str] = []
    element_type = element.get("type")
    if element_type not in ELEMENT_TYPES:
        errors.append(
            f"{where} has unsupported type {element_type!r} "
            f"(expected one of {sorted(ELEMENT_TYPES)})"
        )
        return errors

    attributes = element.get("attributes")
    if not isinstance(attributes, dict):
        errors.append(f"{where} ({element_type}) is missing an 'attributes' mapping")
        return errors

    element_id = element.get("id")
    if element_id is not None:
        if element_type == "markdown":
            errors.append(f"{where} is markdown and must not set an 'id'")
        elif not _is_text(element_id) or not ID_PATTERN.match(str(element_id)):
            errors.append(f"{where} has invalid id {element_id!r}")
        elif element_id in seen_ids:
            errors.append(f"{where} reuses id {element_id!r}; ids must be unique per template")
        else:
            seen_ids.add(element_id)

    if element_type == "markdown":
        if not _is_text(attributes.get("value")):
            errors.append(f"{where} (markdown) needs a non-empty 'attributes.value'")
        if "validations" in element:
            errors.append(f"{where} is markdown and must not set 'validations'")
        return errors

    if not _is_text(attributes.get("label")):
        errors.append(f"{where} ({element_type}) needs a non-empty 'attributes.label'")

    if element_type in ("dropdown", "checkboxes"):
        errors.extend(_validate_options(where, element_type, attributes.get("options")))

    validations = element.get("validations")
    if validations is not None:
        if not isinstance(validations, dict):
            errors.append(f"{where} has non-mapping 'validations'")
        elif "required" in validations and not isinstance(validations["required"], bool):
            errors.append(f"{where} has non-boolean 'validations.required'")

    return errors


def _validate_options(where: str, element_type: str, options) -> list[str]:
    if not isinstance(options, list) or not options:
        return [f"{where} ({element_type}) needs a non-empty 'attributes.options' list"]

    errors: list[str] = []
    for position, option in enumerate(options):
        if element_type == "dropdown":
            if not _is_text(option):
                errors.append(f"{where} option[{position}] must be a non-empty string")
        elif not isinstance(option, dict) or not _is_text(option.get("label")):
            errors.append(f"{where} option[{position}] must be a mapping with a 'label'")
    return errors


def validate_config(data) -> list[str]:
    """Return every problem in the template-chooser config."""
    if not isinstance(data, dict):
        return [f"config.yml: top level must be a mapping, got {type(data).__name__}"]

    errors = [f"config.yml: unknown key {key!r}" for key in sorted(set(data) - CONFIG_KEYS)]

    if "blank_issues_enabled" in data and not isinstance(data["blank_issues_enabled"], bool):
        errors.append("config.yml: 'blank_issues_enabled' must be a boolean")

    links = data.get("contact_links")
    if links is not None:
        if not isinstance(links, list) or not links:
            errors.append("config.yml: 'contact_links' must be a non-empty list")
        else:
            for position, link in enumerate(links):
                if not isinstance(link, dict):
                    errors.append(f"config.yml: contact_links[{position}] must be a mapping")
                    continue
                for key in sorted(CONTACT_LINK_KEYS - set(link)):
                    errors.append(f"config.yml: contact_links[{position}] is missing {key!r}")
                for key in sorted(set(link) - CONTACT_LINK_KEYS):
                    errors.append(f"config.yml: contact_links[{position}] has unknown key {key!r}")
    return errors


def validate_sync_contract(workflow) -> list[str]:
    """Return every drift between the sync workflow and its documented contract."""
    if not isinstance(workflow, dict):
        return ["sync-templates.yml: top level must be a mapping"]

    job = (workflow.get("jobs") or {}).get("sync")
    if not isinstance(job, dict):
        return ["sync-templates.yml: the 'sync' job is missing"]

    errors: list[str] = []

    matrix_repos = (((job.get("strategy") or {}).get("matrix") or {}).get("repo")) or []
    if not isinstance(matrix_repos, list) or not matrix_repos:
        errors.append("sync-templates.yml: the sync matrix lists no downstream repos")
        matrix_repos = []
    else:
        for missing in sorted(EXPECTED_SYNC_REPOS - set(matrix_repos)):
            errors.append(f"sync-templates.yml: documented downstream repo {missing} is not synced")
        for extra in sorted(set(matrix_repos) - EXPECTED_SYNC_REPOS):
            errors.append(
                f"sync-templates.yml: {extra} is synced but undocumented in "
                "docs/skills/bonedigger-templates.md"
            )

    concurrency = job.get("concurrency")
    if not isinstance(concurrency, dict):
        errors.append("sync-templates.yml: the sync job needs a per-repo concurrency group")
    elif concurrency.get("cancel-in-progress") is not False:
        # A cancel between `git push` and `gh pr create` orphans the remote branch.
        errors.append("sync-templates.yml: concurrency must set 'cancel-in-progress: false'")

    errors.extend(_validate_token_scope(job, matrix_repos))
    return errors


def _validate_token_scope(job: dict, matrix_repos: list) -> list[str]:
    steps = job.get("steps")
    if not isinstance(steps, list):
        return ["sync-templates.yml: the sync job has no steps"]

    for step in steps:
        if not isinstance(step, dict) or step.get("id") != "app-token":
            continue
        raw = ((step.get("with") or {}).get("repositories")) or ""
        granted = {name.strip() for name in str(raw).split(",") if name.strip()}
        if not granted:
            return ["sync-templates.yml: the app token grants access to no repositories"]
        missing = sorted(
            repo for repo in matrix_repos if str(repo).split("/")[-1] not in granted
        )
        return [
            f"sync-templates.yml: {repo} is in the sync matrix but not in the app token "
            "'repositories' list"
            for repo in missing
        ]
    return ["sync-templates.yml: the 'app-token' step is missing"]


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def collect_errors(root: Path) -> list[str]:
    """Validate every template plus the sync contract under `root`."""
    errors: list[str] = []

    template_dir = root / "templates"
    templates = sorted(template_dir.glob("*.yml"))
    if not templates:
        return [f"{template_dir}: no *.yml templates found"]

    for path in templates:
        try:
            data = _load(path)
        except yaml.YAMLError as exc:
            errors.append(f"{path.name}: is not parseable YAML: {exc}")
            continue
        if path.name == "config.yml":
            errors.extend(validate_config(data))
        else:
            errors.extend(validate_issue_form(path.name, data))

    for path in sorted(template_dir.glob("*")):
        if path.is_file() and path.suffix != ".yml":
            errors.append(
                f"{path.name}: sync copies only 'templates/*.yml', so this file never "
                "reaches a downstream repo"
            )

    workflow_path = root / ".github" / "workflows" / "sync-templates.yml"
    if not workflow_path.is_file():
        errors.append("sync-templates.yml: workflow is missing")
    else:
        errors.extend(validate_sync_contract(_load(workflow_path)))

    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    errors = collect_errors(root)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} template problem(s) found.", file=sys.stderr)
        return 1
    print("templates: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
