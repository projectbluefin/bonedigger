"""Keep Python installs in CI reviewable: every direct requirement needs ==.

This gate intentionally covers pip/pip3, python -m pip and pipx run/install
in workflow run steps (.github/workflows/ and the workflow-shaped files at the
top of .github/, such as copilot-setup-steps.yml) and Justfile recipes. It is
a static check, not a general shell parser; new installer forms should extend
this gate and its fixtures together.

A VCS requirement counts as pinned only at a full 40-hex commit (git+URL@sha),
which is immutable; branch and tag refs move and are rejected like a bare name.
"""

from __future__ import annotations

import re
import shlex
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9,._-]+\])?==[A-Za-z0-9][A-Za-z0-9.!+_-]*")
VCS_PIN = re.compile(r"git\+https://[^@\s]+@[0-9a-f]{40}")
INSTALL = re.compile(
    r"(?:^|[;&|]\s*)\s*(?:sudo\s+)?"
    r"(?:pip3?|python(?:3(?:\.\d+)?)?\s+-m\s+pip)\s+"
    r"(?:(?:--disable-pip-version-check|--no-input)\s+)*install\s+"
)
PIPX = re.compile(r"(?:^|[;&|]\s*)\s*(?:sudo\s+)?pipx\s+(?:run|install)\s+")
FLAGS = {"-q", "--quiet", "-U", "--upgrade", "--user", "--no-deps",
         "--no-cache-dir", "--require-hashes", "--break-system-packages",
         "--disable-pip-version-check", "--no-input"}


def logical_lines(text):
    """Join shell/requirements continuations without swallowing comments."""
    pending = ""
    start = 1
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        if not pending:
            start = number
        pending += line.strip()
        if pending.endswith("\\"):
            pending = pending[:-1] + " "
            continue
        yield start, pending
        pending = ""
    if pending:
        yield start, pending


def pinned(requirement):
    return bool(PIN.fullmatch(requirement) or VCS_PIN.fullmatch(requirement))


def requirement_errors(root, name, seen=()):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        return [f"requirements file outside repository: {name}"]
    if path in seen:
        return [f"recursive requirements file: {name}"]
    try:
        text = path.read_text()
    except OSError:
        return [f"missing requirements file: {name}"]
    errors = []
    for line, entry in logical_lines(text):
        entry = entry.split(" #", 1)[0].strip()
        if not entry:
            continue
        if entry.startswith(("-r ", "--requirement ", "--requirement=")):
            nested = entry.replace("=", " ", 1).split(maxsplit=1)[1]
            errors += requirement_errors(root, str(path.parent / nested), (*seen, path))
            continue
        # Hashes and environment markers do not change an exact version pin.
        package = entry.split(";", 1)[0].split(" --hash=", 1)[0].strip()
        if not pinned(package):
            errors.append(f"{name}:{line}: requirement must use an exact == version: {entry}")
    return errors


def install_errors(root, text, source):
    errors = []
    for line, command in logical_lines(text):
        for match in INSTALL.finditer(command):
            lexer = shlex.shlex(command[match.end():], posix=True, punctuation_chars=";&|<>")
            lexer.whitespace_split = True
            try:
                args = list(lexer)
            except ValueError as error:
                errors.append(f"{source}:{line}: cannot inspect pip install: {error}")
                continue
            i = 0
            while i < len(args):
                arg = args[i]
                i += 1
                if not arg:
                    errors.append(f"{source}:{line}: empty pip argument")
                    continue
                if arg.isdigit() and i < len(args) and args[i][0] in "<>":
                    arg = args[i]
                    i += 1
                if arg[0] in "<>":
                    i += 1  # redirection destination is not a package
                    continue
                if arg[0] in ";&|":
                    break
                if arg in FLAGS:
                    continue
                name = None
                if arg in ("-r", "--requirement"):
                    if i == len(args):
                        errors.append(f"{source}:{line}: missing requirements filename")
                        break
                    name = args[i]
                    i += 1
                elif arg.startswith("--requirement="):
                    name = arg.split("=", 1)[1]
                elif arg.startswith("-r"):
                    name = arg[2:]
                if name is not None:
                    errors += [f"{source}:{line}: {error}" for error in requirement_errors(root, name)]
                elif not pinned(arg):
                    errors.append(f"{source}:{line}: pip argument must use an exact == version: {arg}")
    return errors


