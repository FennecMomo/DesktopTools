"""Task state and persistence, independent of Tk and Windows APIs."""
from __future__ import annotations
import json
import logging
import math
import os
import tempfile
import time
import urllib.parse
from pathlib import Path

RESTORE_MARGIN = 10
WINDOW_MODES = ("便签", "待办", "任务胶囊", "倒计时", "时钟", "快捷按键", "浏览器")
DEFAULT_BROWSER_URL = "https://www.bing.com/"
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, max(minimum, maximum)))


def _default_settings_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "DesktopTools" / "settings.json"
    return Path.home() / "AppData" / "Local" / "DesktopTools" / "settings.json"


def _browser_destination(address: str) -> str:
    if not isinstance(address, str):
        raise ValueError("网址必须是文字")
    value = address.strip()
    if not value:
        return DEFAULT_BROWSER_URL
    if len(value) > 8192:
        raise ValueError("网址过长")
    if any(character.isspace() for character in value):
        return "https://www.bing.com/search?q=" + urllib.parse.quote_plus(value)
    if "://" not in value:
        if ":" in value and "." not in value.split(":", 1)[0] and not value.startswith("localhost:"):
            raise ValueError("仅支持 http:// 或 https:// 网页")
        if "." not in value and not value.startswith("localhost:"):
            return "https://www.bing.com/search?q=" + urllib.parse.quote_plus(value)
        scheme = "http://" if value.startswith(("localhost:", "127.0.0.1:")) else "https://"
        value = scheme + value
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("仅支持有效的 http:// 或 https:// 网址")
    return value


def _parse_hide_hotkey(value: str) -> tuple[str, int, int]:
    if not isinstance(value, str):
        raise ValueError("请输入快捷键组合，例如 Ctrl+K")
    parts = [part.strip().lower() for part in value.split("+")]
    if len(parts) < 2 or any(not part for part in parts):
        raise ValueError("请输入快捷键组合，例如 Ctrl+K")
    aliases = {"control": "ctrl"}
    names = {
        "ctrl": ("Ctrl", MOD_CONTROL),
        "alt": ("Alt", MOD_ALT),
        "shift": ("Shift", MOD_SHIFT),
    }
    modifiers = 0
    seen: set[str] = set()
    for part in parts[:-1]:
        name = aliases.get(part, part)
        if name not in names or name in seen:
            raise ValueError("修饰键仅支持 Ctrl、Alt、Shift，且不能重复")
        seen.add(name)
        modifiers |= names[name][1]
    if not modifiers & (MOD_CONTROL | MOD_ALT):
        raise ValueError("快捷隐藏至少需要 Ctrl 或 Alt")
    key_name = parts[-1].upper()
    if len(key_name) == 1 and key_name in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        virtual_key = ord(key_name)
    elif key_name.startswith("F") and key_name[1:].isdigit() and 1 <= int(key_name[1:]) <= 12:
        number = int(key_name[1:])
        key_name = f"F{number}"
        virtual_key = 0x70 + number - 1
    else:
        raise ValueError("主键只支持 A–Z、0–9 或 F1–F12")
    if modifiers == (MOD_CONTROL | MOD_ALT) and key_name == "D":
        raise ValueError("Ctrl+Alt+D 已用于快速收集")
    label = "+".join(names[name][0] for name in ("ctrl", "alt", "shift") if name in seen)
    return f"{label}+{key_name}", modifiers, virtual_key


