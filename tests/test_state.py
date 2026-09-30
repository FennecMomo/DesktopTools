import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktoptools.state import (
    DEFAULT_BROWSER_URL, SettingsStore, TaskState, WindowStateStore,
)


class StateTests(unittest.TestCase):
    def setUp(self):
        handler = logging.NullHandler()
        logger = logging.getLogger("desktoptools")
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "windows.json"

    def test_corrupt_bytes_preserved_before_first_save(self):
        for original in (b'{"tasks":[{"note":"recoverable"}],"windows":[', b'\xff\xfeinvalid'):
            with self.subTest(original=original):
                self.path.write_bytes(original)
                store = WindowStateStore(self.path)
                self.assertEqual(store.load(), [])
                self.assertEqual(store.backup_path.read_bytes(), original)
                store.save([], [])
                self.assertEqual(store.backup_path.read_bytes(), original)
                self.assertEqual(json.loads(self.path.read_text())['tasks'], [])

    def test_invalid_root_and_task_collection_preserved(self):
        for raw in ([], {"windows": [], "tasks": {}}, {"windows": [], "version": 999}):
            with self.subTest(raw=raw):
                self.path.write_text(json.dumps(raw), encoding="utf-8")
                store = WindowStateStore(self.path)
                store.load()
                self.assertIsNotNone(store.backup_path)

    def test_backup_failure_blocks_overwrite_and_can_retry(self):
        original = b'{"recoverable": '
        self.path.write_bytes(original)
        store = WindowStateStore(self.path)
        with patch.object(store, "_preserve_original", side_effect=PermissionError("disk full")):
            store.load()
            with self.assertRaises(PermissionError):
                store.save([], [])
        self.assertEqual(self.path.read_bytes(), original)
        store.save([], [])
        self.assertEqual(store.backup_path.read_bytes(), original)

    def test_read_denial_does_not_overwrite_existing_file(self):
        original = b'{"windows":[],"tasks":[{"id":1,"note":"valuable"}]}'
        self.path.write_bytes(original)
        store = WindowStateStore(self.path)
        with patch.object(Path, "read_bytes", side_effect=PermissionError("locked")):
            self.assertEqual(store.load(), [])
            with self.assertRaises(PermissionError):
                store.save([], [])
        self.assertEqual(self.path.read_bytes(), original)
        store.save([], [])
        self.assertEqual(store.backup_path.read_bytes(), original)

    def test_missing_file_needs_no_recovery(self):
        store = WindowStateStore(self.path)
        self.assertEqual(store.load(), [])
        self.assertIsNone(store.load_warning)
        store.save([], [])
        self.assertIsNone(store.backup_path)

    def test_invalid_browser_field_is_local_to_field(self):
        for value in (None, 42, [], {}, "https://[broken"):
            with self.subTest(value=value):
                self.path.write_text(json.dumps({"windows": [{
                    "id": 1, "active": True, "geometry": [560, 320, 10, 10],
                    "browser_url": value,
                }], "tasks": [{"id": 1, "note": "keep me"}]}), encoding="utf-8")
                store = WindowStateStore(self.path)
                self.assertEqual(store.load()[0]["browser_url"], DEFAULT_BROWSER_URL)
                self.assertEqual(store.load_tasks()[0]["note"], "keep me")

    def test_nonfinite_settings_use_defaults(self):
        for value in (float("nan"), float("inf"), -float("inf"), None, True, ""):
            with self.subTest(value=value):
                self.path.write_text(json.dumps({"opacity_percent": value, "restore_margin": value}))
                settings = SettingsStore(self.path).load()
                self.assertEqual(settings["opacity_percent"], 86)
                self.assertEqual(settings["restore_margin"], 10)

    def test_230_deadline_fields_round_trip_and_221_records_migrate(self):
        records = [
            {"text": "new", "done": False, "due": 1800000000.25, "created": 1700000000.5},
            {"text": "old", "done": True},
        ]
        self.path.write_text(json.dumps({"version": 2, "windows": [], "tasks": [{"id": 1, "todos": records}]}))
        store = WindowStateStore(self.path)
        tasks = store.load_tasks()
        store.save(store.load(), tasks)
        restored = WindowStateStore(self.path).load_tasks()[0]["todos"]
        self.assertEqual(restored[0], records[0])
        self.assertEqual(restored[1], {**records[1], "due": None, "created": None})

    def test_invalid_deadlines_do_not_discard_todo(self):
        for value in (float("nan"), float("inf"), True, "tomorrow", {}):
            with self.subTest(value=value):
                task = TaskState.from_record(1, {"todos": [{"text": "keep", "done": False, "due": value, "created": value}]})
                self.assertEqual(task.snapshot()["todos"], [{"text": "keep", "done": False, "due": None, "created": None}])

    def test_pause_timers_preserves_remaining_and_status(self):
        task = TaskState(1)
        task.focus_status = task.timer_status = "running"
        task.focus_deadline, task.timer_deadline = 160, 190
        with patch("desktoptools.state.time.monotonic", return_value=100):
            task.pause_timers()
        self.assertEqual((task.focus_remaining_seconds, task.timer_remaining_seconds), (60, 90))
        self.assertEqual((task.focus_status, task.timer_status), ("paused", "paused"))
        self.assertIsNone(task.focus_deadline)
        self.assertIsNone(task.timer_deadline)


if __name__ == "__main__":
    unittest.main()