# pipx options that take a separate value (`--opt value`); the value must not
# be mistaken for the package spec. `--opt=value` is one token and needs no entry.
PIPX_VALUE_OPTIONS = frozenset({
    "--app", "--backend", "--cooldown", "--fetch-python", "--include-resources-from",
    "--index-url", "--lock", "--pip-args", "--preinstall", "--python",
    "--python-args", "--suffix", "--upgrade-strategy", "--with",
})


def pipx_errors(root, text, source):
    """pipx run/install resolves a bare name to the newest release on every
    run; the package spec (positional or --spec) must carry an == pin."""
    errors = []
    for line, command in logical_lines(text):
        for match in PIPX.finditer(command):
            lexer = shlex.shlex(command[match.end():], posix=True, punctuation_chars=";&|<>")
            lexer.whitespace_split = True
            try:
                args = list(lexer)
            except ValueError as error:
                errors.append(f"{source}:{line}: cannot inspect pipx command: {error}")
                continue
            spec = None
            i = 0
            while i < len(args):
                arg = args[i]
                i += 1
                if arg and arg[0] in ";&|":
                    break
                if arg == "--spec" and i < len(args):
                    spec = args[i]
                    i += 1
                    continue
                if arg.startswith("--spec="):
                    spec = arg.split("=", 1)[1]
                    continue
                if arg in PIPX_VALUE_OPTIONS:
                    i += 1
                    continue
                if arg.startswith("-"):
                    continue
                if spec is None:
                    spec = arg
                break  # anything after the package or app name belongs to it
            if spec is None:
                errors.append(f"{source}:{line}: pipx command names no package")
            elif not pinned(spec):
                errors.append(f"{source}:{line}: pipx package must use an exact == version: {spec}")
    return errors


def check_tree(root):
    errors = []
    paths = []
    for folder in (".github", ".github/workflows"):
        paths += sorted((root / folder).glob("*.yml"))
        paths += sorted((root / folder).glob("*.yaml"))

    def inspect(node, source):
        if isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                if key.value == "run" and isinstance(value, yaml.ScalarNode):
                    where = f"{source}:{value.start_mark.line + 1}"
                    errors.extend(install_errors(root, value.value, where))
                    errors.extend(pipx_errors(root, value.value, where))
                else:
                    inspect(value, source)
        elif isinstance(node, yaml.SequenceNode):
            for child in node.value:
                inspect(child, source)

    for path in paths:
        inspect(yaml.compose(path.read_text()), path.relative_to(root))
    justfile = root / "Justfile"
    if justfile.exists():
        errors.extend(install_errors(root, justfile.read_text(), "Justfile"))
        errors.extend(pipx_errors(root, justfile.read_text(), "Justfile"))
    return errors


# Installs that predate this gate and still need pinning. Each entry is the
# exact error the gate reports today; once the install is pinned the entry
# goes stale and the test fails until it is removed, so the list only shrinks.
# Pinning pr-validate.yml (pip install --user -r .github/requirements-ci.txt) must delete
# its entry below in the same commit.
BASELINE = frozenset({
})


