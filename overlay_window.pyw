from __future__ import annotations

import ctypes
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import tkinter.messagebox as messagebox
import urllib.error
import urllib.request
import winreg
from collections import deque
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path
from queue import Empty, Queue


APP_TITLE = "DesktopTools 自由窗口"
APP_VERSION = "1.0.2"
UPDATE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/FennecMomo/DesktopTools/"
    "main/dist/update.json"
)
UPDATE_PACKAGE_URL = (
    "https://raw.githubusercontent.com/FennecMomo/DesktopTools/"
    "main/dist/DesktopTools.exe"
)
MAX_UPDATE_BYTES = 100 * 1024 * 1024

WINDOW_WIDTH = 560
WINDOW_HEIGHT = 320
MIN_WIDTH = 380
MIN_HEIGHT = 280
TITLE_HEIGHT = 48
LOCK_WIDTH = 68
LOCK_HEIGHT = 32
UNLOCK_ICON_SIZE = 38
CLOSE_AREA_WIDTH = 48
BALL_SIZE = 58
BALL_MARGIN = 6
RESTORE_MARGIN = 10
EDGE_TRIGGER_DISTANCE = 28
ANIMATION_STEPS = 10
ANIMATION_DELAY_MS = 14
HOVER_POLL_MS = 90
HOVER_MARGIN = 16
WINDOW_MODES = ("便签", "待办", "倒计时", "时钟")
MODE_HINTS = {
    "便签": "把临时想法放在手边",
    "待办": "双击事项即可切换完成状态",
    "倒计时": "专注、休息或提醒自己换个任务",
    "时钟": "开会或全屏工作时也能看到时间",
}

BG_OUTER = "#11141A"
BG_TITLE = "#20242D"
BG_BODY = "#292E39"
BG_PANEL = "#222730"
BORDER = "#4B5262"
TEXT = "#F5F7FA"
TEXT_MUTED = "#AAB2C0"
OUTLINED_TEXT_FILL = "#FFFFFF"
OUTLINED_TEXT_STROKE = "#000000"
ACCENT = "#66D9A6"
ACCENT_HOVER = "#80E5B7"
LOCKED_ACCENT = "#F5B85C"
LOCKED_HOVER = "#FFC873"
CLOSE_HOVER = "#E05260"
TRANSPARENT_KEY = "#010203"

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_LAYERED = 0x00080000
LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
MONITOR_DEFAULTTONEAREST = 0x00000002

WM_NULL = 0x0000
WM_DESTROY = 0x0002
WM_CONTEXTMENU = 0x007B
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_APP = 0x8000
TRAY_CALLBACK_MESSAGE = WM_APP + 20

NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100
TPM_NONOTIFY = 0x0080

TRAY_COMMAND_ADD = 1001
TRAY_COMMAND_SETTINGS = 1002
TRAY_COMMAND_EXIT = 1003
TRAY_COMMAND_UPDATE = 1004
IDI_APPLICATION = 32512
MIIM_BITMAP = 0x00000080
DIB_RGB_COLORS = 0
BI_RGB = 0
MENU_ICON_SIZE = 16


class Point(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class Rect(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", Rect),
        ("rcWork", Rect),
        ("dwFlags", wintypes.DWORD),
    ]


class Guid(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class NotifyIconData(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", Guid),
        ("hBalloonIcon", wintypes.HICON),
    ]


class BitmapInfoHeader(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class RgbQuad(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_ubyte),
        ("rgbGreen", ctypes.c_ubyte),
        ("rgbRed", ctypes.c_ubyte),
        ("rgbReserved", ctypes.c_ubyte),
    ]


class BitmapInfo(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BitmapInfoHeader),
        ("bmiColors", RgbQuad * 1),
    ]


class MenuItemInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("fMask", wintypes.UINT),
        ("fType", wintypes.UINT),
        ("fState", wintypes.UINT),
        ("wID", wintypes.UINT),
        ("hSubMenu", wintypes.HMENU),
        ("hbmpChecked", wintypes.HBITMAP),
        ("hbmpUnchecked", wintypes.HBITMAP),
        ("dwItemData", ctypes.c_size_t),
        ("dwTypeData", wintypes.LPWSTR),
        ("cch", wintypes.UINT),
        ("hbmpItem", wintypes.HBITMAP),
    ]


WindowProcedure = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class WindowClassEx(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WindowProcedure),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


def _enable_dpi_awareness() -> None:
    """Keep geometry and text crisp on scaled Windows displays."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


_enable_dpi_awareness()

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
_pointer_bits = ctypes.sizeof(ctypes.c_void_p) * 8

if _pointer_bits == 64:
    _get_window_long = user32.GetWindowLongPtrW
    _set_window_long = user32.SetWindowLongPtrW
else:
    _get_window_long = user32.GetWindowLongW
    _set_window_long = user32.SetWindowLongW

_get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
_get_window_long.restype = ctypes.c_ssize_t
_set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
_set_window_long.restype = ctypes.c_ssize_t

user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.MonitorFromPoint.argtypes = [Point, wintypes.DWORD]
user32.MonitorFromPoint.restype = wintypes.HANDLE
user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(Rect)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND,
    wintypes.DWORD,
    ctypes.c_ubyte,
    wintypes.DWORD,
]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
user32.GetLayeredWindowAttributes.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.POINTER(wintypes.DWORD),
]
user32.GetLayeredWindowAttributes.restype = wintypes.BOOL
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WindowClassEx)]
user32.RegisterClassExW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
user32.UnregisterClassW.restype = wintypes.BOOL
user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
user32.LoadIconW.restype = wintypes.HICON
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_size_t,
    wintypes.LPCWSTR,
]
user32.AppendMenuW.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.LPVOID,
]
user32.TrackPopupMenu.restype = wintypes.UINT
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.DestroyMenu.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostMessageW.restype = wintypes.BOOL
user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
user32.RegisterWindowMessageW.restype = wintypes.UINT
user32.GetCursorPos.argtypes = [ctypes.POINTER(Point)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetMenuItemInfoW.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    wintypes.BOOL,
    ctypes.POINTER(MenuItemInfo),
]
user32.SetMenuItemInfoW.restype = wintypes.BOOL

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
shell32.Shell_NotifyIconW.argtypes = [
    wintypes.DWORD,
    ctypes.POINTER(NotifyIconData),
]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(BitmapInfo),
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p),
    wintypes.HANDLE,
    wintypes.DWORD,
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
gdi32.DeleteObject.restype = wintypes.BOOL

HWND_TOPMOST = wintypes.HWND(-1)


def _top_level_handle(window: tk.Misc) -> int:
    """Return the native wrapper HWND used by Tk on Windows."""
    window.update_idletasks()
    child_handle = int(window.winfo_id())
    parent_handle = user32.GetParent(wintypes.HWND(child_handle))
    return int(parent_handle or child_handle)


def _set_native_topmost(window: tk.Misc) -> None:
    hwnd = _top_level_handle(window)
    user32.SetWindowPos(
        wintypes.HWND(hwnd),
        HWND_TOPMOST,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
    )


def _set_absolute_geometry(
    window: tk.Misc,
    *,
    width: int | None = None,
    height: int | None = None,
    x: int | None = None,
    y: int | None = None,
) -> None:
    """Move/resize a Tk window using absolute virtual-screen coordinates.

    Tk treats negative geometry coordinates as offsets from the right or bottom
    edge. SetWindowPos avoids that behavior and supports monitors placed to the
    left or above the primary display.
    """
    move_window = x is not None and y is not None
    resize_window = width is not None and height is not None
    flags = SWP_NOACTIVATE
    if not move_window:
        flags |= SWP_NOMOVE
    if not resize_window:
        flags |= SWP_NOSIZE

    hwnd = _top_level_handle(window)
    success = user32.SetWindowPos(
        wintypes.HWND(hwnd),
        HWND_TOPMOST,
        int(x or 0),
        int(y or 0),
        int(width or 0),
        int(height or 0),
        flags,
    )
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())


def _native_window_geometry(window: tk.Misc) -> tuple[int, int, int, int]:
    """Read the actual window rectangle, including withdrawn Tk windows."""
    rectangle = Rect()
    if not user32.GetWindowRect(
        wintypes.HWND(_top_level_handle(window)),
        ctypes.byref(rectangle),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return (
        rectangle.right - rectangle.left,
        rectangle.bottom - rectangle.top,
        rectangle.left,
        rectangle.top,
    )


def _colorref(color: str) -> int:
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    return (blue << 16) | (green << 8) | red


def _set_layered_attributes(hwnd: int, key: int, alpha: int, flags: int) -> bool:
    """Combine uniform alpha and a background color key on one layered window.

    Tk's -alpha and -transparentcolor attributes each replace the layered
    window flags, so the two cannot be active at the same time through Tk.
    Calling SetLayeredWindowAttributes directly keeps both at once.
    """
    handle = wintypes.HWND(hwnd)
    extended_style = int(_get_window_long(handle, GWL_EXSTYLE))
    if not extended_style & WS_EX_LAYERED:
        _set_window_long(handle, GWL_EXSTYLE, extended_style | WS_EX_LAYERED)
    return bool(
        user32.SetLayeredWindowAttributes(
            handle,
            key,
            _clamp(alpha, 0, 255),
            flags,
        )
    )


def _monitor_areas_at(x: int, y: int) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    monitor = user32.MonitorFromPoint(Point(x, y), MONITOR_DEFAULTTONEAREST)
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())

    monitor_area = (
        info.rcMonitor.left,
        info.rcMonitor.top,
        info.rcMonitor.right,
        info.rcMonitor.bottom,
    )
    work_area = (
        info.rcWork.left,
        info.rcWork.top,
        info.rcWork.right,
        info.rcWork.bottom,
    )
    return monitor_area, work_area


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, max(minimum, maximum)))


def _default_settings_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "DesktopTools" / "settings.json"
    return Path.home() / "AppData" / "Local" / "DesktopTools" / "settings.json"


class SettingsStore:
    DEFAULTS = {
        "opacity_percent": 86,
        "edge_collapse_enabled": True,
        "restore_margin": RESTORE_MARGIN,
        "no_background": False,
        "auto_update": False,
    }

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else _default_settings_path()

    def load(self) -> dict[str, int | bool]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raw = {}
        if not isinstance(raw, dict):
            raw = {}

        opacity = raw.get("opacity_percent")
        if isinstance(opacity, bool) or not isinstance(opacity, (int, float)):
            opacity = self.DEFAULTS["opacity_percent"]

        edge_collapse = raw.get("edge_collapse_enabled")
        if not isinstance(edge_collapse, bool):
            edge_collapse = self.DEFAULTS["edge_collapse_enabled"]

        restore_margin = raw.get("restore_margin")
        if isinstance(restore_margin, bool) or not isinstance(
            restore_margin,
            (int, float),
        ):
            restore_margin = self.DEFAULTS["restore_margin"]

        no_background = raw.get("no_background")
        if not isinstance(no_background, bool):
            no_background = self.DEFAULTS["no_background"]

        auto_update = raw.get("auto_update")
        if not isinstance(auto_update, bool):
            auto_update = self.DEFAULTS["auto_update"]

        return {
            "opacity_percent": _clamp(round(opacity), 55, 100),
            "edge_collapse_enabled": edge_collapse,
            "restore_margin": _clamp(round(restore_margin), 0, 80),
            "no_background": no_background,
            "auto_update": auto_update,
        }

    def save(self, settings: dict[str, int | bool]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "opacity_percent": _clamp(int(settings["opacity_percent"]), 55, 100),
            "edge_collapse_enabled": bool(settings["edge_collapse_enabled"]),
            "restore_margin": _clamp(int(settings["restore_margin"]), 0, 80),
            "no_background": bool(settings["no_background"]),
            "auto_update": bool(settings["auto_update"]),
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
        except BaseException:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise


class WindowStateStore:
    """Keep independent window snapshots outside the repository."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else _default_settings_path().with_name(
            "windows.json"
        )

    def load(self) -> list[dict[str, object]]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return []
        if not isinstance(raw, dict) or not isinstance(raw.get("windows"), list):
            return []

        windows: list[dict[str, object]] = []
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
            ball_geometry = item.get("ball_geometry")
            dock_edge = item.get("dock_edge")
            collapsed = (
                item.get("collapsed") is True
                and self._valid_geometry(ball_geometry)
                and dock_edge in ("left", "right", "top", "bottom")
            )
            windows.append(
                {
                    "id": number,
                    "active": item.get("active") is True,
                    "mode": mode if mode in WINDOW_MODES else WINDOW_MODES[0],
                    "geometry": list(geometry),
                    "collapsed": collapsed,
                    "locked": item.get("locked") is True and not collapsed,
                    "ball_geometry": list(ball_geometry) if collapsed else None,
                    "dock_edge": dock_edge if collapsed else None,
                    "note": item["note"] if isinstance(item.get("note"), str) else "",
                    "todos": todos,
                    "timer_minutes": (
                        _clamp(timer_minutes, 1, 180)
                        if type(timer_minutes) is int
                        else 25
                    ),
                }
            )
        return windows

    @staticmethod
    def _valid_geometry(value: object) -> bool:
        return (
            isinstance(value, (list, tuple))
            and len(value) == 4
            and all(type(component) is int for component in value)
            and value[0] > 0
            and value[1] > 0
        )

    def save(self, windows: list[dict[str, object]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="windows-",
            suffix=".tmp",
            dir=self.path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
                json.dump(
                    {"version": 1, "windows": windows},
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
        except BaseException:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise


class AutoStartStore:
    """Manage this user's Windows Run entry without requiring administrator rights."""

    KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    VALUE_NAME = "DesktopTools"

    def command(self) -> str:
        if getattr(sys, "frozen", False):
            return f'"{Path(sys.executable).resolve()}"'
        python = Path(sys.executable).resolve()
        pythonw = python.with_name("pythonw.exe")
        if pythonw.exists():
            python = pythonw
        return f'"{python}" "{Path(__file__).resolve()}"'

    def get_command(self) -> str | None:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.KEY_PATH,
                0,
                winreg.KEY_QUERY_VALUE,
            ) as key:
                value, _value_type = winreg.QueryValueEx(key, self.VALUE_NAME)
        except FileNotFoundError:
            return None
        return value if isinstance(value, str) and value.strip() else None

    def is_enabled(self) -> bool:
        return self.get_command() is not None

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                self.KEY_PATH,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(
                    key,
                    self.VALUE_NAME,
                    0,
                    winreg.REG_SZ,
                    self.command(),
                )
        else:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    self.KEY_PATH,
                    0,
                    winreg.KEY_SET_VALUE,
                ) as key:
                    winreg.DeleteValue(key, self.VALUE_NAME)
            except FileNotFoundError:
                pass

    def refresh_frozen_path(self) -> None:
        """Keep an enabled startup entry valid after the executable is moved."""
        if getattr(sys, "frozen", False):
            stored = self.get_command()
            if stored is not None and stored != self.command():
                self.set_enabled(True)


class UpdateError(Exception):
    pass


def _version_numbers(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or re.fullmatch(r"\d+\.\d+\.\d+", value) is None:
        raise UpdateError("版本号格式无效")
    return tuple(int(part) for part in value.split("."))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class UpdateClient:
    """Read the public GitHub package index and verify a staged executable."""

    def __init__(
        self,
        directory: Path | None = None,
        *,
        manifest_url: str = UPDATE_MANIFEST_URL,
        package_url: str = UPDATE_PACKAGE_URL,
        opener: Callable | None = None,
    ) -> None:
        self.directory = (
            Path(directory)
            if directory is not None
            else _default_settings_path().parent / "updates"
        )
        self.manifest_url = manifest_url
        self.package_url = package_url
        self._open = opener or urllib.request.urlopen

    @staticmethod
    def _request(url: str) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            headers={
                "User-Agent": f"DesktopTools/{APP_VERSION}",
                "Cache-Control": "no-cache",
            },
        )

    def latest(self) -> dict[str, str | int] | None:
        try:
            with self._open(self._request(self.manifest_url), timeout=15) as response:
                contents = response.read(64 * 1024 + 1)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise UpdateError(f"GitHub 返回 HTTP {error.code}") from error
        except (OSError, urllib.error.URLError) as error:
            raise UpdateError(f"无法连接 GitHub：{error}") from error
        if len(contents) > 64 * 1024:
            raise UpdateError("版本索引过大")
        try:
            raw = json.loads(contents)
        except (ValueError, UnicodeError) as error:
            raise UpdateError("版本索引不是有效 JSON") from error
        if not isinstance(raw, dict):
            raise UpdateError("版本索引格式无效")
        version = raw.get("version")
        digest = raw.get("sha256")
        size = raw.get("size")
        _version_numbers(version)
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None:
            raise UpdateError("版本索引缺少有效的 SHA-256")
        if type(size) is not int or not 0 < size <= MAX_UPDATE_BYTES:
            raise UpdateError("版本索引包含无效的文件大小")
        return {"version": version, "sha256": digest.lower(), "size": size}

    def download(self, latest: dict[str, str | int]) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        destination = self.directory / (
            f"DesktopTools-{latest['version']}-{latest['sha256'][:12]}.exe"
        )
        if (
            destination.is_file()
            and destination.stat().st_size == latest["size"]
            and _sha256_file(destination) == latest["sha256"]
        ):
            return destination

        descriptor, temporary_name = tempfile.mkstemp(
            prefix="download-",
            suffix=".tmp",
            dir=self.directory,
        )
        temporary_path = Path(temporary_name)
        try:
            digest = hashlib.sha256()
            downloaded = 0
            try:
                with os.fdopen(descriptor, "wb") as file:
                    with self._open(
                        self._request(self.package_url), timeout=30
                    ) as response:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            if downloaded == 0 and not chunk.startswith(b"MZ"):
                                raise UpdateError("下载内容不是 Windows EXE")
                            downloaded += len(chunk)
                            if downloaded > latest["size"]:
                                raise UpdateError("下载文件大小与版本索引不符")
                            digest.update(chunk)
                            file.write(chunk)
                    file.flush()
                    os.fsync(file.fileno())
            except (OSError, urllib.error.URLError) as error:
                raise UpdateError(f"下载更新失败：{error}") from error
            if downloaded != latest["size"] or digest.hexdigest() != latest["sha256"]:
                raise UpdateError("下载文件校验失败，未安装更新")
            os.replace(temporary_path, destination)
            return destination
        finally:
            temporary_path.unlink(missing_ok=True)


def _apply_staged_update(arguments: list[str]) -> int:
    """Run from the verified new EXE after the old process has exited."""
    if (
        len(arguments) != 3
        or arguments[2] not in ("restart", "no-restart")
        or not getattr(sys, "frozen", False)
    ):
        return 2
    target = Path(arguments[0]).resolve()
    expected_sha256 = arguments[1].lower()
    restart = arguments[2] == "restart"
    staged = Path(sys.executable).resolve()
    try:
        staged_sha256 = _sha256_file(staged)
    except OSError:
        return 3
    if (
        target == staged
        or target.suffix.lower() != ".exe"
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
        or staged_sha256 != expected_sha256
    ):
        return 3

    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".DesktopTools-update-",
            suffix=".tmp",
            dir=target.parent,
        )
    except OSError:
        return 4
    temporary_path = Path(temporary_name)
    try:
        with staged.open("rb") as source, os.fdopen(descriptor, "wb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
            destination.flush()
            os.fsync(destination.fileno())
        deadline = time.monotonic() + 120
        while True:
            try:
                os.replace(temporary_path, target)
                break
            except OSError as error:
                if getattr(error, "winerror", None) not in (5, 32, 33):
                    raise
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)
        if restart:
            subprocess.Popen([str(target)], cwd=target.parent)
        return 0
    except OSError:
        return 4
    finally:
        temporary_path.unlink(missing_ok=True)


