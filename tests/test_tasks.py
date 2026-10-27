import json
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

from app import service, store


TASKS = [
    {"id": 1, "title": "Write Launch recap", "description": "Draft an internal summary", "status": "open", "completed_at": None},
    {"id": 2, "title": "Fix login redirect", "description": "Resolve the OAuth callback", "status": "done", "completed_at": "2026-02-21T09:15:00+00:00"},
    {"id": 3, "title": "Workshop agenda", "description": "Plan the onboarding session", "status": "open", "completed_at": None},
    {"id": 4, "title": "Archive report", "description": "Move the weekly report", "status": "open", "completed_at": None},
]


class TaskServiceTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.data_file = Path(directory.name) / "tasks.json"
        self.data_file.write_text(json.dumps(deepcopy(TASKS)), encoding="utf-8")
        data_file = patch.object(store, "DATA_FILE", self.data_file)
        data_file.start()
        self.addCleanup(data_file.stop)

    def ids(self, **filters):
        return [task["id"] for task in service.list_tasks(**filters)]

    def test_omitted_filters_preserve_all_tasks_and_order(self):
        self.assertEqual(service.list_tasks(), TASKS)

    def test_open_status_returns_only_open_tasks(self):
        self.assertEqual(self.ids(status="open"), [1, 3, 4])

    def test_done_status_returns_only_done_tasks(self):
        self.assertEqual(self.ids(status="done"), [2])

    def test_title_search_is_case_insensitive(self):
        self.assertEqual(self.ids(q="lAuNcH"), [1])

    def test_description_only_search_is_case_insensitive(self):
        self.assertEqual(self.ids(q="oNbOaRdInG"), [3])

    def test_search_matches_substrings(self):
        self.assertEqual(self.ids(q="port"), [4])

    def test_search_without_matches_returns_an_empty_list(self):
        self.assertEqual(self.ids(q="not-present"), [])

    def test_search_and_status_filters_compose(self):
        self.assertEqual(self.ids(status="open", q="PLAN"), [3])
        self.assertEqual(self.ids(status="done", q="PLAN"), [])
        self.assertEqual(self.ids(status="done", q="LOGIN"), [2])

    def test_completion_is_persisted_with_a_utc_timestamp(self):
        completed = service.complete_task(1)
        fetched = service.get_task(1)
        stored = json.loads(self.data_file.read_text(encoding="utf-8"))
        self.assertEqual(completed["status"], "done")
        self.assertIsNotNone(completed["completed_at"])
        self.assertEqual(fetched, completed)
        self.assertEqual(stored[0], completed)
        self.assertEqual(datetime.fromisoformat(fetched["completed_at"]).utcoffset(), timedelta(0))
        self.assertEqual(stored[1:], TASKS[1:])

    def test_missing_task_does_not_modify_storage(self):
        before = self.data_file.read_bytes()
        self.assertIsNone(service.complete_task(999))
        self.assertEqual(self.data_file.read_bytes(), before)


if __name__ == "__main__":
    main()