class PythonInstallPinTests(unittest.TestCase):
    def test_repository_installs_are_pinned(self):
        errors = set(check_tree(ROOT))
        self.assertEqual(sorted(errors - BASELINE), [])
        self.assertEqual(sorted(BASELINE - errors), [], "stale BASELINE entry: remove it")

    def test_install_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements.txt").write_text("# helpers\npyyaml==6.0.3\njsonschema==4.26.0\n")
            for command in (
                "pip install pyyaml==6.0.3 jsonschema==4.26.0",
                "pip3 install -q 'pyyaml==6.0.3' # comment",
                "python3 -m pip install --quiet -r requirements.txt",
                "pip install --requirement=requirements.txt",
                "pip install -rrequirements.txt",
                "pip install pyyaml==6.0.3 2>/dev/null || true",
                "pip install --quiet git+https://example.com/pkg.git@" + "0" * 40,
                "# pip install unpinned",
                "echo 'pip install unpinned'",
            ):
                with self.subTest(command=command):
                    self.assertEqual(install_errors(root, command, "fixture"), [])
            for command in (
                "pip install pyyaml", "pip3 install pyyaml>=6",
                "python -m pip install pyyaml==6.*", "pip install -r missing.txt",
                "pip install pyyaml==6.0.3 jsonschema",
                "echo start && python3 -m pip install jsonschema",
                "pip install \\\n jsonschema", "pip install -r requirements.txt jsonschema",
                "pip install --requirement", "pip install git+https://example.com/pkg",
                "pip install git+https://example.com/pkg@main",
                "pip install git+https://example.com/pkg@v1.2.3",
                "pip install git+https://example.com/pkg@" + "0" * 7,
                "pip install git+https://example.com/pkg@" + "0" * 40 + "@main",
                "pip install ${PACKAGE}", "pip install pyyaml===6.0.3",
            ):
                with self.subTest(command=command):
                    self.assertTrue(install_errors(root, command, "fixture"))

    def test_pipx_forms(self):
        for command in (
            "pipx run pre-commit==4.7.0 run --all-files",
            "pipx run --spec pre-commit==4.7.0 pre-commit run --all-files",
            "pipx run --spec=pre-commit==4.7.0 pre-commit run --all-files",
            "pipx install --force pre-commit==4.7.0",
            "sudo pipx install pre-commit==4.7.0 && pre-commit run",
            "pipx run pre-commit==4.7.0 run pre-commit",
            "pipx run --python 3.12 pre-commit==4.7.0 run",
            "pipx run --pip-args '--no-cache-dir' --path pre-commit==4.7.0 run",
            "pipx install --suffix _x --python=3.12 pre-commit==4.7.0",
            "# pipx run pre-commit",
            "echo 'pipx run pre-commit'",
        ):
            with self.subTest(command=command):
                self.assertEqual(pipx_errors(ROOT, command, "fixture"), [])
        for command in (
            "pipx run pre-commit run --all-files",
            "pipx run --spec pre-commit pre-commit run",
            "pipx run pre-commit>=4 run",
            "pipx install pre-commit",
            "echo start && pipx run pre-commit run",
            "pipx run \\\n pre-commit run",
            "pipx run --python 3.12",
            "pipx run --python 3.12 pre-commit run",
            "pipx install --pip-args=-q --suffix _x pre-commit",
            "pipx run ${TOOL} run",
        ):
            with self.subTest(command=command):
                self.assertTrue(pipx_errors(ROOT, command, "fixture"), command)

    def test_requirements_reject_loose_nested_missing_and_cyclic_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for entry in ("pyyaml", "pyyaml>=6", "pyyaml==6.*", "-r missing.txt",
                          "-r requirements.txt", "pyyaml==6.0.3\njsonschema",
                          "git+https://example.com/pkg@main"):
                with self.subTest(entry=entry):
                    (root / "requirements.txt").write_text(entry)
                    self.assertTrue(requirement_errors(root, "requirements.txt"))
            (root / "nested.txt").write_text('pyyaml==6.0.3 ; python_version >= "3.10"\n')
            (root / "requirements.txt").write_text(
                "-r nested.txt\njsonschema==4.26.0 \\\n --hash=sha256:abc\n"
                "git+https://example.com/pkg.git@" + "f" * 40 + "\n")
            self.assertEqual(requirement_errors(root, "requirements.txt"), [])

    def test_workflow_requirements_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "build.yml").write_text(
                "jobs:\n  check:\n    steps:\n"
                "      - run: python3 -m pip install -q -r tests/requirements.txt\n")
            (root / "tests").mkdir()
            requirements = root / "tests/requirements.txt"
            requirements.write_text("pyyaml\njsonschema\n")
            self.assertEqual(len(check_tree(root)), 2)
            requirements.write_text("pyyaml==6.0.3\njsonschema==4.26.0\n")
            self.assertEqual(check_tree(root), [])

    def test_workflow_and_justfile_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            for suffix in ("yml", "yaml"):
                (workflows / f"ci.{suffix}").write_text(
                    "jobs:\n  check:\n    steps:\n      - name: pip install harmless\n"
                    "        run: |\n          python3 -m pip install \\\n"
                    "            jsonschema\n")
            (root / "Justfile").write_text(
                "check:\n    pip install --quiet jsonschema 2>/dev/null || true\n"
                "lint:\n    pipx run pre-commit run --all-files\n")
            (root / ".github/setup.yml").write_text(
                "jobs:\n  setup:\n    steps:\n      - run: pipx run pre-commit run\n")
            errors = check_tree(root)
            self.assertEqual(len(errors), 5, errors)
            self.assertTrue(any("Justfile:2:" in error for error in errors))
            self.assertTrue(any("Justfile:4:" in error for error in errors))
            self.assertTrue(any(".github/setup.yml:4:" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