def _menu_icon_color(kind: str, x: float, y: float) -> tuple[int, int, int] | None:
    center = (MENU_ICON_SIZE - 1) / 2
    dx = x - center
    dy = y - center
    radius = math.hypot(dx, dy)

    if kind == "add":
        if abs(dx) <= 1.05 and abs(dy) <= 4.1:
            return 245, 255, 250
        if abs(dy) <= 1.05 and abs(dx) <= 4.1:
            return 245, 255, 250
        if radius <= 6.65:
            return 52, 181, 122
        return None

    if kind == "settings":
        angle = math.atan2(dy, dx)
        tooth = abs(math.cos(angle * 4)) >= 0.68
        outer_radius = 7.15 if tooth else 6.1
        if 2.25 <= radius <= outer_radius:
            return 65, 169, 224
        return None

    if kind == "update":
        shaft = abs(dx) <= 1.0 and -5.6 <= dy <= 1.5
        arrow = 0 <= dy <= 4.2 and abs(dx) <= dy + 0.5
        base = 4.7 <= dy <= 5.9 and abs(dx) <= 5.2
        if shaft or arrow or base:
            return 94, 196, 231
        return None

    if kind == "exit":
        ring_center_y = 8.25
        ring_dx = x - center
        ring_dy = y - ring_center_y
        ring_radius = math.hypot(ring_dx, ring_dy)
        ring = abs(ring_radius - 5.0) <= 1.15 and not (
            y < 5.3 and abs(ring_dx) < 2.25
        )
        stem = abs(dx) <= 1.0 and 1.3 <= y <= 7.2
        if ring or stem:
            return 222, 75, 89
    return None


def _create_menu_bitmap(kind: str) -> int:
    bitmap_info = BitmapInfo()
    bitmap_info.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
    bitmap_info.bmiHeader.biWidth = MENU_ICON_SIZE
    bitmap_info.bmiHeader.biHeight = -MENU_ICON_SIZE
    bitmap_info.bmiHeader.biPlanes = 1
    bitmap_info.bmiHeader.biBitCount = 32
    bitmap_info.bmiHeader.biCompression = BI_RGB
    bits = ctypes.c_void_p()
    bitmap = gdi32.CreateDIBSection(
        None,
        ctypes.byref(bitmap_info),
        DIB_RGB_COLORS,
        ctypes.byref(bits),
        None,
        0,
    )
    if not bitmap or not bits.value:
        return 0

    pixels = (ctypes.c_uint32 * (MENU_ICON_SIZE * MENU_ICON_SIZE)).from_address(
        bits.value
    )
    samples_per_axis = 4
    sample_count = samples_per_axis * samples_per_axis
    for pixel_y in range(MENU_ICON_SIZE):
        for pixel_x in range(MENU_ICON_SIZE):
            red = green = blue = hits = 0
            for sample_y in range(samples_per_axis):
                for sample_x in range(samples_per_axis):
                    color = _menu_icon_color(
                        kind,
                        pixel_x + (sample_x + 0.5) / samples_per_axis,
                        pixel_y + (sample_y + 0.5) / samples_per_axis,
                    )
                    if color is not None:
                        red += color[0]
                        green += color[1]
                        blue += color[2]
                        hits += 1
            if not hits:
                continue
            alpha = round(255 * hits / sample_count)
            red = round(red / hits * alpha / 255)
            green = round(green / hits * alpha / 255)
            blue = round(blue / hits * alpha / 255)
            pixels[pixel_y * MENU_ICON_SIZE + pixel_x] = (
                alpha << 24 | red << 16 | green << 8 | blue
            )
    return int(bitmap)


class SystemTrayIcon:
    def __init__(
        self,
        root: tk.Misc,
        *,
        on_add: Callable[[], None],
        on_settings: Callable[[], None],
        on_update: Callable[[], None],
        on_exit: Callable[[], None],
        show_icon: bool = True,
    ) -> None:
        self.root = root
        self.on_add = on_add
        self.on_settings = on_settings
        self.on_update = on_update
        self.on_exit = on_exit
        self.show_icon = show_icon
        self._cleaned = False
        self._icon_added = False
        self._menu_bitmaps: dict[int, int] = {}
        self._pending_actions: deque[Callable[[], None]] = deque()
        self._drain_after_id: str | None = None
        self._instance_handle = kernel32.GetModuleHandleW(None)
        self._class_name = f"DesktopToolsTray_{id(self):x}"
        self._window_proc_callback = WindowProcedure(self._window_proc)
        self._taskbar_created_message = user32.RegisterWindowMessageW(
            "TaskbarCreated"
        )

        icon_resource = ctypes.cast(
            ctypes.c_void_p(IDI_APPLICATION),
            wintypes.LPCWSTR,
        )
        self._icon_handle = user32.LoadIconW(None, icon_resource)

        window_class = WindowClassEx()
        window_class.cbSize = ctypes.sizeof(WindowClassEx)
        window_class.lpfnWndProc = self._window_proc_callback
        window_class.hInstance = self._instance_handle
        window_class.hIcon = self._icon_handle
        window_class.hIconSm = self._icon_handle
        window_class.lpszClassName = self._class_name

        self._class_atom = user32.RegisterClassExW(ctypes.byref(window_class))
        if not self._class_atom:
            raise ctypes.WinError(ctypes.get_last_error())

        self.hwnd = user32.CreateWindowExW(
            0,
            self._class_name,
            APP_TITLE,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            self._instance_handle,
            None,
        )
        if not self.hwnd:
            user32.UnregisterClassW(self._class_name, self._instance_handle)
            raise ctypes.WinError(ctypes.get_last_error())

        self._menu_bitmaps = {
            TRAY_COMMAND_ADD: _create_menu_bitmap("add"),
            TRAY_COMMAND_SETTINGS: _create_menu_bitmap("settings"),
            TRAY_COMMAND_UPDATE: _create_menu_bitmap("update"),
            TRAY_COMMAND_EXIT: _create_menu_bitmap("exit"),
        }

        self._notify_data = NotifyIconData()
        self._notify_data.cbSize = ctypes.sizeof(NotifyIconData)
        self._notify_data.hWnd = self.hwnd
        self._notify_data.uID = 1
        self._notify_data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self._notify_data.uCallbackMessage = TRAY_CALLBACK_MESSAGE
        self._notify_data.hIcon = self._icon_handle
        self._notify_data.szTip = "DesktopTools 自由窗口"

        if show_icon:
            self._add_icon()
        self._drain_after_id = self.root.after(40, self._drain_actions)

    def _add_icon(self) -> None:
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._notify_data)):
            raise RuntimeError("无法创建系统托盘图标")
        self._icon_added = True

    def _window_proc(
        self,
        hwnd: int,
        message: int,
        w_param: int,
        l_param: int,
    ) -> int:
        if message == self._taskbar_created_message and self.show_icon:
            try:
                self._add_icon()
            except RuntimeError:
                pass
            return 0

        if message == TRAY_CALLBACK_MESSAGE:
            mouse_message = int(l_param) & 0xFFFFFFFF
            if mouse_message in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self._show_context_menu()
                return 0
            if mouse_message == WM_LBUTTONDBLCLK:
                self._schedule(self.on_add)
                return 0

        if message == WM_DESTROY:
            return 0

        return int(user32.DefWindowProcW(hwnd, message, w_param, l_param))

    def _show_context_menu(self) -> None:
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        try:
            user32.AppendMenuW(menu, MF_STRING, TRAY_COMMAND_ADD, "添加自由窗口")
            user32.AppendMenuW(menu, MF_STRING, TRAY_COMMAND_SETTINGS, "设置")
            user32.AppendMenuW(menu, MF_STRING, TRAY_COMMAND_UPDATE, "检查更新")
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, TRAY_COMMAND_EXIT, "退出")
            self._apply_menu_bitmaps(menu)

            cursor = Point()
            user32.GetCursorPos(ctypes.byref(cursor))
            user32.SetForegroundWindow(self.hwnd)
            command = user32.TrackPopupMenu(
                menu,
                TPM_RIGHTBUTTON | TPM_RETURNCMD | TPM_NONOTIFY,
                cursor.x,
                cursor.y,
                0,
                self.hwnd,
                None,
            )
            user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        finally:
            user32.DestroyMenu(menu)

        self.dispatch_command_for_test(command)

    def _apply_menu_bitmaps(self, menu: int) -> bool:
        all_applied = True
        for command, bitmap in self._menu_bitmaps.items():
            if not bitmap:
                all_applied = False
                continue
            item_info = MenuItemInfo()
            item_info.cbSize = ctypes.sizeof(MenuItemInfo)
            item_info.fMask = MIIM_BITMAP
            item_info.hbmpItem = wintypes.HBITMAP(bitmap)
            applied = user32.SetMenuItemInfoW(
                menu,
                command,
                False,
                ctypes.byref(item_info),
            )
            all_applied = bool(applied) and all_applied
        return all_applied

    def _schedule(self, action: Callable[[], None]) -> None:
        # Never call Tcl/Tk from inside the native WndProc callback. Doing so
        # re-enters the interpreter while it is dispatching a Windows message
        # and can terminate pythonw when the action creates another window.
        self._pending_actions.append(action)

    def _drain_actions(self) -> None:
        self._drain_after_id = None
        if self._cleaned:
            return
        while self._pending_actions:
            action = self._pending_actions.popleft()
            try:
                action()
            except Exception as error:
                self.root.report_callback_exception(
                    type(error),
                    error,
                    error.__traceback__,
                )
        if not self._cleaned:
            try:
                self._drain_after_id = self.root.after(40, self._drain_actions)
            except tk.TclError:
                pass

    def dispatch_command_for_test(self, command: int) -> None:
        actions = {
            TRAY_COMMAND_ADD: self.on_add,
            TRAY_COMMAND_SETTINGS: self.on_settings,
            TRAY_COMMAND_UPDATE: self.on_update,
            TRAY_COMMAND_EXIT: self.on_exit,
        }
        action = actions.get(command)
        if action is not None:
            self._schedule(action)

    def cleanup(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
        if self._drain_after_id is not None:
            try:
                self.root.after_cancel(self._drain_after_id)
            except tk.TclError:
                pass
            self._drain_after_id = None
        if self._icon_added:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._notify_data))
            self._icon_added = False
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None
        if self._class_atom:
            user32.UnregisterClassW(self._class_name, self._instance_handle)
            self._class_atom = 0
        for bitmap in self._menu_bitmaps.values():
            if bitmap:
                gdi32.DeleteObject(wintypes.HANDLE(bitmap))
        self._menu_bitmaps.clear()


