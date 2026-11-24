"""Keep the main-failure alert listening to every run that syncs main.

``sync-templates.yml`` only fires on pushes that touch ``templates/**``; a fix
to the workflow itself is delivered with a ``workflow_dispatch`` run on main
(docs/skills/bonedigger-templates.md). If ci-alert.yml ignores dispatched
runs, the documented recovery never closes an open alert and a failed
dispatch never opens one.
"""

from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
ALERT = ROOT / ".github/workflows/ci-alert.yml"
SYNC = ROOT / ".github/workflows/sync-templates.yml"


def triggers(path):
    doc = yaml.safe_load(path.read_text())
    # PyYAML reads the bare key ``on`` as boolean True.
    return doc.get("on", doc.get(True))


class CiAlertEventsTest(unittest.TestCase):
    def test_alert_accepts_every_main_trigger_of_the_sync(self):
        condition = yaml.safe_load(ALERT.read_text())["jobs"]["alert"]["if"]
        for event in ("push", "workflow_dispatch"):
            with self.subTest(event=event):
                self.assertIn(event, triggers(SYNC))
                self.assertIn(f"github.event.workflow_run.event == '{event}'", condition)


if __name__ == "__main__":
    unittest.main()