class ProtectedJsonStore:
    """Keep unreadable input intact until an exact recovery copy is durable."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.load_warning: str | None = None
        self.backup_path: Path | None = None
        self._load_blocked = False
        self._loaded = False
        self._document: dict = {}

    def _preserve_original(self, contents: bytes) -> None:
        descriptor, name = tempfile.mkstemp(
            prefix=self.path.name + ".recovery-", suffix=".bak", dir=self.path.parent,
        )
        backup = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as file:
                file.write(contents)
                file.flush()
                os.fsync(file.fileno())
        except BaseException:
            backup.unlink(missing_ok=True)
            raise
        self.backup_path = backup
        self.load_warning = f"原存档无法加载，已保留恢复副本：{backup}"

    def _read_document(self, *, window_state: bool = False) -> dict:
        if self._loaded:
            return self._document
        self._loaded = True
        try:
            contents = self.path.read_bytes()
        except FileNotFoundError:
            return self._document
        except OSError:
            self._load_blocked = True
            self.load_warning = f"无法读取原存档，已禁止覆盖：{self.path}"
            logging.getLogger("desktoptools").exception("State read failed: %s", self.path)
            return self._document
        try:
            raw = json.loads(contents.decode("utf-8-sig"))
            if not isinstance(raw, dict):
                raise ValueError("存档根节点必须是对象")
            if window_state and (
                not isinstance(raw.get("windows"), list)
                or ("tasks" in raw and not isinstance(raw["tasks"], list))
                or raw.get("version", 1) not in (1, 2)
            ):
                raise ValueError("窗口存档结构或版本无效")
        except (UnicodeError, ValueError):
            logging.getLogger("desktoptools").warning("Invalid state: %s", self.path)
            try:
                self._preserve_original(contents)
            except OSError:
                self._load_blocked = True
                self.load_warning = f"无法备份原存档，已禁止覆盖：{self.path}"
                logging.getLogger("desktoptools").exception("Recovery backup failed")
            return self._document
        self._document = raw
        return raw

    def _prepare_save(self) -> None:
        if self._load_blocked:
            # Retrying a save may succeed after a permissions/disk issue is fixed.
            # Never replace the source until its original bytes are preserved.
            try:
                contents = self.path.read_bytes()
            except FileNotFoundError:
                pass
            else:
                self._preserve_original(contents)
            self._load_blocked = False


def _finite_number(value: object) -> bool:
    # Huge JSON integers are finite but cannot be converted to a C double.
    return type(value) is int or (type(value) is float and math.isfinite(value))


class SettingsStore(ProtectedJsonStore):
    DEFAULTS = {
        "opacity_percent": 86,
        "edge_collapse_enabled": True,
        "restore_margin": RESTORE_MARGIN,
        "no_background": False,
        "auto_update": False,
        "hide_hotkey": "Ctrl+K",
    }

    def __init__(self, path: Path | None = None) -> None:
        super().__init__(Path(path) if path is not None else _default_settings_path())

    def load(self) -> dict[str, int | bool | str]:
        raw = self._read_document()

        opacity = raw.get("opacity_percent")
        if not _finite_number(opacity):
            opacity = self.DEFAULTS["opacity_percent"]

        edge_collapse = raw.get("edge_collapse_enabled")
        if not isinstance(edge_collapse, bool):
            edge_collapse = self.DEFAULTS["edge_collapse_enabled"]

        restore_margin = raw.get("restore_margin")
        if not _finite_number(restore_margin):
            restore_margin = self.DEFAULTS["restore_margin"]

        no_background = raw.get("no_background")
        if not isinstance(no_background, bool):
            no_background = self.DEFAULTS["no_background"]

        auto_update = raw.get("auto_update")
        if not isinstance(auto_update, bool):
            auto_update = self.DEFAULTS["auto_update"]

        try:
            hide_hotkey = _parse_hide_hotkey(raw.get("hide_hotkey"))[0]
        except ValueError:
            hide_hotkey = self.DEFAULTS["hide_hotkey"]

        return {
            "opacity_percent": _clamp(round(opacity), 55, 100),
            "edge_collapse_enabled": edge_collapse,
            "restore_margin": _clamp(round(restore_margin), 0, 80),
            "no_background": no_background,
            "auto_update": auto_update,
            "hide_hotkey": hide_hotkey,
        }

    def save(self, settings: dict[str, int | bool | str]) -> None:
        self._prepare_save()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "opacity_percent": _clamp(int(settings["opacity_percent"]), 55, 100),
            "edge_collapse_enabled": bool(settings["edge_collapse_enabled"]),
            "restore_margin": _clamp(int(settings["restore_margin"]), 0, 80),
            "no_background": bool(settings["no_background"]),
            "auto_update": bool(settings["auto_update"]),
            "hide_hotkey": _parse_hide_hotkey(settings["hide_hotkey"])[0],
        }
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="settings-",
            suffix=".tmp",
            dir=self.path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
            self._document = payload
            self._loaded = True
        except BaseException:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise


class TaskState:
    """Content and timers shared by every window bound to one task number."""

    def __init__(self, task_id: int) -> None:
        self.id = task_id
        self.note = ""
        self.todos: list[tuple[str, bool, float | None, float | None]] = []
        self.focus_task_index: int | None = None
        self.focus_status = "ready"
        self.focus_remaining_seconds: float = 25 * 60
        self.focus_deadline: float | None = None
        self.timer_minutes = 25
        self.timer_remaining_seconds: float = 25 * 60
        self.timer_deadline: float | None = None
        self.timer_status = "ready"

    @classmethod
    def from_record(cls, task_id: int, record: dict[str, object]) -> "TaskState":
        task = cls(task_id)
        task.note = record.get("note") if isinstance(record.get("note"), str) else ""
        raw_todos = record.get("todos")
        if isinstance(raw_todos, list):
            task.todos = [
                (
                    item["text"],
                    item["done"],
                    item.get("due")
                    if type(item.get("due")) in (int, float)
                    and math.isfinite(item.get("due"))
                    else None,
                    item.get("created")
                    if type(item.get("created")) in (int, float)
                    and math.isfinite(item.get("created"))
                    else None,
                )
                for item in raw_todos
                if isinstance(item, dict)
                and isinstance(item.get("text"), str)
                and isinstance(item.get("done"), bool)
            ]
        minutes = record.get("timer_minutes")
        if type(minutes) is int:
            task.timer_minutes = _clamp(minutes, 1, 180)
        task.timer_remaining_seconds = task.timer_minutes * 60
        focus_index = record.get("focus_task_index")
        if type(focus_index) is int and 0 <= focus_index < len(task.todos):
            task.focus_task_index = focus_index
            status = record.get("focus_status")
            if status in ("running", "paused", "finished"):
                task.focus_status = "paused" if status == "running" else status
        remaining = record.get("focus_remaining_seconds")
        if _finite_number(remaining):
            task.focus_remaining_seconds = _clamp(round(remaining), 0, 180 * 60)
        else:
            task.focus_remaining_seconds = task.timer_minutes * 60
        return task

    def pause_timers(self) -> None:
        now = time.monotonic()
        if self.focus_deadline is not None:
            self.focus_remaining_seconds = max(0, self.focus_deadline - now)
            self.focus_deadline = None
            self.focus_status = "paused"
        if self.timer_deadline is not None:
            self.timer_remaining_seconds = max(0, self.timer_deadline - now)
            self.timer_deadline = None
            self.timer_status = "paused"

    def snapshot(self) -> dict[str, object]:
        return {
            "id": self.id,
            "note": self.note,
            "todos": [
                {
                    "text": title,
                    "done": done,
                    "due": due,
                    "created": created,
                }
                for title, done, due, created in self.todos
            ],
            "focus_task_index": self.focus_task_index,
            "focus_status": self.focus_status,
            "focus_remaining_seconds": (
                max(0, math.ceil(self.focus_deadline - time.monotonic()))
                if self.focus_deadline is not None
                else max(0, math.ceil(self.focus_remaining_seconds))
            ),
            "timer_minutes": self.timer_minutes,
            "timer_status": self.timer_status,
        }



class WindowStateStore(ProtectedJsonStore):
    """Persist window presentation separately from shared task content."""

    def __init__(self, path: Path | None = None) -> None:
        super().__init__(Path(path) if path is not None else _default_settings_path().with_name("windows.json"))

    def load(self) -> list[dict[str, object]]:
        raw = self._read_document(window_state=True)
        if not isinstance(raw, dict) or not isinstance(raw.get("windows"), list):
            return []

        windows: list[dict[str, object]] = []
        has_tasks = isinstance(raw.get("tasks"), list)
        seen_ids: set[int] = set()
        for item in raw["windows"]:
            if not isinstance(item, dict):
                continue
            number = item.get("id")
            geometry = item.get("geometry")
            if (
                type(number) is not int
                or number < 1
                or number in seen_ids
                or not self._valid_geometry(geometry)
            ):
                continue
            seen_ids.add(number)
            mode = item.get("mode")
            task_id = item.get("task_id")
            if type(task_id) is not int or task_id < 1:
                task_id = number
            timer_minutes = item.get("timer_minutes")
            raw_todos = item.get("todos")
            todos = []
            if isinstance(raw_todos, list):
                for todo in raw_todos:
                    if (
                        isinstance(todo, dict)
                        and isinstance(todo.get("text"), str)
                        and isinstance(todo.get("done"), bool)
                    ):
                        todos.append({"text": todo["text"], "done": todo["done"]})
            focus_index = item.get("focus_task_index")
            if type(focus_index) is not int or not 0 <= focus_index < len(todos):
                focus_index = None
            focus_status = item.get("focus_status")
            if focus_status not in ("ready", "running", "paused", "finished"):
                focus_status = "ready"
            raw_remaining = item.get("focus_remaining_seconds")
            default_remaining = (
                _clamp(timer_minutes, 1, 180) if type(timer_minutes) is int else 25
            ) * 60
            focus_remaining = (
                _clamp(round(raw_remaining), 0, 180 * 60)
                if _finite_number(raw_remaining)
                else default_remaining
            )
            ball_geometry = item.get("ball_geometry")
            dock_edge = item.get("dock_edge")
            collapsed = (
                item.get("collapsed") is True
                and self._valid_geometry(ball_geometry)
                and dock_edge in ("left", "right", "top", "bottom")
            )
            try:
                browser_url = _browser_destination(item.get("browser_url", ""))
            except (TypeError, ValueError):
                browser_url = DEFAULT_BROWSER_URL
            window_record = {
                "id": number,
                "task_id": task_id,
                "active": item.get("active") is True,
                "mode": (
                    "待办" if not has_tasks and mode == "任务胶囊" and focus_index is None
                    else mode if mode in WINDOW_MODES else WINDOW_MODES[0]
                ),
                "geometry": list(geometry),
                "collapsed": collapsed,
                "locked": item.get("locked") is True and not collapsed,
                "ball_geometry": list(ball_geometry) if collapsed else None,
                "dock_edge": dock_edge if collapsed else None,
                "browser_url": browser_url,
            }
            if not has_tasks:
                window_record.update(
                    {
                        "note": item["note"] if isinstance(item.get("note"), str) else "",
                        "todos": todos,
                        "focus_task_index": focus_index,
                        "focus_status": focus_status if focus_index is not None else "ready",
                        "focus_remaining_seconds": focus_remaining,
                        "timer_minutes": (
                            _clamp(timer_minutes, 1, 180)
                            if type(timer_minutes) is int else 25
                        ),
                    }
                )
            windows.append(window_record)
        return windows

    def load_tasks(self) -> list[dict[str, object]] | None:
        raw = self._read_document(window_state=True)
        if not isinstance(raw, dict) or not isinstance(raw.get("tasks"), list):
            return None
        tasks: list[dict[str, object]] = []
        seen_ids: set[int] = set()
        for item in raw["tasks"]:
            if not isinstance(item, dict):
                continue
            task_id = item.get("id")
            if type(task_id) is not int or task_id < 1 or task_id in seen_ids:
                continue
            seen_ids.add(task_id)
            tasks.append(TaskState.from_record(task_id, item).snapshot())
        return tasks

    @staticmethod
    def _valid_geometry(value: object) -> bool:
        return (
            isinstance(value, (list, tuple))
            and len(value) == 4
            and all(type(component) is int for component in value)
            and value[0] > 0
            and value[1] > 0
        )

    def save(
        self,
        windows: list[dict[str, object]],
        tasks: list[dict[str, object]],
    ) -> None:
        self._prepare_save()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 2, "windows": windows, "tasks": tasks}
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="windows-",
            suffix=".tmp",
            dir=self.path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
                json.dump(
                    payload,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
            self._document = payload
            self._loaded = True
        except BaseException:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