class OverlayApp:
    def __init__(
        self,
        *,
        visible: bool = True,
        initial_position: tuple[int, int] | None = None,
        master: tk.Misc | None = None,
        on_close: Callable[["OverlayApp"], None] | None = None,
        opacity_percent: tk.IntVar | None = None,
        edge_collapse_enabled: tk.BooleanVar | None = None,
        restore_margin: tk.IntVar | None = None,
        no_background: tk.BooleanVar | None = None,
        instance_number: int = 1,
        saved_state: dict[str, object] | None = None,
        on_state_change: Callable[["OverlayApp"], None] | None = None,
    ) -> None:
        self.visible = visible
        self.on_close = on_close
        self.on_state_change = on_state_change
        self.instance_number = instance_number
        self._state_ready = False
        self._closed = False
        self.locked = False
        self.collapsed = False
        self.animating = False
        self._background_hidden = False
        self._constant_styles: list[tuple[tk.Widget, dict[str, str]]] = []
        self._stateful_styles: dict[tk.Widget, tuple[str, ...]] = {}
        self._drag_origin: tuple[int, int] | None = None
        self._resize_origin: tuple[int, int, int, int] | None = None
        self._restore_geometry: tuple[int, int, int, int] | None = None
        self._ball_geometry: tuple[int, int, int, int] | None = None
        self._dock_edge: str | None = None
        self._sync_scheduled = False
        self.mode = WINDOW_MODES[0]
        self.todo_items: list[tuple[str, bool]] = []
        self._timer_duration_minutes = 25
        self._timer_remaining_seconds = 25 * 60
        self._timer_deadline: float | None = None
        self._tick_after_id: str | None = None
        self.root = tk.Tk() if master is None else tk.Toplevel(master)
        if not visible or (saved_state is not None and saved_state["collapsed"]):
            self.root.withdraw()

        self.opacity_percent = opacity_percent or tk.IntVar(master=self.root, value=86)
        self.edge_collapse_enabled = edge_collapse_enabled or tk.BooleanVar(
            master=self.root,
            value=True,
        )
        self.restore_margin = restore_margin or tk.IntVar(
            master=self.root,
            value=RESTORE_MARGIN,
        )
        self.no_background = no_background or tk.BooleanVar(
            master=self.root,
            value=False,
        )

        self.root.title(f"{APP_TITLE} #{instance_number}")
        self.root.overrideredirect(True)
        self.root.configure(bg=BG_OUTER)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.opacity_percent.get() / 100)
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self._build_main_window()
        self._restore_saved_content(saved_state)
        restored_geometry = None
        if saved_state is None:
            self._place_initial_window(initial_position)
        else:
            restored_geometry = self._place_saved_geometry(saved_state["geometry"])
        self.root.update_idletasks()
        self._build_lock_window()
        self._build_ball_window()
        if saved_state is not None:
            self.set_mode(saved_state["mode"])
        if saved_state is not None and saved_state["collapsed"]:
            self._restore_saved_ball(saved_state, restored_geometry)
        if saved_state is not None and saved_state["locked"]:
            self.set_locked(True)

        self.root.bind("<Configure>", self._on_main_configure, add="+")
        self.root.bind("<Escape>", lambda _event: self.close())
        self.root.after_idle(self._sync_lock_window)
        self._tick_modes()

        cursor = Point()
        user32.GetCursorPos(ctypes.byref(cursor))
        self.update_background_for_hover(cursor.x, cursor.y)
        self._state_ready = True

    def _restore_saved_content(self, saved_state: dict[str, object] | None) -> None:
        self.timer_minutes.trace_add("write", self._on_timer_duration_changed)
        if saved_state is None:
            return
        self.note_text.insert("1.0", saved_state["note"])
        self.todo_items = [
            (todo["text"], todo["done"])
            for todo in saved_state["todos"]
        ]
        self._render_todos()
        self.timer_minutes.set(saved_state["timer_minutes"])
        self._timer_remaining_seconds = self._timer_duration_minutes * 60
        self._update_timer_display()

    def _place_saved_geometry(self, geometry: object) -> tuple[int, int, int, int]:
        width, height, x, y = geometry
        _, (left, top, right, bottom) = _monitor_areas_at(
            x + width // 2,
            y + height // 2,
        )
        margin = self._restore_margin_pixels()
        width = min(max(MIN_WIDTH, width), max(1, right - left - 2 * margin))
        height = min(max(MIN_HEIGHT, height), max(1, bottom - top - 2 * margin))
        x = _clamp(x, left + margin, right - width - margin)
        y = _clamp(y, top + margin, bottom - height - margin)
        _set_absolute_geometry(
            self.root,
            width=width,
            height=height,
            x=x,
            y=y,
        )
        return width, height, x, y

    def _restore_saved_ball(
        self,
        saved_state: dict[str, object],
        restored_geometry: tuple[int, int, int, int],
    ) -> None:
        _, _, ball_x, ball_y = saved_state["ball_geometry"]
        _, (left, top, right, bottom) = _monitor_areas_at(
            ball_x + BALL_SIZE // 2,
            ball_y + BALL_SIZE // 2,
        )
        ball_x = _clamp(ball_x, left + BALL_MARGIN, right - BALL_SIZE - BALL_MARGIN)
        ball_y = _clamp(ball_y, top + BALL_MARGIN, bottom - BALL_SIZE - BALL_MARGIN)
        self._restore_geometry = restored_geometry
        self._ball_geometry = (BALL_SIZE, BALL_SIZE, ball_x, ball_y)
        self._dock_edge = saved_state["dock_edge"]
        _set_absolute_geometry(
            self.ball_window,
            width=BALL_SIZE,
            height=BALL_SIZE,
            x=ball_x,
            y=ball_y,
        )
        self.collapsed = True
        if self.visible:
            self.ball_window.deiconify()
            _set_native_topmost(self.ball_window)

    def state_snapshot(self) -> dict[str, object]:
        if self._restore_geometry is not None and (self.collapsed or self.animating):
            geometry = self._restore_geometry
        else:
            geometry = _native_window_geometry(self.root)
        return {
            "id": self.instance_number,
            "active": True,
            "mode": self.mode,
            "geometry": list(geometry),
            "collapsed": self.collapsed,
            "locked": self.locked,
            "ball_geometry": list(self._ball_geometry) if self.collapsed else None,
            "dock_edge": self._dock_edge if self.collapsed else None,
            "note": self.note_text.get("1.0", "end-1c"),
            "todos": [
                {"text": title, "done": done}
                for title, done in self.todo_items
            ],
            "timer_minutes": self._timer_duration_minutes,
        }

    def _notify_state_changed(self) -> None:
        if self._state_ready and not self._closed and self.on_state_change is not None:
            self.on_state_change(self)

    def _build_main_window(self) -> None:
        border = tk.Frame(self.root, bg=BORDER, bd=0, highlightthickness=0)
        border.pack(fill="both", expand=True)

        shell = tk.Frame(border, bg=BG_BODY, bd=0, highlightthickness=0)
        shell.pack(fill="both", expand=True, padx=1, pady=1)

        self.title_bar = tk.Frame(
            shell,
            bg=BG_TITLE,
            height=TITLE_HEIGHT,
            cursor="fleur",
            bd=0,
            highlightthickness=0,
        )
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.pack_propagate(False)

        grip = tk.Label(
            self.title_bar,
            text="⠿",
            bg=BG_TITLE,
            fg=TEXT_MUTED,
            font=("Segoe UI Symbol", 14),
            padx=12,
            cursor="fleur",
        )
        grip.pack(side="left")
        self.drag_grip = grip

        self.title_label = tk.Label(
            self.title_bar,
            text=f"自由窗口 #{self.instance_number}",
            bg=BG_TITLE,
            fg=TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
            cursor="fleur",
        )
        self.title_label.pack(side="left")

        self.close_button = tk.Button(
            self.title_bar,
            text="×",
            command=self.close,
            bg=BG_TITLE,
            fg=TEXT,
            activebackground=CLOSE_HOVER,
            activeforeground="#FFFFFF",
            disabledforeground="#646B78",
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", 15),
            cursor="hand2",
            width=3,
            takefocus=False,
        )
        self.close_button.pack(side="right", fill="y")

        # This gap is occupied by the separate lock-control HWND.
        lock_gap = tk.Frame(
            self.title_bar,
            bg=BG_TITLE,
            width=LOCK_WIDTH + 12,
            bd=0,
            highlightthickness=0,
        )
        lock_gap.pack(side="right", fill="y")
        lock_gap.pack_propagate(False)

        self.mode_button = tk.Button(
            self.title_bar,
            text="便签 ▾",
            command=self._show_mode_menu,
            bg=BG_TITLE,
            fg=ACCENT,
            activebackground="#343B47",
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Microsoft YaHei UI", 9),
            cursor="hand2",
            width=9,
            takefocus=False,
        )
        self.mode_button.pack(side="right", fill="y")
        self.mode_menu = tk.Menu(
            self.root,
            tearoff=False,
            bg=BG_PANEL,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground="#102219",
            relief="flat",
        )
        for mode in WINDOW_MODES:
            self.mode_menu.add_command(
                label=mode,
                command=lambda selected=mode: self.set_mode(selected),
            )

        for widget in (self.title_bar, grip, self.title_label, lock_gap):
            widget.bind("<ButtonPress-1>", self._begin_drag)
            widget.bind("<B1-Motion>", self._drag_window)
            widget.bind("<ButtonRelease-1>", self._end_drag)

        body = tk.Frame(shell, bg=BG_BODY, bd=0, highlightthickness=0)
        body.pack(fill="both", expand=True)

        panel = tk.Frame(
            body,
            bg=BG_PANEL,
            bd=0,
            highlightbackground="#3B414E",
            highlightthickness=1,
        )
        panel.pack(fill="both", expand=True, padx=16, pady=16)

        self.status_label = tk.Label(
            panel,
            text="●  便签",
            bg=BG_PANEL,
            fg=ACCENT,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self.status_label.pack(pady=(10, 2))

        self.message_label = tk.Label(
            panel,
            text=MODE_HINTS["便签"],
            bg=BG_PANEL,
            fg=TEXT,
            justify="center",
            font=("Microsoft YaHei UI", 9),
            padx=10,
        )
        self.message_label.pack()

        self.mode_container = tk.Frame(panel, bg=BG_PANEL)
        self.mode_container.pack(fill="both", expand=True, padx=12, pady=(5, 10))

        self.resize_grip = tk.Label(
            body,
            text="◢",
            bg=BG_BODY,
            fg="#717A8C",
            font=("Segoe UI Symbol", 11),
            cursor="size_nw_se",
            padx=4,
            pady=1,
        )
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se")
        self.resize_grip.bind("<ButtonPress-1>", self._begin_resize)
        self.resize_grip.bind("<B1-Motion>", self._resize_window)
        self.resize_grip.bind("<ButtonRelease-1>", self._end_resize)

        self._constant_styles = [
            (self.root, {"bg": BG_OUTER}),
            (border, {"bg": BORDER}),
            (shell, {"bg": BG_BODY}),
            (self.title_bar, {"bg": BG_TITLE}),
            (grip, {"bg": BG_TITLE, "fg": TEXT_MUTED}),
            (self.title_label, {"bg": BG_TITLE, "fg": TEXT}),
            (lock_gap, {"bg": BG_TITLE}),
            (body, {"bg": BG_BODY}),
            (
                panel,
                {"bg": BG_PANEL, "highlightbackground": "#3B414E"},
            ),
            (self.message_label, {"bg": BG_PANEL}),
            (self.resize_grip, {"bg": BG_BODY, "fg": "#717A8C"}),
        ]
        self._stateful_styles = {
            self.close_button: (
                "bg",
                "fg",
                "activebackground",
                "activeforeground",
                "disabledforeground",
            ),
            self.status_label: ("bg", "fg"),
        }
        self._constant_styles.append(
            (
                self.mode_button,
                {
                    "bg": BG_TITLE,
                    "fg": ACCENT,
                    "activebackground": "#343B47",
                    "activeforeground": TEXT,
                },
            )
        )
        self._constant_styles.append((self.mode_container, {"bg": BG_PANEL}))
        self._build_mode_views()

    def _register_mode_style(
        self,
        widget: tk.Widget,
        **options: str,
    ) -> tk.Widget:
        self._constant_styles.append((widget, options))
        return widget

    def _build_mode_views(self) -> None:
        self.mode_views: dict[str, tk.Frame] = {}
        for mode in WINDOW_MODES:
            view = tk.Frame(self.mode_container, bg=BG_PANEL)
            self._register_mode_style(view, bg=BG_PANEL)
            self.mode_views[mode] = view

        note_view = self.mode_views["便签"]
        self.note_text = tk.Text(
            note_view,
            wrap="word",
            undo=True,
            bg=BG_PANEL,
            fg=TEXT,
            insertbackground=ACCENT,
            selectbackground="#476A60",
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Microsoft YaHei UI", 11),
            padx=8,
            pady=6,
        )
        self.note_text.pack(fill="both", expand=True)
        self._register_mode_style(self.note_text, bg=BG_PANEL)
        self.note_text.bind("<<Modified>>", self._on_note_modified)

        todo_view = self.mode_views["待办"]
        self.todo_entry_row = tk.Frame(todo_view, bg=BG_PANEL)
        self.todo_entry_row.pack(fill="x", pady=(0, 5))
        self._register_mode_style(self.todo_entry_row, bg=BG_PANEL)
        self.todo_input = tk.Entry(
            self.todo_entry_row,
            bg=BG_BODY,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            bd=0,
            font=("Microsoft YaHei UI", 10),
        )
        self.todo_input.pack(side="left", fill="x", expand=True, ipady=4)
        self.todo_input.bind("<Return>", self._add_todo)
        self._register_mode_style(self.todo_input, bg=BG_BODY, fg=TEXT)
        todo_add = tk.Button(
            self.todo_entry_row,
            text="添加",
            command=self._add_todo,
            bg=ACCENT,
            fg="#102219",
            relief="flat",
            bd=0,
            padx=12,
            cursor="hand2",
        )
        todo_add.pack(side="right", padx=(8, 0), ipady=2)
        self._register_mode_style(todo_add, bg=ACCENT, fg="#102219")

        self.todo_list = tk.Listbox(
            todo_view,
            bg=BG_PANEL,
            fg=TEXT,
            selectbackground="#3B6557",
            selectforeground=TEXT,
            exportselection=False,
            activestyle="none",
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Microsoft YaHei UI", 10),
        )
        self.todo_list.pack(fill="both", expand=True)
        self.todo_list.bind("<Double-Button-1>", self._toggle_todo)
        self._register_mode_style(
            self.todo_list,
            bg=BG_PANEL,
            selectbackground="#3B6557",
        )
        self.todo_actions = tk.Frame(todo_view, bg=BG_PANEL)
        self.todo_actions.pack(fill="x", pady=(4, 0))
        self._register_mode_style(self.todo_actions, bg=BG_PANEL)
        for label, action in (
            ("完成 / 撤销", self._toggle_todo),
            ("删除选中", self._delete_todo),
        ):
            button = tk.Button(
                self.todo_actions,
                text=label,
                command=action,
                bg=BG_BODY,
                fg=TEXT_MUTED,
                relief="flat",
                bd=0,
                padx=8,
                cursor="hand2",
                font=("Microsoft YaHei UI", 8),
            )
            button.pack(side="left", padx=(0, 8))
            self._register_mode_style(button, bg=BG_BODY, fg=TEXT_MUTED)

        timer_view = self.mode_views["倒计时"]
        self.timer_label = tk.Label(
            timer_view,
            text="25:00",
            bg=BG_PANEL,
            fg=TEXT,
            font=("Segoe UI", 30, "bold"),
        )
        self.timer_label.pack(expand=True)
        self._register_mode_style(self.timer_label, bg=BG_PANEL)
        self.timer_actions = tk.Frame(timer_view, bg=BG_PANEL)
        self.timer_actions.pack(pady=(0, 4))
        self._register_mode_style(self.timer_actions, bg=BG_PANEL)
        self.timer_minutes = tk.IntVar(master=self.root, value=25)
        self.timer_minutes_input = tk.Spinbox(
            self.timer_actions,
            from_=1,
            to=180,
            textvariable=self.timer_minutes,
            width=4,
            justify="center",
            bg=BG_BODY,
            fg=TEXT,
            buttonbackground=BG_TITLE,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.timer_minutes_input.pack(side="left", padx=(0, 3))
        self._register_mode_style(self.timer_minutes_input, bg=BG_BODY, fg=TEXT)
        minutes_label = tk.Label(
            self.timer_actions,
            text="分钟",
            bg=BG_PANEL,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 9),
        )
        minutes_label.pack(side="left", padx=(0, 12))
        self._register_mode_style(minutes_label, bg=BG_PANEL, fg=TEXT_MUTED)
        self.timer_start_button = tk.Button(
            self.timer_actions,
            text="开始",
            command=self._toggle_timer,
            bg=ACCENT,
            fg="#102219",
            relief="flat",
            bd=0,
            padx=13,
            cursor="hand2",
        )
        self.timer_start_button.pack(side="left", padx=(0, 8))
        self._register_mode_style(
            self.timer_start_button,
            bg=ACCENT,
            fg="#102219",
        )
        timer_reset = tk.Button(
            self.timer_actions,
            text="重置",
            command=self._reset_timer,
            bg=BG_BODY,
            fg=TEXT_MUTED,
            relief="flat",
            bd=0,
            padx=13,
            cursor="hand2",
        )
        timer_reset.pack(side="left")
        self._register_mode_style(timer_reset, bg=BG_BODY, fg=TEXT_MUTED)

        clock_view = self.mode_views["时钟"]
        self.clock_time_label = tk.Label(
            clock_view,
            bg=BG_PANEL,
            fg=TEXT,
            font=("Segoe UI", 30, "bold"),
        )
        self.clock_time_label.pack(expand=True)
        self._register_mode_style(self.clock_time_label, bg=BG_PANEL)
        self.clock_date_label = tk.Label(
            clock_view,
            bg=BG_PANEL,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 10),
        )
        self.clock_date_label.pack(pady=(0, 8))
        self._register_mode_style(self.clock_date_label, bg=BG_PANEL)
        self.mode_views[self.mode].pack(fill="both", expand=True)

        self.outlined_canvas = tk.Canvas(
            self.mode_container,
            bg=TRANSPARENT_KEY,
            bd=0,
            highlightthickness=0,
        )
        self._outline_snapshot: tuple[object, ...] | None = None
        self.outlined_canvas.bind(
            "<Configure>",
            lambda _event: self._refresh_outlined_content(),
        )

    def _show_mode_menu(self) -> None:
        if self.locked or self._background_hidden:
            return
        try:
            self.mode_menu.tk_popup(
                self.mode_button.winfo_rootx(),
                self.mode_button.winfo_rooty() + self.mode_button.winfo_height(),
            )
        finally:
            self.mode_menu.grab_release()

    def set_mode(self, mode: str) -> None:
        if mode not in self.mode_views:
            raise ValueError(f"未知窗口用途: {mode}")
        if mode == self.mode:
            return
        self.mode_views[self.mode].pack_forget()
        self.mode = mode
        self.mode_views[mode].pack(fill="both", expand=True)
        self.mode_button.configure(text=f"{mode} ▾")
        self._apply_control_colors()
        if self._background_hidden:
            self._apply_background_state()
        self._refresh_outlined_content()
        self._notify_state_changed()

    def _on_note_modified(self, _event: tk.Event) -> None:
        if not self.note_text.edit_modified():
            return
        self.note_text.edit_modified(False)
        self._refresh_outlined_content()
        self._notify_state_changed()

    def _draw_outlined_text(
        self,
        value: str,
        x: int,
        y: int,
        *,
        font: tuple[str, int] | tuple[str, int, str],
        anchor: str = "center",
        width: int = 0,
        large: bool = False,
    ) -> None:
        options = {
            "text": value,
            "font": font,
            "anchor": anchor,
            "justify": "left" if anchor == "nw" else "center",
            "width": width,
        }
        offsets = [
            (dx, dy)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if dx or dy
        ]
        if large:
            offsets.extend(((-2, 0), (2, 0), (0, -2), (0, 2)))
        for dx, dy in offsets:
            self.outlined_canvas.create_text(
                x + dx,
                y + dy,
                fill=OUTLINED_TEXT_STROKE,
                tags=("outlined-stroke",),
                **options,
            )
        self.outlined_canvas.create_text(
            x,
            y,
            fill=OUTLINED_TEXT_FILL,
            tags=("outlined-fill",),
            **options,
        )

    def _refresh_outlined_content(self) -> None:
        if not self._background_hidden:
            return
        canvas_width = max(240, self.outlined_canvas.winfo_width())
        canvas_height = max(100, self.outlined_canvas.winfo_height())
        if self.mode == "便签":
            note = self.note_text.get("1.0", "end-1c")
            content = note if note.strip() else "空便签"
        elif self.mode == "待办":
            content = "\n".join(
                f"{'☑' if done else '☐'}  {title}"
                for title, done in self.todo_items
            ) or "暂无待办"
        elif self.mode == "倒计时":
            content = str(self.timer_label.cget("text"))
        else:
            content = (
                str(self.clock_time_label.cget("text")),
                str(self.clock_date_label.cget("text")),
            )
        snapshot = (self.mode, canvas_width, canvas_height, content)
        if snapshot == self._outline_snapshot:
            return
        self._outline_snapshot = snapshot
        self.outlined_canvas.delete("all")

        if self.mode == "便签":
            if note.strip():
                self._draw_outlined_text(
                    note,
                    12,
                    8,
                    font=("Microsoft YaHei UI", 11, "bold"),
                    anchor="nw",
                    width=canvas_width - 24,
                )
            else:
                self._draw_outlined_text(
                    "空便签",
                    canvas_width // 2,
                    canvas_height // 2,
                    font=("Microsoft YaHei UI", 12, "bold"),
                )
        elif self.mode == "待办":
            self._draw_outlined_text(
                content,
                12 if self.todo_items else canvas_width // 2,
                8 if self.todo_items else canvas_height // 2,
                font=("Microsoft YaHei UI", 10, "bold"),
                anchor="nw" if self.todo_items else "center",
                width=canvas_width - 24 if self.todo_items else 0,
            )
        elif self.mode == "倒计时":
            self._draw_outlined_text(
                content,
                canvas_width // 2,
                canvas_height // 2,
                font=("Segoe UI", 30, "bold"),
                large=True,
            )
        else:
            clock_time, clock_date = content
            self._draw_outlined_text(
                clock_time,
                canvas_width // 2,
                canvas_height * 2 // 5,
                font=("Segoe UI", 30, "bold"),
                large=True,
            )
            self._draw_outlined_text(
                clock_date,
                canvas_width // 2,
                canvas_height * 3 // 4,
                font=("Microsoft YaHei UI", 10, "bold"),
            )

    def _set_outlined_view(self, visible: bool) -> None:
        if visible:
            self.note_text.pack_forget()
            self.todo_list.pack_forget()
            self.timer_label.pack_forget()
            self.clock_time_label.pack_forget()
            self.clock_date_label.pack_forget()
            self.outlined_canvas.place(
                relx=0,
                rely=0,
                relwidth=1,
                relheight=1,
            )
            self._outline_snapshot = None
            self._refresh_outlined_content()
        else:
            self.outlined_canvas.place_forget()
            self.note_text.pack(fill="both", expand=True)
            self.todo_list.pack(fill="both", expand=True)
            self.timer_label.pack(expand=True)
            self.clock_time_label.pack(expand=True)
            self.clock_date_label.pack(pady=(0, 8))
            self._outline_snapshot = None

    def _add_todo(self, _event: tk.Event | None = None) -> None:
        title = self.todo_input.get().strip()
        if not title:
            return
        self.todo_items.append((title, False))
        self.todo_input.delete(0, "end")
        self._render_todos()
        self._notify_state_changed()

    def _selected_todo_index(self) -> int | None:
        selection = self.todo_list.curselection()
        return int(selection[0]) if selection else None

    def _render_todos(self, selected: int | None = None) -> None:
        self.todo_list.delete(0, "end")
        for title, done in self.todo_items:
            self.todo_list.insert("end", f"{'☑' if done else '☐'}  {title}")
        if selected is not None and selected < len(self.todo_items):
            self.todo_list.selection_set(selected)
        self._refresh_outlined_content()

    def _toggle_todo(self, _event: tk.Event | None = None) -> None:
        selected = self._selected_todo_index()
        if selected is None:
            return
        title, done = self.todo_items[selected]
        self.todo_items[selected] = (title, not done)
        self._render_todos(selected)
        self._notify_state_changed()

    def _delete_todo(self) -> None:
        selected = self._selected_todo_index()
        if selected is None:
            return
        del self.todo_items[selected]
        self._render_todos(min(selected, len(self.todo_items) - 1))
        self._notify_state_changed()

    def _on_timer_duration_changed(self, *_trace_arguments: str) -> None:
        try:
            minutes = int(self.timer_minutes.get())
        except (tk.TclError, ValueError):
            return
        if not 1 <= minutes <= 180:
            return
        self._timer_duration_minutes = minutes
        self._notify_state_changed()

    def _timer_minutes_value(self) -> int:
        try:
            raw_minutes = int(self.timer_minutes.get())
        except (tk.TclError, ValueError):
            return self._timer_duration_minutes
        minutes = _clamp(raw_minutes, 1, 180)
        if minutes != raw_minutes:
            self.timer_minutes.set(minutes)
        return minutes

    def _toggle_timer(self) -> None:
        if self._timer_deadline is not None:
            self._timer_remaining_seconds = max(
                0,
                self._timer_deadline - time.monotonic(),
            )
            self._timer_deadline = None
            self.timer_start_button.configure(text="继续")
        else:
            if self.timer_start_button.cget("text") in ("开始", "重新开始"):
                self._timer_remaining_seconds = self._timer_minutes_value() * 60
            self._timer_deadline = time.monotonic() + self._timer_remaining_seconds
            self.timer_start_button.configure(text="暂停")
        self._update_timer_display()

    def _reset_timer(self) -> None:
        self._timer_deadline = None
        self._timer_remaining_seconds = self._timer_minutes_value() * 60
        self.timer_start_button.configure(text="开始")
        self._update_timer_display()

    def _update_timer_display(self) -> None:
        remaining = max(0, math.ceil(self._timer_remaining_seconds))
        minutes, seconds = divmod(remaining, 60)
        self.timer_label.configure(
            text=f"{minutes:02d}:{seconds:02d}",
            fg=CLOSE_HOVER if remaining == 0 else TEXT,
        )
        self._refresh_outlined_content()

    def _tick_modes(self) -> None:
        self._tick_after_id = None
        if self._closed:
            return
        if self._timer_deadline is not None:
            self._timer_remaining_seconds = max(
                0,
                self._timer_deadline - time.monotonic(),
            )
            if self._timer_remaining_seconds == 0:
                self._timer_deadline = None
                self.timer_start_button.configure(text="重新开始")
            self._update_timer_display()
        now = time.localtime()
        self.clock_time_label.configure(text=time.strftime("%H:%M:%S", now))
        weekday = "一二三四五六日"[now.tm_wday]
        self.clock_date_label.configure(
            text=f"{now.tm_year:04d}-{now.tm_mon:02d}-{now.tm_mday:02d}  星期{weekday}"
        )
        self._refresh_outlined_content()
        self._tick_after_id = self.root.after(250, self._tick_modes)

    def _build_lock_window(self) -> None:
        self.lock_window = tk.Toplevel(self.root)
        if not self.visible:
            self.lock_window.withdraw()

        self.lock_window.overrideredirect(True)
        self.lock_window.configure(bg=BG_TITLE)
        self.lock_window.attributes("-topmost", True)
        try:
            self.lock_window.attributes("-toolwindow", True)
            self.lock_window.attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            pass

        self.lock_button = tk.Button(
            self.lock_window,
            text="锁定",
            command=self.toggle_lock,
            bg=ACCENT,
            fg="#102219",
            activebackground=ACCENT_HOVER,
            activeforeground="#102219",
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
            takefocus=False,
        )
        self.lock_button.pack(fill="both", expand=True)

        self.unlock_canvas = tk.Canvas(
            self.lock_window,
            width=UNLOCK_ICON_SIZE,
            height=UNLOCK_ICON_SIZE,
            bg=TRANSPARENT_KEY,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.unlock_canvas.create_oval(
            2,
            2,
            UNLOCK_ICON_SIZE - 2,
            UNLOCK_ICON_SIZE - 2,
            fill=LOCKED_ACCENT,
            outline=LOCKED_HOVER,
            width=2,
        )
        self.unlock_canvas.create_arc(
            11,
            8,
            27,
            25,
            start=22,
            extent=200,
            style="arc",
            outline="#30200A",
            width=3,
        )
        self.unlock_canvas.create_rectangle(
            12,
            19,
            26,
            29,
            fill="#30200A",
            outline="#30200A",
        )
        self.unlock_canvas.create_oval(
            18,
            22,
            20,
            24,
            fill=LOCKED_ACCENT,
            outline=LOCKED_ACCENT,
        )
        self.unlock_canvas.bind(
            "<ButtonRelease-1>",
            lambda _event: self.set_locked(False),
        )

        self._constant_styles.append((self.lock_window, {"bg": BG_TITLE}))
        self._stateful_styles[self.lock_button] = (
            "bg",
            "fg",
            "activebackground",
            "activeforeground",
        )

    def _build_ball_window(self) -> None:
        self.ball_window = tk.Toplevel(self.root)
        self.ball_window.withdraw()
        self.ball_window.overrideredirect(True)
        self.ball_window.configure(bg=TRANSPARENT_KEY)
        self.ball_window.attributes("-topmost", True)
        try:
            self.ball_window.attributes("-toolwindow", True)
            self.ball_window.attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            pass

        self.ball_canvas = tk.Canvas(
            self.ball_window,
            width=BALL_SIZE,
            height=BALL_SIZE,
            bg=TRANSPARENT_KEY,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.ball_canvas.pack(fill="both", expand=True)
        self.ball_shape = self.ball_canvas.create_oval(
            3,
            3,
            BALL_SIZE - 3,
            BALL_SIZE - 3,
            fill=BG_TITLE,
            outline=ACCENT,
            width=3,
        )
        self.ball_canvas.create_text(
            BALL_SIZE // 2,
            BALL_SIZE // 2,
            text="展开",
            fill=TEXT,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        self.ball_canvas.bind("<Enter>", self._ball_hover_on)
        self.ball_canvas.bind("<Leave>", self._ball_hover_off)
        self.ball_canvas.bind("<ButtonRelease-1>", self._restore_from_ball)

    def _ball_hover_on(self, _event: tk.Event) -> None:
        self.ball_canvas.itemconfigure(
            self.ball_shape,
            fill="#303844",
            outline=ACCENT_HOVER,
        )

    def _ball_hover_off(self, _event: tk.Event) -> None:
        self.ball_canvas.itemconfigure(
            self.ball_shape,
            fill=BG_TITLE,
            outline=ACCENT,
        )

    def _restore_margin_pixels(self) -> int:
        try:
            return _clamp(int(self.restore_margin.get()), 0, 80)
        except (tk.TclError, ValueError):
            return RESTORE_MARGIN

    def _place_initial_window(
        self,
        initial_position: tuple[int, int] | None,
    ) -> None:
        if initial_position is None:
            cursor = Point()
            user32.GetCursorPos(ctypes.byref(cursor))
            anchor_x, anchor_y = cursor.x, cursor.y
        else:
            anchor_x, anchor_y = initial_position

        _monitor_area, work_area = _monitor_areas_at(anchor_x, anchor_y)
        left, top, right, bottom = work_area
        if initial_position is None:
            x = left + max(0, (right - left - WINDOW_WIDTH) // 2)
            y = top + max(0, (bottom - top - WINDOW_HEIGHT) // 2)
        else:
            x = _clamp(
                anchor_x,
                left + RESTORE_MARGIN,
                right - WINDOW_WIDTH - RESTORE_MARGIN,
            )
            y = _clamp(
                anchor_y,
                top + RESTORE_MARGIN,
                bottom - WINDOW_HEIGHT - RESTORE_MARGIN,
            )
        _set_absolute_geometry(
            self.root,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            x=x,
            y=y,
        )

    def _begin_drag(self, event: tk.Event) -> None:
        if self.locked:
            return
        self._drag_origin = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )

    def _drag_window(self, event: tk.Event) -> None:
        if self.locked or self._drag_origin is None:
            return
        offset_x, offset_y = self._drag_origin
        x = event.x_root - offset_x
        y = event.y_root - offset_y
        _set_absolute_geometry(self.root, x=x, y=y)

    def _end_drag(self, event: tk.Event) -> None:
        self._drag_origin = None
        if (
            self.locked
            or self.animating
            or self.collapsed
            or not self.edge_collapse_enabled.get()
        ):
            return
        dock_target = self._ball_target_at_edge(event.x_root, event.y_root)
        if dock_target is not None:
            target, edge = dock_target
            self._collapse_to_ball(target, edge)
        else:
            self._notify_state_changed()

    def _begin_resize(self, event: tk.Event) -> None:
        if self.locked:
            return
        self._resize_origin = (
            event.x_root,
            event.y_root,
            self.root.winfo_width(),
            self.root.winfo_height(),
        )

    def _resize_window(self, event: tk.Event) -> None:
        if self.locked or self._resize_origin is None:
            return
        start_x, start_y, start_width, start_height = self._resize_origin
        width = max(MIN_WIDTH, start_width + event.x_root - start_x)
        height = max(MIN_HEIGHT, start_height + event.y_root - start_y)
        _set_absolute_geometry(self.root, width=width, height=height)

    def _end_resize(self, _event: tk.Event) -> None:
        self._resize_origin = None
        self._notify_state_changed()

    def _ball_target_at_edge(
        self,
        cursor_x: int,
        cursor_y: int,
    ) -> tuple[tuple[int, int, int, int], str] | None:
        monitor_area, work_area = _monitor_areas_at(cursor_x, cursor_y)
        monitor_left, monitor_top, monitor_right, monitor_bottom = monitor_area
        work_left, work_top, work_right, work_bottom = work_area

        distances = {
            "left": abs(cursor_x - monitor_left),
            "right": abs((monitor_right - 1) - cursor_x),
            "top": abs(cursor_y - monitor_top),
            "bottom": abs((monitor_bottom - 1) - cursor_y),
        }
        edge = min(distances, key=distances.get)
        if distances[edge] > EDGE_TRIGGER_DISTANCE:
            return None

        center_x = self.root.winfo_x() + self.root.winfo_width() // 2
        center_y = self.root.winfo_y() + self.root.winfo_height() // 2
        min_x = work_left + BALL_MARGIN
        max_x = work_right - BALL_SIZE - BALL_MARGIN
        min_y = work_top + BALL_MARGIN
        max_y = work_bottom - BALL_SIZE - BALL_MARGIN

        if edge == "left":
            x = min_x
            y = _clamp(center_y - BALL_SIZE // 2, min_y, max_y)
        elif edge == "right":
            x = max_x
            y = _clamp(center_y - BALL_SIZE // 2, min_y, max_y)
        elif edge == "top":
            x = _clamp(center_x - BALL_SIZE // 2, min_x, max_x)
            y = min_y
        else:
            x = _clamp(center_x - BALL_SIZE // 2, min_x, max_x)
            y = max_y

        return (BALL_SIZE, BALL_SIZE, x, y), edge

    def _collapse_to_ball(
        self,
        target: tuple[int, int, int, int],
        dock_edge: str,
    ) -> None:
        if self.locked or self.collapsed or self.animating:
            return

        start = (
            self.root.winfo_width(),
            self.root.winfo_height(),
            self.root.winfo_x(),
            self.root.winfo_y(),
        )
        self._restore_geometry = start
        self._dock_edge = dock_edge
        self.animating = True
        self.lock_window.withdraw()
        self.root.minsize(1, 1)

        self._animate_geometry(
            start,
            target,
            lambda: self._finish_collapse(target),
        )

    def _finish_collapse(self, target: tuple[int, int, int, int]) -> None:
        self.root.withdraw()
        self._ball_geometry = target
        _set_absolute_geometry(
            self.ball_window,
            width=target[0],
            height=target[1],
            x=target[2],
            y=target[3],
        )
        if self.visible:
            self.ball_window.deiconify()
            self.ball_window.attributes("-topmost", True)
            self.ball_window.lift()
            _set_native_topmost(self.ball_window)
        self.collapsed = True
        self.animating = False
        self._notify_state_changed()

    def _restored_geometry_in_work_area(self) -> tuple[int, int, int, int]:
        if self._restore_geometry is None or self._ball_geometry is None:
            raise RuntimeError("restore geometry is unavailable")

        width, height, original_x, original_y = self._restore_geometry
        _, _, ball_x, ball_y = self._ball_geometry
        _monitor_area, work_area = _monitor_areas_at(
            ball_x + BALL_SIZE // 2,
            ball_y + BALL_SIZE // 2,
        )
        left, top, right, bottom = work_area

        margin = self._restore_margin_pixels()
        available_width = max(1, right - left - margin * 2)
        available_height = max(1, bottom - top - margin * 2)
        width = min(width, available_width)
        height = min(height, available_height)

        min_x = left + margin
        max_x = right - width - margin
        min_y = top + margin
        max_y = bottom - height - margin
        x = _clamp(original_x, min_x, max_x)
        y = _clamp(original_y, min_y, max_y)

        if self._dock_edge == "left":
            x = min_x
        elif self._dock_edge == "right":
            x = max_x
        elif self._dock_edge == "top":
            y = min_y
        elif self._dock_edge == "bottom":
            y = max_y

        return width, height, x, y

    def _restore_from_ball(self, _event: tk.Event | None = None) -> None:
        if (
            not self.collapsed
            or self.animating
            or self._restore_geometry is None
            or self._ball_geometry is None
        ):
            return

        start = self._ball_geometry
        target = self._restored_geometry_in_work_area()
        self._restore_geometry = target
        self.animating = True
        self.ball_window.withdraw()
        self.root.minsize(1, 1)
        _set_absolute_geometry(
            self.root,
            width=start[0],
            height=start[1],
            x=start[2],
            y=start[3],
        )
        if self.visible:
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            self.root.lift()
        self._animate_geometry(
            start,
            target,
            lambda: self._finish_restore(target),
        )

    def _finish_restore(self, target: tuple[int, int, int, int]) -> None:
        self.root.minsize(
            min(MIN_WIDTH, target[0]),
            min(MIN_HEIGHT, target[1]),
        )
        self.collapsed = False
        self.animating = False
        self._ball_geometry = None
        self._dock_edge = None
        if self.visible:
            self.root.focus_force()
        self._sync_lock_window()
        self._notify_state_changed()

    def _animate_geometry(
        self,
        start: tuple[int, int, int, int],
        target: tuple[int, int, int, int],
        on_complete: Callable[[], None],
        step: int = 0,
    ) -> None:
        progress = min(1.0, step / ANIMATION_STEPS)
        eased = 1.0 - (1.0 - progress) ** 3
        current = tuple(
            round(start_value + (target_value - start_value) * eased)
            for start_value, target_value in zip(start, target)
        )
        _set_absolute_geometry(
            self.root,
            width=current[0],
            height=current[1],
            x=current[2],
            y=current[3],
        )
        self.root.update_idletasks()

        if step >= ANIMATION_STEPS:
            on_complete()
            return
        self.root.after(
            ANIMATION_DELAY_MS,
            lambda: self._animate_geometry(
                start,
                target,
                on_complete,
                step + 1,
            ),
        )

    def _on_main_configure(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return
        if not self.animating and not self.collapsed:
            self._notify_state_changed()
        if self._sync_scheduled:
            return
        self._sync_scheduled = True
        self.root.after_idle(self._sync_lock_window)

    def _sync_lock_window(self) -> None:
        self._sync_scheduled = False
        if not self.lock_window.winfo_exists():
            return

        if (
            not self.visible
            or self.collapsed
            or self.animating
            or (self._background_hidden and not self.locked)
            or self.root.state() != "normal"
        ):
            self.lock_window.withdraw()
            return

        slot_x = (
            self.root.winfo_x()
            + self.root.winfo_width()
            - CLOSE_AREA_WIDTH
            - LOCK_WIDTH
            - 10
        )
        control_size = UNLOCK_ICON_SIZE if self.locked else LOCK_WIDTH
        control_height = UNLOCK_ICON_SIZE if self.locked else LOCK_HEIGHT
        x = slot_x + (LOCK_WIDTH - control_size) // 2
        y = self.root.winfo_y() + (TITLE_HEIGHT - control_height) // 2 + 1
        _set_absolute_geometry(
            self.lock_window,
            width=control_size,
            height=control_height,
            x=x,
            y=y,
        )
        self.lock_window.deiconify()
        self.lock_window.attributes("-topmost", True)
        self.lock_window.lift()
        _set_native_topmost(self.lock_window)

    def update_background_for_hover(self, cursor_x: int, cursor_y: int) -> None:
        """Hide the window chrome unless the cursor is on (or near) it."""
        if self._closed or self.locked:
            return
        if not self.no_background.get():
            self._set_background_hidden(False)
            return
        if self.collapsed or self.animating:
            return

        root_handle = _top_level_handle(self.root)
        native_rect = Rect()
        if not user32.GetWindowRect(
            wintypes.HWND(root_handle),
            ctypes.byref(native_rect),
        ):
            return
        hovered = (
            native_rect.left - HOVER_MARGIN
            <= cursor_x
            <= native_rect.right + HOVER_MARGIN
            and native_rect.top - HOVER_MARGIN
            <= cursor_y
            <= native_rect.bottom + HOVER_MARGIN
        )
        interacting = self._drag_origin is not None or self._resize_origin is not None
        self._set_background_hidden(not hovered and not interacting)

    def _set_background_hidden(self, hidden: bool) -> None:
        if self._background_hidden == hidden:
            return
        self._background_hidden = hidden
        self._apply_background_state()
        self._apply_layered_style()
        self._sync_lock_window()

    def _apply_background_state(self) -> None:
        if self._background_hidden:
            for widget, options in self._constant_styles:
                widget.configure(
                    **{option: TRANSPARENT_KEY for option in options}
                )
            for widget, options in self._stateful_styles.items():
                widget.configure(
                    **{option: TRANSPARENT_KEY for option in options}
                )
            # A transparent foreground still leaves antialiased glyph pixels
            # around the color key. Remove chrome text and widgets entirely.
            self.drag_grip.configure(text="")
            self.title_label.configure(text="")
            self.mode_button.configure(text="")
            self.close_button.configure(text="")
            self.resize_grip.configure(text="")
            self.status_label.pack_forget()
            self.message_label.pack_forget()
            self.todo_entry_row.pack_forget()
            self.todo_actions.pack_forget()
            self.timer_actions.pack_forget()
            self._set_outlined_view(True)
        else:
            for widget, options in self._constant_styles:
                widget.configure(**options)
            self.drag_grip.configure(text="⠿")
            self.title_label.configure(text=f"自由窗口 #{self.instance_number}")
            self.mode_button.configure(text=f"{self.mode} ▾")
            self.close_button.configure(text="×")
            self.resize_grip.configure(text="◢")
            self.status_label.pack(pady=(10, 2), before=self.mode_container)
            self.message_label.pack(before=self.mode_container)
            self.todo_entry_row.pack(
                fill="x",
                pady=(0, 5),
            )
            self._set_outlined_view(False)
            self.todo_actions.pack(fill="x", pady=(4, 0))
            self.timer_actions.pack(pady=(0, 4))
            self._apply_control_colors()

    def _apply_layered_style(self) -> None:
        if self._closed:
            return
        if self._background_hidden:
            _set_layered_attributes(
                _top_level_handle(self.root),
                _colorref(TRANSPARENT_KEY),
                255,
                LWA_ALPHA | LWA_COLORKEY,
            )
        else:
            self.root.attributes("-alpha", self.opacity_percent.get() / 100)

    def toggle_lock(self) -> None:
        self.set_locked(not self.locked)

    def set_locked(self, locked: bool) -> None:
        if self.locked == locked:
            return
        self.locked = locked

        hwnd = _top_level_handle(self.root)
        style = int(_get_window_long(wintypes.HWND(hwnd), GWL_EXSTYLE))
        if locked:
            style |= WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
        else:
            style &= ~(WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)
        _set_window_long(wintypes.HWND(hwnd), GWL_EXSTYLE, style)

        user32.SetWindowPos(
            wintypes.HWND(hwnd),
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE
            | SWP_NOSIZE
            | SWP_NOACTIVATE
            | SWP_FRAMECHANGED,
        )

        self._apply_control_colors()
        if locked:
            self.lock_button.pack_forget()
            self.unlock_canvas.pack(fill="both", expand=True)
            self.lock_window.configure(bg=TRANSPARENT_KEY)
            # Keep the useful content visible and click-through, but suppress
            # all chrome even when the cursor hovers over the window.
            self._set_background_hidden(True)
        else:
            self.unlock_canvas.pack_forget()
            self.lock_button.pack(fill="both", expand=True)
            self.lock_window.configure(bg=BG_TITLE)
            if self.visible:
                self.root.attributes("-topmost", True)
                self.root.lift()
                self.root.focus_force()
            cursor = Point()
            if user32.GetCursorPos(ctypes.byref(cursor)):
                self.update_background_for_hover(cursor.x, cursor.y)
            if self._background_hidden:
                self._apply_background_state()

        self._sync_lock_window()
        self._notify_state_changed()

    def _apply_control_colors(self) -> None:
        self.close_button.configure(
            bg=BG_TITLE,
            fg=TEXT,
            activebackground=CLOSE_HOVER,
            activeforeground="#FFFFFF",
            disabledforeground="#646B78",
        )
        if self.locked:
            self.status_label.configure(
                text=f"●  {self.mode} · 已锁定",
                bg=BG_PANEL,
                fg=LOCKED_ACCENT,
            )
            self.message_label.configure(
                text="鼠标可穿透窗口；点击右上角“解锁”恢复操作"
            )
            self.close_button.configure(state="disabled", cursor="arrow")
            self.mode_button.configure(state="disabled", cursor="arrow")
            self.resize_grip.configure(cursor="arrow")
            self.title_bar.configure(cursor="arrow")
            self.title_label.configure(cursor="arrow")
        else:
            self.lock_button.configure(
                text="锁定",
                bg=ACCENT,
                activebackground=ACCENT_HOVER,
                fg="#102219",
                activeforeground="#102219",
            )
            self.status_label.configure(
                text=f"●  {self.mode}",
                bg=BG_PANEL,
                fg=ACCENT,
            )
            self.message_label.configure(
                text=MODE_HINTS[self.mode]
            )
            self.close_button.configure(state="normal", cursor="hand2")
            self.mode_button.configure(state="normal", cursor="hand2")
            self.resize_grip.configure(cursor="size_nw_se")
            self.title_bar.configure(cursor="fleur")
            self.title_label.configure(cursor="fleur")

    def click_through_style_is_set(self) -> bool:
        hwnd = _top_level_handle(self.root)
        style = int(_get_window_long(wintypes.HWND(hwnd), GWL_EXSTYLE))
        return bool(style & WS_EX_TRANSPARENT and style & WS_EX_NOACTIVATE)

    def close(self) -> None:
        if self._closed:
            return
        self._notify_state_changed()
        self._closed = True
        if self._tick_after_id is not None:
            try:
                self.root.after_cancel(self._tick_after_id)
            except tk.TclError:
                pass
            self._tick_after_id = None
        try:
            if self.lock_window.winfo_exists():
                self.lock_window.destroy()
        except (AttributeError, tk.TclError):
            pass
        try:
            if self.ball_window.winfo_exists():
                self.ball_window.destroy()
        except (AttributeError, tk.TclError):
            pass
        try:
            self.root.destroy()
        finally:
            callback = self.on_close
            self.on_close = None
            if callback is not None:
                callback(self)

    def apply_shared_settings(self) -> None:
        if self._closed:
            return
        self._apply_layered_style()

    def run(self) -> None:
        self.root.mainloop()


class DesktopManager:
    def __init__(
        self,
        *,
        tray_enabled: bool = True,
        visible: bool = True,
        create_initial_window: bool = True,
        initial_position: tuple[int, int] | None = None,
        settings_path: Path | None = None,
        state_path: Path | None = None,
        auto_start_store: AutoStartStore | None = None,
        update_client: UpdateClient | None = None,
    ) -> None:
        self.visible = visible
        self._exiting = False
        self._settings_save_error = False
        self._window_save_error = False
        self._auto_start_error: str | None = None
        self._settings_save_after_id: str | None = None
        self._settings_dirty = False
        self._window_save_after_id: str | None = None
        self._window_state_dirty = False
        self._hover_after_id: str | None = None
        self._update_poll_after_id: str | None = None
        self._update_queue: Queue[tuple[str, object, object, bool]] = Queue()
        self._update_busy = False
        self._staged_update: tuple[Path, str, str] | None = None
        self._restart_after_update = False
        self._update_message = f"当前版本 v{APP_VERSION}"
        self.windows: list[OverlayApp] = []
        self.settings_window: tk.Toplevel | None = None

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_TITLE)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        self.settings_store = SettingsStore(settings_path)
        self.update_client = update_client or UpdateClient()
        self.auto_start_store = auto_start_store or AutoStartStore()
        try:
            self.auto_start_store.refresh_frozen_path()
            auto_start_enabled = self.auto_start_store.is_enabled()
        except OSError as error:
            auto_start_enabled = False
            self._auto_start_error = f"无法读取开机启动状态：{error}"
        self.auto_start = tk.BooleanVar(master=self.root, value=auto_start_enabled)
        self.window_store = WindowStateStore(
            state_path if state_path is not None else self.settings_store.path.with_name("windows.json")
        )
        self._window_records = self.window_store.load()
        self._next_instance_number = max(
            (int(record["id"]) for record in self._window_records),
            default=0,
        ) + 1
        saved_settings = self.settings_store.load()
        self.opacity_percent = tk.IntVar(
            master=self.root,
            value=saved_settings["opacity_percent"],
        )
        self.edge_collapse_enabled = tk.BooleanVar(
            master=self.root,
            value=saved_settings["edge_collapse_enabled"],
        )
        self.restore_margin = tk.IntVar(
            master=self.root,
            value=saved_settings["restore_margin"],
        )
        self.no_background = tk.BooleanVar(
            master=self.root,
            value=saved_settings["no_background"],
        )
        self.auto_update = tk.BooleanVar(
            master=self.root,
            value=saved_settings["auto_update"],
        )
        for setting_variable in (
            self.opacity_percent,
            self.edge_collapse_enabled,
            self.restore_margin,
            self.no_background,
            self.auto_update,
        ):
            setting_variable.trace_add("write", self._schedule_settings_save)
        self.no_background.trace_add("write", self._on_no_background_changed)
        # Write defaults on first launch and normalize older or manually edited files.
        self._settings_dirty = True
        self._settings_save_after_id = self.root.after(250, self._save_settings_now)

        self.tray = SystemTrayIcon(
            self.root,
            on_add=self.add_window,
            on_settings=self.open_settings,
            on_update=self._tray_check_updates,
            on_exit=self.exit_app,
            show_icon=tray_enabled,
        )

        if create_initial_window:
            active_records = [
                record for record in self._window_records if record["active"]
            ]
            if initial_position is None and active_records:
                for record in active_records:
                    self._open_window(record)
            else:
                self.add_window(initial_position=initial_position)
        self._hover_after_id = self.root.after(HOVER_POLL_MS, self._poll_hover)
        if self.auto_update.get() and getattr(sys, "frozen", False):
            self.root.after(1500, lambda: self.check_for_updates(manual=False))

    def add_window(
        self,
        initial_position: tuple[int, int] | None = None,
    ) -> OverlayApp:
        saved_state = None
        if initial_position is None:
            saved_state = next(
                (record for record in reversed(self._window_records) if not record["active"]),
                None,
            )
        if saved_state is not None:
            return self._open_window(saved_state)
        if initial_position is None and self.windows:
            previous = self.windows[-1]
            if previous.collapsed and previous._ball_geometry is not None:
                previous_x = previous._ball_geometry[2]
                previous_y = previous._ball_geometry[3]
            else:
                previous_x = previous.root.winfo_x()
                previous_y = previous.root.winfo_y()
            initial_position = previous_x + 36, previous_y + 36

        return self._open_window(None, initial_position=initial_position)

    def _open_window(
        self,
        saved_state: dict[str, object] | None,
        *,
        initial_position: tuple[int, int] | None = None,
    ) -> OverlayApp:
        instance_number = (
            int(saved_state["id"])
            if saved_state is not None
            else self._next_instance_number
        )

        window = OverlayApp(
            visible=self.visible,
            initial_position=initial_position,
            master=self.root,
            on_close=self._on_window_closed,
            opacity_percent=self.opacity_percent,
            edge_collapse_enabled=self.edge_collapse_enabled,
            restore_margin=self.restore_margin,
            no_background=self.no_background,
            instance_number=instance_number,
            saved_state=saved_state,
            on_state_change=self._on_window_state_changed,
        )
        if saved_state is None:
            self._next_instance_number += 1
        self.windows.append(window)
        self._on_window_state_changed(window)
        self._save_window_states_now()
        self._update_instance_count()
        return window

    def _on_window_state_changed(self, window: OverlayApp) -> None:
        if self._exiting:
            return
        snapshot = window.state_snapshot()
        for index, record in enumerate(self._window_records):
            if record["id"] == window.instance_number:
                if record == snapshot:
                    return
                self._window_records[index] = snapshot
                break
        else:
            self._window_records.append(snapshot)
        self._schedule_window_states_save()

    def _schedule_window_states_save(self) -> None:
        self._window_state_dirty = True
        if self._window_save_after_id is not None:
            try:
                self.root.after_cancel(self._window_save_after_id)
            except tk.TclError:
                pass
        self._window_save_after_id = self.root.after(
            250,
            self._save_window_states_now,
        )

    def _save_window_states_now(self) -> None:
        pending_after = self._window_save_after_id
        self._window_save_after_id = None
        if pending_after is not None:
            try:
                self.root.after_cancel(pending_after)
            except tk.TclError:
                pass
        if not self._window_state_dirty:
            return
        try:
            self.window_store.save(self._window_records)
        except OSError:
            self._window_state_dirty = True
            self._window_save_error = True
            self._update_settings_note()
            return
        self._window_state_dirty = False
        self._window_save_error = False
        self._update_settings_note()

    def _on_window_closed(self, window: OverlayApp) -> None:
        if window in self.windows:
            self.windows.remove(window)
        if not self._exiting:
            for index, record in enumerate(self._window_records):
                if record["id"] == window.instance_number:
                    self._window_records.pop(index)
                    record["active"] = False
                    self._window_records.append(record)
                    break
            self._schedule_window_states_save()
            self._save_window_states_now()
        self._update_instance_count()

    def _on_no_background_changed(self, *_trace_arguments: str) -> None:
        self._refresh_backgrounds()

    def _refresh_backgrounds(self) -> None:
        if self._exiting:
            return
        cursor = Point()
        user32.GetCursorPos(ctypes.byref(cursor))
        for window in tuple(self.windows):
            window.update_background_for_hover(cursor.x, cursor.y)

    def _poll_hover(self) -> None:
        self._hover_after_id = None
        if self._exiting:
            return
        self._refresh_backgrounds()
        self._hover_after_id = self.root.after(HOVER_POLL_MS, self._poll_hover)

    def open_settings(self) -> None:
        if self.settings_window is not None and self.settings_window.winfo_exists():
            if self.visible:
                self.settings_window.deiconify()
                self.settings_window.attributes("-topmost", True)
                self.settings_window.lift()
                self.settings_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        self.settings_window = window
        if not self.visible:
            window.withdraw()
        window.title("DesktopTools 设置")
        window.configure(bg=BG_BODY)
        window.resizable(False, False)
        window.attributes("-topmost", True)
        try:
            window.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        window.protocol("WM_DELETE_WINDOW", self.close_settings)

        tk.Label(
            window,
            text="DesktopTools 设置",
            bg=BG_BODY,
            fg=TEXT,
            font=("Microsoft YaHei UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x", padx=22, pady=(20, 6))

        self.instance_count_label = tk.Label(
            window,
            text="",
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        )
        self.instance_count_label.pack(fill="x", padx=22, pady=(0, 14))

        opacity_row = tk.Frame(window, bg=BG_BODY)
        opacity_row.pack(fill="x", padx=22)
        tk.Label(
            opacity_row,
            text="所有自由窗口的透明度",
            bg=BG_BODY,
            fg=TEXT,
            font=("Microsoft YaHei UI", 10),
        ).pack(side="left")
        self.manager_opacity_value = tk.Label(
            opacity_row,
            text=f"{self.opacity_percent.get()}%",
            bg=BG_BODY,
            fg=ACCENT,
            font=("Segoe UI", 10, "bold"),
        )
        self.manager_opacity_value.pack(side="right")

        tk.Scale(
            window,
            from_=55,
            to=100,
            orient="horizontal",
            variable=self.opacity_percent,
            command=self._on_opacity_changed,
            bg=BG_BODY,
            fg=TEXT_MUTED,
            activebackground=ACCENT,
            troughcolor=BG_PANEL,
            highlightthickness=0,
            bd=0,
            showvalue=False,
            length=326,
        ).pack(fill="x", padx=20, pady=(2, 12))

        tk.Checkbutton(
            window,
            text="拖到屏幕边缘时收起为小球",
            variable=self.edge_collapse_enabled,
            bg=BG_BODY,
            fg=TEXT,
            activebackground=BG_BODY,
            activeforeground=TEXT,
            selectcolor=BG_PANEL,
            font=("Microsoft YaHei UI", 10),
            anchor="w",
            highlightthickness=0,
        ).pack(fill="x", padx=18, pady=(0, 12))

        tk.Checkbutton(
            window,
            text="无背景（鼠标移入时才显示背景和按钮）",
            variable=self.no_background,
            bg=BG_BODY,
            fg=TEXT,
            activebackground=BG_BODY,
            activeforeground=TEXT,
            selectcolor=BG_PANEL,
            font=("Microsoft YaHei UI", 10),
            anchor="w",
            highlightthickness=0,
        ).pack(fill="x", padx=18, pady=(0, 12))

        tk.Checkbutton(
            window,
            text="开机启动（当前 Windows 用户）",
            variable=self.auto_start,
            command=self._on_auto_start_changed,
            bg=BG_BODY,
            fg=TEXT,
            activebackground=BG_BODY,
            activeforeground=TEXT,
            selectcolor=BG_PANEL,
            font=("Microsoft YaHei UI", 10),
            anchor="w",
            highlightthickness=0,
        ).pack(fill="x", padx=18, pady=(0, 12))

        tk.Checkbutton(
            window,
            text="自动更新（启动时检查，退出后安装）",
            variable=self.auto_update,
            command=self._on_auto_update_changed,
            bg=BG_BODY,
            fg=TEXT,
            activebackground=BG_BODY,
            activeforeground=TEXT,
            selectcolor=BG_PANEL,
            font=("Microsoft YaHei UI", 10),
            anchor="w",
            highlightthickness=0,
        ).pack(fill="x", padx=18, pady=(0, 12))

        margin_row = tk.Frame(window, bg=BG_BODY)
        margin_row.pack(fill="x", padx=22)
        tk.Label(
            margin_row,
            text="展开后距停靠边",
            bg=BG_BODY,
            fg=TEXT,
            font=("Microsoft YaHei UI", 10),
        ).pack(side="left")
        tk.Label(
            margin_row,
            text="px",
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Segoe UI", 9),
        ).pack(side="right", padx=(5, 0))
        tk.Spinbox(
            margin_row,
            from_=0,
            to=80,
            textvariable=self.restore_margin,
            width=5,
            justify="center",
            bg=BG_PANEL,
            fg=TEXT,
            buttonbackground=BG_TITLE,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 10),
        ).pack(side="right")

        self.settings_note_label = tk.Label(
            window,
            text="",
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 8),
            anchor="w",
            justify="left",
            wraplength=350,
        )
        self.settings_note_label.pack(fill="x", padx=22, pady=(16, 12))
        self._update_settings_note()

        self.update_status_label = tk.Label(
            window,
            text=self._update_message,
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 8),
            anchor="w",
            justify="left",
            wraplength=350,
        )
        self.update_status_label.pack(fill="x", padx=22, pady=(0, 12))

        actions = tk.Frame(window, bg=BG_BODY)
        actions.pack(fill="x", padx=22, pady=(0, 18))
        tk.Button(
            actions,
            text="恢复默认",
            command=self.reset_settings,
            bg=BG_PANEL,
            fg=TEXT,
            activebackground="#3A414E",
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            font=("Microsoft YaHei UI", 9),
            padx=14,
            pady=6,
            cursor="hand2",
        ).pack(side="left")
        self.update_button = tk.Button(
            actions,
            text="检查更新",
            command=lambda: self.check_for_updates(manual=True),
            bg=BG_PANEL,
            fg=TEXT,
            activebackground="#3A414E",
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            font=("Microsoft YaHei UI", 9),
            padx=14,
            pady=6,
            cursor="hand2",
        )
        self.update_button.pack(side="left", padx=(8, 0))
        tk.Button(
            actions,
            text="关闭",
            command=self.close_settings,
            bg=ACCENT,
            fg="#102219",
            activebackground=ACCENT_HOVER,
            activeforeground="#102219",
            relief="flat",
            bd=0,
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=18,
            pady=6,
            cursor="hand2",
        ).pack(side="right")

        settings_width = 450
        settings_height = 590
        cursor = Point()
        user32.GetCursorPos(ctypes.byref(cursor))
        _monitor_area, work_area = _monitor_areas_at(cursor.x, cursor.y)
        left, top, right, bottom = work_area
        x = left + max(0, (right - left - settings_width) // 2)
        y = top + max(0, (bottom - top - settings_height) // 2)
        _set_absolute_geometry(
            window,
            width=settings_width,
            height=settings_height,
            x=x,
            y=y,
        )
        self._update_instance_count()
        if self.visible:
            window.deiconify()
            window.lift()
            window.focus_force()

    def _on_opacity_changed(self, value: str) -> None:
        percent = _clamp(round(float(value)), 55, 100)
        self.opacity_percent.set(percent)
        if hasattr(self, "manager_opacity_value"):
            self.manager_opacity_value.configure(text=f"{percent}%")
        for window in tuple(self.windows):
            window.apply_shared_settings()

    def _on_auto_start_changed(self) -> None:
        enabled = bool(self.auto_start.get())
        try:
            self.auto_start_store.set_enabled(enabled)
        except OSError as error:
            self.auto_start.set(not enabled)
            self._auto_start_error = f"开机启动设置失败：{error}"
        else:
            self._auto_start_error = None
        self._update_settings_note()

    def _on_auto_update_changed(self) -> None:
        if self.auto_update.get():
            self.check_for_updates(manual=False)

    def _tray_check_updates(self) -> None:
        self.open_settings()
        self.check_for_updates(manual=True)

    def _set_update_message(self, message: str, *, error: bool = False) -> None:
        self._update_message = message
        if not hasattr(self, "update_status_label"):
            return
        try:
            self.update_status_label.configure(
                text=message,
                fg=CLOSE_HOVER if error else TEXT_MUTED,
            )
        except tk.TclError:
            pass

    def check_for_updates(self, *, manual: bool) -> None:
        if self._exiting or (not manual and not self.auto_update.get()):
            return
        if not getattr(sys, "frozen", False):
            self._set_update_message(
                f"当前版本 v{APP_VERSION}；更新功能仅适用于打包后的 EXE。"
            )
            return
        if self._update_busy:
            self._set_update_message("正在检查或下载更新，请稍候……")
            return
        self._update_busy = True
        self._set_update_message("正在检查 GitHub 上的最新版本……")

        def worker() -> None:
            try:
                latest = self.update_client.latest()
                if latest is None:
                    self._update_queue.put(("unpublished", None, None, manual))
                    return
                if _version_numbers(latest["version"]) <= _version_numbers(APP_VERSION):
                    self._update_queue.put(("current", latest, None, manual))
                    return
                self._update_queue.put(("downloading", latest, None, manual))
                staged = self.update_client.download(latest)
                self._update_queue.put(("ready", latest, staged, manual))
            except Exception as error:
                self._update_queue.put(("error", str(error), None, manual))

        threading.Thread(target=worker, daemon=True, name="DesktopToolsUpdate").start()
        if self._update_poll_after_id is None:
            self._update_poll_after_id = self.root.after(100, self._poll_update_queue)

    def _poll_update_queue(self) -> None:
        self._update_poll_after_id = None
        if self._exiting:
            return
        while True:
            try:
                kind, detail, staged, manual = self._update_queue.get_nowait()
            except Empty:
                break
            if kind == "downloading":
                self._set_update_message(f"发现 v{detail['version']}，正在下载并校验……")
                continue
            self._update_busy = False
            if kind == "unpublished":
                self._set_update_message("GitHub 尚未发布更新索引，当前无法检查新版本。")
            elif kind == "current":
                self._set_update_message(f"当前已是最新版本 v{APP_VERSION}。")
            elif kind == "error":
                self._set_update_message(f"检查更新失败：{detail}", error=True)
            elif kind == "ready":
                version = detail["version"]
                self._staged_update = (staged, detail["sha256"], version)
                self._set_update_message(
                    f"新版 v{version} 已下载并校验；退出程序后会自动安装。"
                )
                if manual:
                    self.open_settings()
                    if messagebox.askyesno(
                        "DesktopTools 更新",
                        f"新版 v{version} 已准备好。现在退出并安装，然后重新启动吗？",
                        parent=self.settings_window,
                    ):
                        self._restart_after_update = True
                        self.exit_app()
                        return
        if self._update_busy:
            self._update_poll_after_id = self.root.after(100, self._poll_update_queue)

    def _update_settings_note(self) -> None:
        if not hasattr(self, "settings_note_label"):
            return
        if self._auto_start_error:
            message = self._auto_start_error
        elif self._window_save_error:
            message = "窗口存档暂时无法写入磁盘；退出前会再次尝试。"
        elif self._settings_save_error:
            message = "设置暂时无法写入磁盘；退出前会再次尝试。"
        else:
            message = "设置与窗口存档会自动保存到本机。"
        try:
            self.settings_note_label.configure(
                text=message,
                fg=CLOSE_HOVER if (
                    self._auto_start_error
                    or self._window_save_error
                    or self._settings_save_error
                ) else TEXT_MUTED,
            )
        except tk.TclError:
            pass

    def _schedule_settings_save(self, *_trace_arguments: str) -> None:
        if self._exiting:
            return
        self._settings_dirty = True
        if self._settings_save_after_id is not None:
            try:
                self.root.after_cancel(self._settings_save_after_id)
            except tk.TclError:
                pass
        self._settings_save_after_id = self.root.after(
            250,
            self._save_settings_now,
        )

    def _current_settings(self) -> dict[str, int | bool]:
        try:
            opacity = int(self.opacity_percent.get())
        except (tk.TclError, ValueError):
            opacity = int(SettingsStore.DEFAULTS["opacity_percent"])
        try:
            restore_margin = int(self.restore_margin.get())
        except (tk.TclError, ValueError):
            restore_margin = int(SettingsStore.DEFAULTS["restore_margin"])
        try:
            edge_collapse = bool(self.edge_collapse_enabled.get())
        except tk.TclError:
            edge_collapse = bool(SettingsStore.DEFAULTS["edge_collapse_enabled"])
        try:
            no_background = bool(self.no_background.get())
        except tk.TclError:
            no_background = bool(SettingsStore.DEFAULTS["no_background"])
        try:
            auto_update = bool(self.auto_update.get())
        except tk.TclError:
            auto_update = bool(SettingsStore.DEFAULTS["auto_update"])
        return {
            "opacity_percent": _clamp(opacity, 55, 100),
            "edge_collapse_enabled": edge_collapse,
            "restore_margin": _clamp(restore_margin, 0, 80),
            "no_background": no_background,
            "auto_update": auto_update,
        }

    def _save_settings_now(self) -> None:
        pending_after = self._settings_save_after_id
        self._settings_save_after_id = None
        if pending_after is not None:
            try:
                self.root.after_cancel(pending_after)
            except tk.TclError:
                pass
        if not self._settings_dirty:
            return
        try:
            self.settings_store.save(self._current_settings())
        except OSError:
            self._settings_dirty = True
            self._settings_save_error = True
            self._update_settings_note()
            return
        self._settings_dirty = False
        self._settings_save_error = False
        self._update_settings_note()

    def reset_settings(self) -> None:
        self.opacity_percent.set(86)
        self.edge_collapse_enabled.set(True)
        self.restore_margin.set(RESTORE_MARGIN)
        self.no_background.set(False)
        self.auto_update.set(False)
        if self.auto_start.get():
            self.auto_start.set(False)
            self._on_auto_start_changed()
        self._on_opacity_changed("86")

    def close_settings(self) -> None:
        self._save_settings_now()
        if self.settings_window is None:
            return
        try:
            if self.settings_window.winfo_exists():
                self.settings_window.destroy()
        except tk.TclError:
            pass
        self.settings_window = None

    def _update_instance_count(self) -> None:
        if hasattr(self, "instance_count_label"):
            try:
                self.instance_count_label.configure(
                    text=f"当前自由窗口实例：{len(self.windows)} 个"
                )
            except tk.TclError:
                pass

    def exit_app(self) -> None:
        if self._exiting:
            return
        for window in tuple(self.windows):
            self._on_window_state_changed(window)
        self._save_window_states_now()
        self._exiting = True
        self.close_settings()
        if self._update_poll_after_id is not None:
            try:
                self.root.after_cancel(self._update_poll_after_id)
            except tk.TclError:
                pass
            self._update_poll_after_id = None
        if self._hover_after_id is not None:
            try:
                self.root.after_cancel(self._hover_after_id)
            except tk.TclError:
                pass
            self._hover_after_id = None
        for window in tuple(self.windows):
            window.on_close = None
            window.on_state_change = None
            window.close()
        self.windows.clear()
        self.tray.cleanup()
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        if self._staged_update is not None and getattr(sys, "frozen", False):
            staged, digest, _version = self._staged_update
            try:
                subprocess.Popen(
                    [
                        str(staged),
                        "--apply-update",
                        str(Path(sys.executable).resolve()),
                        digest,
                        "restart" if self._restart_after_update else "no-restart",
                    ],
                    cwd=staged.parent,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError:
                # Keep the verified staged package for the next manual attempt.
                pass

    def run(self) -> None:
        self.root.mainloop()


def _self_test() -> None:
    class MemoryAutoStartStore(AutoStartStore):
        def __init__(self) -> None:
            self.saved_command: str | None = None
            self.fail_next = False

        def get_command(self) -> str | None:
            return self.saved_command

        def set_enabled(self, enabled: bool) -> None:
            if self.fail_next:
                self.fail_next = False
                raise PermissionError("test registry denial")
            self.saved_command = self.command() if enabled else None

        def refresh_frozen_path(self) -> None:
            pass

    def outlined_text(window: OverlayApp) -> list[str]:
        canvas = window.outlined_canvas
        fill_items = canvas.find_withtag("outlined-fill")
        stroke_items = canvas.find_withtag("outlined-stroke")
        assert fill_items and stroke_items, "outlined foreground was not drawn"
        assert all(
            canvas.itemcget(item, "fill") == OUTLINED_TEXT_FILL
            for item in fill_items
        )
        assert all(
            canvas.itemcget(item, "fill") == OUTLINED_TEXT_STROKE
            for item in stroke_items
        )
        return [canvas.itemcget(item, "text") for item in fill_items]

    app = OverlayApp(visible=False)
    app.root.update()
    assert _position_from_arguments(["--position", "-120", "80"]) == (-120, 80)
    assert app.mode == "便签"
    app.note_text.insert("1.0", "临时想法")
    app.mode_menu.invoke(1)
    assert app.mode == "待办", "mode menu did not switch the window purpose"
    app.todo_input.insert(0, "检查切换")
    app._add_todo()
    assert app.todo_items == [("检查切换", False)]
    app.todo_list.selection_set(0)
    app._toggle_todo()
    assert app.todo_items == [("检查切换", True)]
    app.set_mode("倒计时")
    app.timer_minutes.set(2)
    app._reset_timer()
    assert app.timer_label.cget("text") == "02:00"
    app._toggle_timer()
    assert app._timer_deadline is not None
    app._toggle_timer()
    assert app._timer_deadline is None
    app.set_mode("时钟")
    assert app.clock_time_label.cget("text")
    app.set_mode("便签")
    assert app.note_text.get("1.0", "end-1c") == "临时想法"
    assert app.todo_items == [("检查切换", True)]

    _set_absolute_geometry(
        app.root,
        width=MIN_WIDTH,
        height=MIN_HEIGHT,
        x=-160,
        y=-120,
    )
    app.root.update_idletasks()
    native_rect = Rect()
    root_handle = _top_level_handle(app.root)
    assert user32.GetWindowRect(
        wintypes.HWND(root_handle),
        ctypes.byref(native_rect),
    ), "native window rectangle is unavailable"
    assert native_rect.left == -160, "negative X coordinate was mirrored"
    assert native_rect.top == -120, "negative Y coordinate was mirrored"

    app.set_locked(True)
    app.root.update()
    assert app.click_through_style_is_set(), "click-through style was not enabled"
    assert app.mode_button.cget("state") == "disabled"
    app.set_locked(False)
    app.root.update()
    assert not app.click_through_style_is_set(), "click-through style was not disabled"
    assert app.mode_button.cget("state") == "normal"

    app.no_background.set(True)
    app.update_background_for_hover(-100000, -100000)
    assert app._background_hidden, "background was not hidden away from the cursor"
    assert app.title_bar.cget("bg") == TRANSPARENT_KEY
    assert app.title_label.cget("fg") == TRANSPARENT_KEY
    assert app.title_label.cget("text") == ""
    assert app.drag_grip.cget("text") == ""
    assert app.status_label.cget("bg") == TRANSPARENT_KEY
    assert app.status_label.cget("fg") == TRANSPARENT_KEY
    assert app.status_label.winfo_manager() == ""
    assert app.message_label.cget("fg") == TEXT
    assert app.message_label.winfo_manager() == ""
    assert app.close_button.cget("fg") == TRANSPARENT_KEY
    assert app.close_button.cget("text") == ""
    assert app.lock_button.cget("fg") == TRANSPARENT_KEY
    assert app.mode_button.cget("fg") == TRANSPARENT_KEY
    assert app.mode_button.cget("text") == ""
    assert app.note_text.cget("bg") == TRANSPARENT_KEY
    assert app.note_text.winfo_manager() == ""
    assert app.outlined_canvas.winfo_manager() == "place"
    assert "临时想法" in outlined_text(app)
    assert app.note_text.get("1.0", "end-1c") == "临时想法"
    app.note_text.delete("1.0", "end")
    app.root.update()
    assert "空便签" in outlined_text(app)
    app.note_text.insert("1.0", "再次写入")
    app.root.update()
    assert "再次写入" in outlined_text(app)
    app.set_mode("待办")
    assert app.todo_entry_row.winfo_manager() == ""
    assert app.todo_actions.winfo_manager() == ""
    assert app.todo_list.winfo_manager() == ""
    assert "☑  检查切换" in outlined_text(app)
    app.set_mode("倒计时")
    assert app.timer_actions.winfo_manager() == ""
    assert app.timer_label.winfo_manager() == ""
    assert "02:00" in outlined_text(app)
    app.set_mode("时钟")
    assert app.clock_time_label.cget("bg") == TRANSPARENT_KEY
    assert app.clock_time_label.winfo_manager() == ""
    assert app.clock_time_label.cget("text") in outlined_text(app)
    app.set_mode("便签")
    layered_key = wintypes.DWORD()
    layered_alpha = ctypes.c_ubyte()
    layered_flags = wintypes.DWORD()
    assert user32.GetLayeredWindowAttributes(
        wintypes.HWND(root_handle),
        ctypes.byref(layered_key),
        ctypes.byref(layered_alpha),
        ctypes.byref(layered_flags),
    ), "layered window attributes are unavailable"
    assert layered_flags.value & LWA_COLORKEY, "background color key was not applied"
    assert layered_key.value == _colorref(TRANSPARENT_KEY)
    assert layered_alpha.value == 255, "foreground was dimmed without a background"

    app.update_background_for_hover(
        app.root.winfo_x() + 5,
        app.root.winfo_y() + 5,
    )
    assert not app._background_hidden, "background was not restored on hover"
    assert app.title_bar.cget("bg") == BG_TITLE
    assert app.title_label.cget("fg") == TEXT
    assert app.title_label.cget("text") == "自由窗口 #1"
    assert app.mode_button.cget("text") == "便签 ▾"
    assert app.status_label.cget("bg") == BG_PANEL
    assert app.status_label.cget("fg") == ACCENT
    assert app.status_label.winfo_manager() == "pack"
    assert app.message_label.winfo_manager() == "pack"
    assert app.close_button.cget("fg") == TEXT
    assert app.lock_button.cget("fg") == "#102219"
    assert app.note_text.cget("fg") == TEXT
    assert app.note_text.winfo_manager() == "pack"
    assert app.outlined_canvas.winfo_manager() == ""
    assert app.todo_entry_row.winfo_manager() == "pack"
    assert app.timer_actions.winfo_manager() == "pack"
    layered_flags = wintypes.DWORD()
    assert user32.GetLayeredWindowAttributes(
        wintypes.HWND(root_handle),
        ctypes.byref(layered_key),
        ctypes.byref(layered_alpha),
        ctypes.byref(layered_flags),
    )
    assert not layered_flags.value & LWA_COLORKEY, "background color key was not cleared"
    app.no_background.set(False)
    app.root.update()

    cursor = Point()
    user32.GetCursorPos(ctypes.byref(cursor))
    monitor_area, _work_area = _monitor_areas_at(cursor.x, cursor.y)
    left, top, right, bottom = monitor_area
    dock_target = app._ball_target_at_edge(right - 1, top + (bottom - top) // 2)
    assert dock_target is not None, "display edge was not detected"
    ball_geometry, dock_edge = dock_target
    assert dock_edge == "right", "right display edge was not selected"

    app._collapse_to_ball(ball_geometry, dock_edge)
    deadline = time.monotonic() + 2
    while app.animating and time.monotonic() < deadline:
        app.root.update()
        time.sleep(0.01)
    assert app.collapsed and not app.animating, "window did not collapse to ball"
    assert app._ball_geometry == ball_geometry, "collapsed ball geometry is incorrect"

    app._restore_from_ball()
    deadline = time.monotonic() + 2
    while app.animating and time.monotonic() < deadline:
        app.root.update()
        time.sleep(0.01)
    assert not app.collapsed and not app.animating, "window did not restore from ball"
    assert app._restore_geometry is not None
    restored_width, restored_height, restored_x, restored_y = app._restore_geometry
    _, work_area = _monitor_areas_at(
        ball_geometry[2] + BALL_SIZE // 2,
        ball_geometry[3] + BALL_SIZE // 2,
    )
    work_left, work_top, work_right, work_bottom = work_area
    assert restored_x + restored_width == work_right - RESTORE_MARGIN
    assert restored_x >= work_left + RESTORE_MARGIN
    assert restored_y >= work_top + RESTORE_MARGIN
    assert restored_y + restored_height <= work_bottom - RESTORE_MARGIN
    app.close()

    visible_lock_app = OverlayApp(visible=True)
    visible_lock_app.note_text.insert("1.0", "锁定后保留内容")
    visible_lock_app.root.update()
    original_position = (
        visible_lock_app.root.winfo_x(),
        visible_lock_app.root.winfo_y(),
    )
    visible_lock_app.set_locked(True)
    visible_lock_app.root.update()
    assert visible_lock_app.root.state() == "normal"
    assert visible_lock_app._background_hidden
    assert visible_lock_app.click_through_style_is_set()
    assert visible_lock_app.outlined_canvas.winfo_ismapped()
    assert not visible_lock_app.note_text.winfo_ismapped()
    assert visible_lock_app.note_text.get("1.0", "end-1c") == "锁定后保留内容"
    assert "锁定后保留内容" in outlined_text(visible_lock_app)
    assert visible_lock_app.title_label.cget("text") == ""
    assert visible_lock_app.lock_window.state() == "normal"
    assert visible_lock_app.unlock_canvas.winfo_manager() == "pack"
    assert visible_lock_app.lock_button.winfo_manager() == ""
    assert visible_lock_app.lock_window.winfo_width() == UNLOCK_ICON_SIZE
    assert visible_lock_app.lock_window.winfo_height() == UNLOCK_ICON_SIZE
    visible_lock_app.update_background_for_hover(*original_position)
    visible_lock_app.root.update()
    assert visible_lock_app.root.state() == "normal"
    assert visible_lock_app._background_hidden, (
        "hover unexpectedly revealed locked window chrome"
    )
    assert visible_lock_app.title_label.cget("text") == ""
    visible_lock_app.note_text.delete("1.0", "end")
    visible_lock_app.root.update()
    assert "空便签" in outlined_text(visible_lock_app), (
        "empty locked note became invisible"
    )
    visible_lock_app.unlock_canvas.event_generate(
        "<ButtonRelease-1>",
        x=UNLOCK_ICON_SIZE // 2,
        y=UNLOCK_ICON_SIZE // 2,
    )
    visible_lock_app.root.update()
    assert visible_lock_app.root.state() == "normal"
    assert visible_lock_app.lock_button.winfo_manager() == "pack"
    assert not visible_lock_app.click_through_style_is_set()
    assert (
        visible_lock_app.root.winfo_x(),
        visible_lock_app.root.winfo_y(),
    ) == original_position
    visible_lock_app.no_background.set(True)
    visible_lock_app.set_locked(True)
    visible_lock_app.root.update()
    assert visible_lock_app.root.state() == "normal"
    assert visible_lock_app._background_hidden
    assert "空便签" in outlined_text(visible_lock_app)
    visible_lock_app.set_locked(False)
    visible_lock_app.root.update()
    assert visible_lock_app.root.state() == "normal"
    visible_lock_app.close()

    temporary_settings_directory = tempfile.TemporaryDirectory()
    test_settings_path = (
        Path(temporary_settings_directory.name) / "DesktopTools" / "settings.json"
    )
    fake_package = b"MZ" + b"desktop-tools-update-test" * 128
    fake_manifest = {
        "version": "2.0.0",
        "sha256": hashlib.sha256(fake_package).hexdigest(),
        "size": len(fake_package),
    }

    def fake_release_opener(request: urllib.request.Request, *, timeout: int) -> io.BytesIO:
        del timeout
        return io.BytesIO(
            json.dumps(fake_manifest).encode("utf-8")
            if request.full_url.endswith("update.json")
            else fake_package
        )

    release_client = UpdateClient(
        directory=Path(temporary_settings_directory.name) / "updates",
        opener=fake_release_opener,
    )
    assert _version_numbers("2.1.3") > _version_numbers(APP_VERSION)
    assert release_client.latest() == fake_manifest
    staged_test_package = release_client.download(fake_manifest)
    assert staged_test_package.read_bytes() == fake_package
    assert release_client.download(fake_manifest) == staged_test_package

    def corrupt_package_opener(
        request: urllib.request.Request, *, timeout: int
    ) -> io.BytesIO:
        del timeout
        return io.BytesIO(
            json.dumps(fake_manifest).encode("utf-8")
            if request.full_url.endswith("update.json")
            else b"MZ" + b"corrupt"
        )

    corrupt_client = UpdateClient(
        directory=Path(temporary_settings_directory.name) / "bad-updates",
        opener=corrupt_package_opener,
    )
    try:
        corrupt_client.download(fake_manifest)
        raise AssertionError("corrupt update was accepted")
    except UpdateError:
        pass

    def current_manifest_opener(
        request: urllib.request.Request, *, timeout: int
    ) -> io.BytesIO:
        del request, timeout
        return io.BytesIO(
            json.dumps({**fake_manifest, "version": APP_VERSION}).encode("utf-8")
        )

    current_client = UpdateClient(
        directory=Path(temporary_settings_directory.name) / "current-updates",
        opener=current_manifest_opener,
    )
    memory_auto_start = MemoryAutoStartStore()
    assert AutoStartStore().command().startswith('"')
    manager = DesktopManager(
        tray_enabled=True,
        visible=True,
        create_initial_window=False,
        settings_path=test_settings_path,
        auto_start_store=memory_auto_start,
        update_client=current_client,
    )
    assert manager.tray.hwnd, "tray message window was not created"
    assert all(manager.tray._menu_bitmaps.values()), "tray menu icons were not created"
    test_menu = user32.CreatePopupMenu()
    assert test_menu, "test popup menu was not created"
    try:
        user32.AppendMenuW(test_menu, MF_STRING, TRAY_COMMAND_ADD, "添加自由窗口")
        user32.AppendMenuW(test_menu, MF_STRING, TRAY_COMMAND_SETTINGS, "设置")
        user32.AppendMenuW(test_menu, MF_STRING, TRAY_COMMAND_UPDATE, "检查更新")
        user32.AppendMenuW(test_menu, MF_STRING, TRAY_COMMAND_EXIT, "退出")
        assert manager.tray._apply_menu_bitmaps(test_menu), (
            "tray menu icons were not attached"
        )
    finally:
        user32.DestroyMenu(test_menu)
    manager.tray.dispatch_command_for_test(TRAY_COMMAND_ADD)
    deadline = time.monotonic() + 1
    while len(manager.windows) < 1 and time.monotonic() < deadline:
        manager.root.update()
        time.sleep(0.01)
    manager.tray.dispatch_command_for_test(TRAY_COMMAND_ADD)
    deadline = time.monotonic() + 1
    while len(manager.windows) < 2 and time.monotonic() < deadline:
        manager.root.update()
        time.sleep(0.01)
    assert len(manager.windows) == 2, "manager did not create two instances"
    first_window, second_window = manager.windows
    first_window.note_text.insert("1.0", "第一扇便签")
    first_window.set_mode("待办")
    first_window.todo_input.insert(0, "只属于第一个窗口")
    first_window._add_todo()
    first_window.todo_list.selection_set(0)
    first_window._toggle_todo()
    first_window.timer_minutes.set(7)
    second_window.note_text.insert("1.0", "第二扇便签")
    _, test_work_area = _monitor_areas_at(
        first_window.root.winfo_x(), first_window.root.winfo_y()
    )
    test_x, test_y = test_work_area[0] + 80, test_work_area[1] + 80
    _set_absolute_geometry(
        first_window.root,
        width=470,
        height=310,
        x=test_x,
        y=test_y,
    )
    manager.root.update()
    first_window._notify_state_changed()
    state_path = test_settings_path.with_name("windows.json")
    deadline = time.monotonic() + 1
    while manager._window_state_dirty and time.monotonic() < deadline:
        manager.root.update()
        time.sleep(0.01)
    assert not manager._window_state_dirty, "window edits were not saved automatically"
    saved_windows = json.loads(state_path.read_text(encoding="utf-8"))["windows"]
    assert len(saved_windows) == 2
    assert saved_windows[0]["mode"] == "待办"
    assert saved_windows[0]["geometry"] == [470, 310, test_x, test_y], saved_windows[0]["geometry"]
    assert saved_windows[0]["note"] == "第一扇便签"
    assert saved_windows[0]["todos"] == [
        {"text": "只属于第一个窗口", "done": True}
    ]
    assert saved_windows[0]["timer_minutes"] == 7
    assert saved_windows[1]["note"] == "第二扇便签"
    assert not any(record["locked"] for record in saved_windows)
    legacy_state = dict(saved_windows[0])
    del legacy_state["locked"]
    legacy_path = test_settings_path.with_name("legacy-windows.json")
    legacy_path.write_text(
        json.dumps({"version": 1, "windows": [legacy_state]}),
        encoding="utf-8",
    )
    assert WindowStateStore(legacy_path).load()[0]["locked"] is False
    assert second_window.mode == "便签"
    assert not second_window.todo_items
    manager.tray.dispatch_command_for_test(TRAY_COMMAND_SETTINGS)
    deadline = time.monotonic() + 1
    while manager.settings_window is None and time.monotonic() < deadline:
        manager.root.update()
        time.sleep(0.01)
    assert manager.settings_window is not None
    manager.root.update_idletasks()
    assert manager.settings_window.winfo_reqwidth() <= 450, (
        manager.settings_window.winfo_reqwidth()
    )
    assert manager.settings_window.winfo_reqheight() <= 590, (
        f"settings controls do not fit: {manager.settings_window.winfo_reqheight()}"
    )
    assert manager.update_button.cget("text") == "检查更新"
    update_controls = [
        child
        for child in manager.settings_window.winfo_children()
        if isinstance(child, tk.Checkbutton)
        and child.cget("text").startswith("自动更新")
    ]
    assert len(update_controls) == 1
    assert manager.auto_update.get() is False
    manager.tray.dispatch_command_for_test(TRAY_COMMAND_UPDATE)
    deadline = time.monotonic() + 2
    while (
        "最新版本" not in manager._update_message
        and "仅适用于" not in manager._update_message
        and time.monotonic() < deadline
    ):
        manager.root.update()
        time.sleep(0.01)
    assert "最新版本" in manager._update_message or "仅适用于" in manager._update_message
    assert manager.auto_start.get() is False
    startup_controls = [
        child
        for child in manager.settings_window.winfo_children()
        if isinstance(child, tk.Checkbutton)
        and child.cget("text").startswith("开机启动")
    ]
    assert len(startup_controls) == 1
    memory_auto_start.fail_next = True
    startup_controls[0].invoke()
    assert manager.auto_start.get() is False
    assert memory_auto_start.saved_command is None
    startup_controls[0].invoke()
    assert manager.auto_start.get() is True
    assert memory_auto_start.saved_command == memory_auto_start.command()
    manager._on_opacity_changed("73")
    assert abs(float(first_window.root.attributes("-alpha")) - 0.73) < 0.01
    assert abs(float(second_window.root.attributes("-alpha")) - 0.73) < 0.01
    manager.reset_settings()
    assert manager.opacity_percent.get() == 86
    assert manager.no_background.get() is False
    assert manager.auto_update.get() is False
    assert manager.auto_start.get() is False
    assert memory_auto_start.saved_command is None
    manager.auto_start.set(True)
    manager._on_auto_start_changed()
    manager.opacity_percent.set(77)
    manager.edge_collapse_enabled.set(False)
    manager.restore_margin.set(17)
    manager.no_background.set(True)
    manager.auto_update.set(True)
    assert first_window._background_hidden, "no-background state was not shared"
    manager._save_settings_now()
    saved_settings = json.loads(test_settings_path.read_text(encoding="utf-8"))
    assert saved_settings["opacity_percent"] == 77
    assert saved_settings["edge_collapse_enabled"] is False
    assert saved_settings["restore_margin"] == 17
    assert saved_settings["no_background"] is True
    assert saved_settings["auto_update"] is True
    manager.close_settings()
    second_window.set_locked(True)
    manager.root.update()
    assert second_window.click_through_style_is_set()
    assert second_window.unlock_canvas.winfo_ismapped()
    manager._save_window_states_now()
    saved_windows = json.loads(state_path.read_text(encoding="utf-8"))["windows"]
    assert next(
        record for record in saved_windows
        if record["id"] == second_window.instance_number
    )["locked"] is True
    second_window.close()
    assert len(manager.windows) == 1, "closing one instance stopped the manager"
    first_window.close()
    assert len(manager.windows) == 0, "closed instance remained registered"
    assert manager.root.winfo_exists(), "manager stopped with the last instance"
    saved_windows = json.loads(state_path.read_text(encoding="utf-8"))["windows"]
    assert not any(record["active"] for record in saved_windows)
    revived_first = manager.add_window()
    revived_second = manager.add_window()
    assert revived_second.instance_number == second_window.instance_number
    assert revived_second.note_text.get("1.0", "end-1c") == "第二扇便签"
    assert revived_second.locked
    assert revived_second.click_through_style_is_set()
    assert revived_second.unlock_canvas.winfo_ismapped()
    revived_second.unlock_canvas.event_generate(
        "<ButtonRelease-1>",
        x=UNLOCK_ICON_SIZE // 2,
        y=UNLOCK_ICON_SIZE // 2,
    )
    manager.root.update()
    assert not revived_second.locked
    assert not revived_second.click_through_style_is_set()
    manager._save_window_states_now()
    saved_windows = json.loads(state_path.read_text(encoding="utf-8"))["windows"]
    assert next(
        record for record in saved_windows
        if record["id"] == second_window.instance_number
    )["locked"] is False
    revived_second.set_locked(True)
    assert revived_first.instance_number == first_window.instance_number
    assert revived_first.mode == "待办"
    assert revived_first.note_text.get("1.0", "end-1c") == "第一扇便签"
    assert revived_first.todo_items == [("只属于第一个窗口", True)]
    assert revived_first.timer_minutes.get() == 7
    assert _native_window_geometry(revived_first.root) == (
        470, 310, test_x, test_y
    ), _native_window_geometry(revived_first.root)
    test_ball, test_edge = revived_first._ball_target_at_edge(
        test_work_area[2] - 1, test_work_area[1] + 150
    )
    revived_first._collapse_to_ball(test_ball, test_edge)
    deadline = time.monotonic() + 2
    while revived_first.animating and time.monotonic() < deadline:
        manager.root.update()
        time.sleep(0.01)
    assert revived_first.collapsed
    manager.open_settings()
    assert manager.settings_window is not None
    manager.exit_app()

    reloaded_manager = DesktopManager(
        tray_enabled=False,
        visible=True,
        create_initial_window=True,
        settings_path=test_settings_path,
        auto_start_store=memory_auto_start,
        update_client=current_client,
    )
    assert reloaded_manager.opacity_percent.get() == 77
    assert reloaded_manager.edge_collapse_enabled.get() is False
    assert reloaded_manager.restore_margin.get() == 17
    assert reloaded_manager.no_background.get() is True
    assert reloaded_manager.auto_update.get() is True
    assert reloaded_manager.auto_start.get() is True
    assert len(reloaded_manager.windows) == 2
    reloaded_by_id = {
        window.instance_number: window for window in reloaded_manager.windows
    }
    reloaded_first = reloaded_by_id[first_window.instance_number]
    reloaded_second = reloaded_by_id[second_window.instance_number]
    assert reloaded_second.note_text.get("1.0", "end-1c") == "第二扇便签"
    assert reloaded_second.locked
    assert reloaded_second.click_through_style_is_set()
    assert reloaded_second.unlock_canvas.winfo_ismapped()
    assert reloaded_second._background_hidden
    assert reloaded_second.outlined_canvas.winfo_ismapped()
    assert "第二扇便签" in outlined_text(reloaded_second)
    _, _, restored_x, restored_y = _native_window_geometry(reloaded_second.root)
    reloaded_second.update_background_for_hover(restored_x + 20, restored_y + 20)
    assert reloaded_second._background_hidden
    assert reloaded_second.title_label.cget("text") == ""
    reloaded_second.unlock_canvas.event_generate(
        "<ButtonRelease-1>",
        x=UNLOCK_ICON_SIZE // 2,
        y=UNLOCK_ICON_SIZE // 2,
    )
    reloaded_manager.root.update()
    assert not reloaded_second.locked
    reloaded_second.set_locked(True)
    assert reloaded_first.mode == "待办"
    assert reloaded_first.todo_items == [("只属于第一个窗口", True)]
    assert reloaded_first.timer_minutes.get() == 7
    assert reloaded_first.collapsed
    assert reloaded_first._ball_geometry == test_ball
    assert reloaded_first.ball_window.state() == "normal"
    reloaded_first._restore_from_ball()
    deadline = time.monotonic() + 2
    while reloaded_first.animating and time.monotonic() < deadline:
        reloaded_manager.root.update()
        time.sleep(0.01)
    assert not reloaded_first.collapsed
    assert _native_window_geometry(reloaded_first.root)[:2] == (470, 310)
    reloaded_first.close()
    reloaded_second.close()
    reloaded_manager.exit_app()
    closed_reopen_manager = DesktopManager(
        tray_enabled=False,
        visible=True,
        settings_path=test_settings_path,
        auto_start_store=memory_auto_start,
        update_client=current_client,
    )
    assert len(closed_reopen_manager.windows) == 1
    reopened = closed_reopen_manager.windows[0]
    assert reopened.instance_number == second_window.instance_number
    assert reopened.mode == "便签"
    assert reopened.note_text.get("1.0", "end-1c") == "第二扇便签"
    assert reopened.locked
    assert reopened.unlock_canvas.winfo_ismapped()
    assert closed_reopen_manager.auto_start.get() is True
    closed_reopen_manager.exit_app()
    temporary_settings_directory.cleanup()
    print(
        "Self-test passed: tray manager and icons, persistent settings and windows, "
        "per-user auto-start option, "
        "verified GitHub update index and persistent auto-update option, "
        "four independent window modes, empty-note placeholder, "
        "no-background mode, persistent content-visible click-through lock, "
        "background lifetime, "
        "and ball collapse/restore work correctly."
    )


def _position_from_arguments(arguments: list[str]) -> tuple[int, int] | None:
    try:
        position_index = arguments.index("--position")
        return (
            int(arguments[position_index + 1]),
            int(arguments[position_index + 2]),
        )
    except (ValueError, IndexError):
        return None


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--apply-update":
        sys.exit(_apply_staged_update(sys.argv[2:]))
    elif "--self-test" in sys.argv:
        _self_test()
    else:
        DesktopManager(
            initial_position=_position_from_arguments(sys.argv[1:])
        ).run()
