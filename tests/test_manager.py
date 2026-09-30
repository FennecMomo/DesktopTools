"""Windows/Tk integration tests with temporary data and no system tray icon."""
import json
import logging
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(os.name == "nt", "Windows native window APIs required")
class ManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = logging.NullHandler()
        logger = logging.getLogger("desktoptools")
        logger.addHandler(handler)
        cls.addClassCleanup(logger.removeHandler, handler)
        cls.api = runpy.run_path(str(Path(__file__).resolve().parents[1] / "overlay_window.pyw"), run_name="tests_app")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.manager = self.api["DesktopManager"](
            tray_enabled=False, visible=False,
            settings_path=self.directory / "settings.json",
        )
        self.manager.root.update()
        self.manager._save_window_states_now()
        self.addCleanup(self.cleanup_manager)

    def cleanup_manager(self):
        if not self.manager._exiting:
            self.manager.exit_app()

    def persisted_tasks(self):
        return json.loads((self.directory / "windows.json").read_text(encoding="utf-8"))["tasks"]

    def test_empty_peer_input_survives_normal_exit(self):
        a = self.manager.windows[0]
        b = self.manager.add_window(task_id=a.task_id)
        self.manager.root.update()
        self.manager._save_window_states_now()
        b.timer_minutes_input.delete(0, "end")
        with patch("time.time", return_value=1234.5):
            a.add_todo_text("must survive")
        self.manager.exit_app()
        self.assertEqual(self.persisted_tasks()[0]["todos"], [{
            "text": "must survive", "done": False, "due": None, "created": 1234.5,
        }])

    def test_broken_peer_does_not_block_saving_or_other_peers(self):
        a = self.manager.windows[0]
        b = self.manager.add_window(task_id=a.task_id)
        c = self.manager.add_window(task_id=a.task_id)
        self.manager.root.update()
        with patch.object(b, "refresh_from_task", side_effect=RuntimeError("render failed")):
            a.add_todo_text("persist despite renderer")
        self.assertIn("persist despite renderer", c.todo_list.get(0))
        self.manager.exit_app()
        self.assertEqual(self.persisted_tasks()[0]["todos"][0]["text"], "persist despite renderer")

    def test_failed_save_keeps_session_then_retry_succeeds(self):
        a = self.manager.windows[0]
        a.add_todo_text("keep in memory")
        with patch.object(self.manager.window_store, "save", side_effect=PermissionError("disk full")):
            self.manager.exit_app()
            self.assertFalse(self.manager._exiting)
            self.assertEqual(self.manager.windows, [a])
            self.assertTrue(a.root.winfo_exists())
            backup = self.directory / "backup.json"
            self.assertTrue(self.manager.export_backup(backup))
            self.assertEqual(json.loads(backup.read_text(encoding="utf-8"))["tasks"][0]["todos"][0]["text"], "keep in memory")
        self.assertTrue(self.manager.retry_save())
        self.manager.exit_app()
        self.assertEqual(self.persisted_tasks()[0]["todos"][0]["text"], "keep in memory")

    def test_settings_save_failure_also_keeps_session(self):
        self.manager.opacity_percent.set(75)
        with patch.object(self.manager.settings_store, "save", side_effect=PermissionError("read only")):
            self.manager.exit_app()
            self.assertFalse(self.manager._exiting)
        self.manager.exit_app()
        self.assertEqual(json.loads((self.directory / "settings.json").read_text())["opacity_percent"], 75)

    def test_rebind_pauses_only_after_last_view_leaves(self):
        a = self.manager.windows[0]
        b = self.manager.add_window(task_id=a.task_id)
        task = a.task
        a._toggle_timer()
        task.focus_deadline = self.api["time"].monotonic() + 60
        task.focus_status = "running"
        self.manager.bind_window_to_task(a, 99)
        self.assertEqual(task.timer_status, "running")
        self.manager.bind_window_to_task(b, 100)
        self.assertEqual(task.timer_status, "paused")
        self.assertEqual(task.focus_status, "paused")
        self.assertIsNone(task.timer_deadline)
        self.assertIsNone(task.focus_deadline)
        self.assertGreater(task.timer_remaining_seconds, 0)

    def test_corrupt_startup_preserves_original_and_recovery_ui_fits(self):
        self.manager.exit_app()
        original = b'{"tasks":[{"note":"recoverable"}],"windows":['
        state_path = self.directory / "windows.json"
        state_path.write_bytes(original)
        self.manager = self.api["DesktopManager"](
            tray_enabled=False, visible=False, settings_path=self.directory / "settings.json",
        )
        self.manager.open_settings()
        self.manager.root.update()
        self.assertEqual(self.manager.window_store.backup_path.read_bytes(), original)
        self.assertLessEqual(self.manager.settings_window.winfo_reqheight(), 650)
        self.assertIn("windows", json.loads(state_path.read_text(encoding="utf-8")))

    def test_settings_overflow_scrolls_each_tab_and_keeps_footer_visible(self):
        self.manager.open_settings()
        window = self.manager.settings_window
        window.attributes("-alpha", 0)
        window.deiconify()
        window.geometry("540x420")
        self.manager.root.update()
        scroll = self.manager._settings_scroll
        for name, page in self.manager._settings_pages.items():
            with self.subTest(tab=name):
                self.manager._select_settings_page(name)
                self.manager.root.update()
                self.assertEqual(scroll.canvas.yview()[0], 0)
                self.assertLess(scroll.canvas.yview()[1], 1)
                # Wheel over a nested label, rather than only the empty canvas.
                label = page.winfo_children()[0]
                label.event_generate("<MouseWheel>", delta=-120)
                self.manager.root.update()
                self.assertGreater(scroll.canvas.yview()[0], 0)
                scroll.scrollbar.tk.call(scroll.scrollbar.cget("command"), "moveto", 1)
                self.manager.root.update()
                self.assertAlmostEqual(scroll.canvas.yview()[1], 1)
                self.assertLessEqual(
                    page.winfo_rooty() + page.winfo_height(),
                    scroll.canvas.winfo_rooty() + scroll.canvas.winfo_height(),
                )
                footer = self.manager.settings_note_label.master
                self.assertTrue(footer.winfo_ismapped())
                self.assertLessEqual(footer.winfo_y() + footer.winfo_height(), window.winfo_height())
        self.manager._select_settings_page("外观与窗口")
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        spinbox = next(w for w in descendants(scroll.body) if w.winfo_class() == "Spinbox")
        old_margin = self.manager.restore_margin.get()
        spinbox.event_generate("<MouseWheel>", delta=-120)
        self.manager.root.update()
        self.assertEqual(self.manager.restore_margin.get(), old_margin)
        self.assertGreater(scroll.canvas.yview()[0], 0)

    def test_settings_initial_height_fits_small_monitor(self):
        with patch.dict(self.manager.open_settings.__func__.__globals__, {
            "_monitor_areas_at": lambda x, y: ((0, 0, 800, 600), (0, 0, 800, 560)),
        }):
            self.manager.open_settings()
        window = self.manager.settings_window
        window.attributes("-alpha", 0)
        window.deiconify()
        self.manager.root.update()
        self.assertLessEqual(window.winfo_height(), 560 - 64)
        self.assertTrue(window.resizable()[1])

    def test_quick_capture_failure_does_not_claim_saved_or_duplicate(self):
        self.manager.open_quick_capture(prefill_clipboard=False)
        self.manager.quick_capture_text.insert("1.0", "captured once")
        with patch.object(self.manager.window_store, "save", side_effect=PermissionError("disk full")), patch.object(self.manager.tray, "notify") as notify, patch("time.time", return_value=1234.5):
            self.manager._save_quick_capture("待办")
            self.assertFalse(any(call.args[0] == "快速收集已保存" for call in notify.call_args_list))
        self.assertIsNone(self.manager.quick_capture_window)
        self.assertTrue(self.manager.retry_save())
        todos = [todo for task in self.persisted_tasks() for todo in task["todos"]]
        self.assertEqual(todos, [{"text": "captured once", "done": False, "due": None, "created": 1234.5}])

    def test_deadline_survives_edit_toggle_peer_sync_and_reopen(self):
        a = self.manager.windows[0]
        b = self.manager.add_window(task_id=a.task_id)
        a.task.todos = [("deadline task", False, 1800000000.25, 1700000000.5)]
        a.refresh_from_task()
        a.todo_list.selection_set(0)
        a._edit_todo()
        a.todo_input.delete(0, "end")
        a.todo_input.insert(0, "edited task")
        a._add_todo()
        a._toggle_todo()
        self.assertEqual(b.todo_items, [("edited task", True, 1800000000.25, 1700000000.5)])
        self.assertIn("待办 1 项（1 项完成）", self.api["_task_content_summary"](a.task))
        self.manager.exit_app()
        self.manager = self.api["DesktopManager"](
            tray_enabled=False, visible=False, settings_path=self.directory / "settings.json",
        )
        self.assertEqual(self.manager.windows[0].todo_items, [("edited task", True, 1800000000.25, 1700000000.5)])

    def test_focus_stays_in_same_window_and_due_reminder_is_not_repeated(self):
        a = self.manager.windows[0]
        a.add_todo_text("focus here")
        a.task.todos[0] = ("focus here", False, 1.0, 0.5)
        a.refresh_from_task()
        a.todo_list.selection_set(0)
        count = len(self.manager.windows)
        a._start_focus_for_selected()
        self.assertEqual(len(self.manager.windows), count)
        self.assertEqual(a.mode, "任务胶囊")
        with patch.object(self.manager.tray, "notify") as notify:
            a._apply_todo_styles(notify=True)
            a._apply_todo_styles(notify=True)
            notify.assert_called_once()
            self.assertEqual(notify.call_args.args[0], "待办已到期")

    def test_timer_completion_notifies_once_across_shared_windows(self):
        a = self.manager.windows[0]
        b = self.manager.add_window(task_id=a.task_id)
        a._toggle_timer()
        a.task.timer_deadline = self.api["time"].monotonic() - 1
        with patch.object(self.manager.tray, "notify") as notify:
            for window in (a, b):
                window.root.after_cancel(window._tick_after_id)
                window._tick_modes()
            notify.assert_called_once()
            self.assertEqual(notify.call_args.args[0], "倒计时结束")
        self.assertEqual(a.task.timer_status, "finished")

    def test_closed_windows_restore_in_number_order(self):
        a = self.manager.windows[0]
        b = self.manager.add_window()
        a.close()
        b.close()
        first = self.manager.add_window()
        second = self.manager.add_window()
        self.assertEqual([first.instance_number, second.instance_number], [a.instance_number, b.instance_number])


if __name__ == "__main__":
    unittest.main()
