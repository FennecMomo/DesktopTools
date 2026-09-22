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
import urllib.parse
import urllib.request
import winreg
from collections import deque
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path
from queue import Empty, Queue


APP_TITLE = "DesktopTools 自由窗口"
APP_VERSION = "2.3.0"
UPDATE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/FennecMomo/DesktopTools/"
    "main/dist/update.json"
)
UPDATE_PACKAGE_URL = (
    "https://raw.githubusercontent.com/FennecMomo/DesktopTools/"
    "main/dist/DesktopTools.exe"
)
MAX_UPDATE_BYTES = 100 * 1024 * 1024
SINGLE_INSTANCE_MUTEX_NAME = "Local\\FennecMomo.DesktopTools.Singleton.v1"
SECOND_INSTANCE_MESSAGE_NAME = "FennecMomo.DesktopTools.SecondInstance.v1"

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
SHORTCUT_ICON_SIZE = 46
SHORTCUT_ICON_GAP = 6
RESTORE_MARGIN = 10
EDGE_TRIGGER_DISTANCE = 28
ANIMATION_STEPS = 10
ANIMATION_DELAY_MS = 14
HOVER_POLL_MS = 90
HOVER_MARGIN = 16
WINDOW_MODES = ("便签", "待办", "任务胶囊", "倒计时", "时钟", "快捷按键", "浏览器")
DEFAULT_BROWSER_URL = "https://www.bing.com/"
BROWSER_MIN_WIDTH = 760
BROWSER_MIN_HEIGHT = 520
MODE_HINTS = {
    "便签": "把临时想法放在手边",
    "待办": "双击切换完成；选中后可编辑或删除",
    "任务胶囊": "一次只专注当前任务",
    "倒计时": "专注、休息或提醒自己换个任务",
    "时钟": "开会或全屏工作时也能看到时间",
    "快捷按键": "一键执行常用操作",
    "浏览器": "在自由窗口中浏览网页",
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
WS_EX_TOOLWINDOW = 0x00000080
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
WM_HOTKEY = 0x0312
WM_APP = 0x8000
HWND_BROADCAST = 0xFFFF
ERROR_ALREADY_EXISTS = 183
TRAY_CALLBACK_MESSAGE = WM_APP + 20
QUICK_CAPTURE_HOTKEY_ID = 1
HIDE_HOTKEY_IDS = (2, 3)
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
GW_OWNER = 4
SW_RESTORE = 9
DWMWA_CLOAKED = 14

NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIM_MODIFY = 0x00000001
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010
NIIF_INFO = 0x00000001

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100
TPM_NONOTIFY = 0x0080

TRAY_COMMAND_ADD = 1001
TRAY_COMMAND_SETTINGS = 1002
TRAY_COMMAND_EXIT = 1003
TRAY_COMMAND_UPDATE = 1004
TRAY_COMMAND_CAPTURE = 1005
TRAY_COMMAND_VISIBILITY = 1006
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

EnumWindowsCallback = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HWND,
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
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
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
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(Point)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [EnumWindowsCallback, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetMenuItemInfoW.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    wintypes.BOOL,
    ctypes.POINTER(MenuItemInfo),
]
user32.SetMenuItemInfoW.restype = wintypes.BOOL

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
kernel32.GetCurrentProcessId.argtypes = []
kernel32.GetCurrentProcessId.restype = wintypes.DWORD
kernel32.CreateMutexW.argtypes = [
    wintypes.LPVOID,
    wintypes.BOOL,
    wintypes.LPCWSTR,
]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
kernel32.ReleaseMutex.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
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

dwmapi.DwmGetWindowAttribute.argtypes = [
    wintypes.HWND,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.DWORD,
]
dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long

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


def _is_cloaked_window(hwnd: int) -> bool:
    """Hide windows that belong to other virtual desktops or suspended UWP apps."""
    cloaked = wintypes.DWORD()
    result = dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        DWMWA_CLOAKED,
        ctypes.byref(cloaked),
        ctypes.sizeof(cloaked),
    )
    return result == 0 and cloaked.value != 0


def _switch_candidates() -> list[int]:
    """List switchable windows in Alt+Tab-like z-order, excluding this process."""
    own_process = kernel32.GetCurrentProcessId()
    candidates: list[int] = []

    def collect(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindow(hwnd, GW_OWNER):
            return True
        if int(_get_window_long(wintypes.HWND(hwnd), GWL_EXSTYLE)) & WS_EX_TOOLWINDOW:
            return True
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value == own_process:
            return True
        class_name = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, class_name, 64)
        if class_name.value in (
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "Shell_SecondaryTrayWnd",
        ):
            return True
        if _is_cloaked_window(hwnd):
            return True
        candidates.append(int(hwnd))
        return True

    user32.EnumWindows(EnumWindowsCallback(collect), 0)
    return candidates


def _activate_window(hwnd: int) -> bool:
    handle = wintypes.HWND(hwnd)
    if user32.IsIconic(handle):
        user32.ShowWindow(handle, SW_RESTORE)
    return bool(user32.SetForegroundWindow(handle))


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


def _browser_destination(address: str) -> str:
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


class SingleInstanceGuard:
    """Own a named Windows mutex for the lifetime of the main app process."""

    def __init__(self, name: str = SINGLE_INSTANCE_MUTEX_NAME) -> None:
        self.name = name
        self._handle: int | None = None

    @property
    def acquired(self) -> bool:
        return self._handle is not None

    def acquire(self) -> bool:
        if self._handle is not None:
            return True
        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, True, self.name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False
        self._handle = handle
        return True

    def close(self) -> None:
        if self._handle is None:
            return
        kernel32.ReleaseMutex(self._handle)
        kernel32.CloseHandle(self._handle)
        self._handle = None


def _signal_existing_instance() -> bool:
    message = user32.RegisterWindowMessageW(SECOND_INSTANCE_MESSAGE_NAME)
    return bool(
        message and user32.PostMessageW(HWND_BROADCAST, message, 0, 0)
    )


class SettingsStore:
    DEFAULTS = {
        "opacity_percent": 86,
        "edge_collapse_enabled": True,
        "restore_margin": RESTORE_MARGIN,
        "no_background": False,
        "auto_update": False,
        "hide_hotkey": "Ctrl+K",
    }

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else _default_settings_path()

    def load(self) -> dict[str, int | bool | str]:
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
        if type(remaining) in (int, float) and math.isfinite(remaining):
            task.focus_remaining_seconds = _clamp(round(remaining), 0, 180 * 60)
        else:
            task.focus_remaining_seconds = task.timer_minutes * 60
        return task

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


FOCUS_STATUS_TEXT = {
    "running": "运行中",
    "paused": "已暂停",
    "finished": "已完成",
    "ready": "待开始",
}
TIMER_STATUS_TEXT = {
    "running": "运行中",
    "paused": "已暂停",
    "finished": "已结束",
    "ready": "未开始",
}
DUE_OVERDUE = "#FF6B6B"


def _format_due_timestamp(value: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value))


def _todo_display_text(item: tuple[str, bool, float | None, float | None]) -> str:
    title, done, due, _created = item
    text = f"{'☑' if done else '☐'}  {title}"
    if due is not None:
        text += f"　⏰ {time.strftime('%m-%d %H:%M:%S', time.localtime(due))}"
    return text


def _due_epoch_from_fields(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    second: int,
) -> float:
    try:
        stamp = time.mktime((year, month, day, hour, minute, second, 0, 0, -1))
    except (OverflowError, ValueError) as error:
        raise ValueError("日期或时间无效") from error
    if time.localtime(stamp)[:6] != (year, month, day, hour, minute, second):
        raise ValueError("日期或时间无效")
    return stamp


def _task_content_summary(task: TaskState) -> str:
    parts: list[str] = []
    note_characters = len("".join(task.note.split()))
    if note_characters:
        parts.append(f"便签 {note_characters} 字")
    done_count = sum(1 for item in task.todos if item[1])
    if task.todos:
        if done_count:
            parts.append(f"待办 {len(task.todos)} 项（{done_count} 项完成）")
        else:
            parts.append(f"待办 {len(task.todos)} 项")
    focus_index = task.focus_task_index
    if focus_index is not None and 0 <= focus_index < len(task.todos):
        title = task.todos[focus_index][0]
        short_title = title[:16] + ("…" if len(title) > 16 else "")
        focus_status = FOCUS_STATUS_TEXT.get(task.focus_status, task.focus_status)
        parts.append(f"任务胶囊：{short_title}（{focus_status}）")
    if task.timer_status != "ready":
        timer_status = TIMER_STATUS_TEXT.get(task.timer_status, task.timer_status)
        parts.append(f"倒计时 {task.timer_minutes} 分（{timer_status}）")
    return " · ".join(parts)


def _prompt_task_binding(
    parent: tk.Misc,
    current_task_id: int,
    tasks: list[TaskState],
) -> int | None:
    window = tk.Toplevel(parent)
    window.withdraw()
    window.title("绑定任务编号")
    window.configure(bg=BG_BODY)
    window.resizable(False, False)
    window.transient(parent.winfo_toplevel())
    window.attributes("-topmost", True)

    result: list[int | None] = [None]

    tk.Label(
        window,
        text="绑定任务编号",
        bg=BG_BODY,
        fg=TEXT,
        font=("Microsoft YaHei UI", 12, "bold"),
        anchor="w",
    ).pack(fill="x", padx=18, pady=(14, 2))

    tk.Label(
        window,
        text="已有任务的内容一览；选中一行可填入编号，输入新编号会新建任务。",
        bg=BG_BODY,
        fg=TEXT_MUTED,
        font=("Microsoft YaHei UI", 9),
        anchor="w",
    ).pack(fill="x", padx=18, pady=(0, 6))

    list_row = tk.Frame(window, bg=BG_BODY)
    list_row.pack(fill="both", expand=True, padx=18)
    list_height = _clamp(len(tasks), 1, 10)
    task_list = tk.Listbox(
        list_row,
        bg=BG_PANEL,
        fg=TEXT,
        selectbackground="#3B6557",
        selectforeground=TEXT,
        activestyle="none",
        relief="flat",
        bd=0,
        highlightthickness=0,
        font=("Microsoft YaHei UI", 9),
        height=list_height,
        width=58,
        exportselection=False,
    )
    task_list.pack(side="left", fill="both", expand=True)
    if len(tasks) > list_height:
        scrollbar = tk.Scrollbar(
            list_row,
            command=task_list.yview,
            bg=BG_BODY,
            troughcolor=BG_PANEL,
            activebackground=BG_TITLE,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        scrollbar.pack(side="right", fill="y")
        task_list.configure(yscrollcommand=scrollbar.set)
    task_ids = [task.id for task in tasks]
    if tasks:
        for index, task in enumerate(tasks):
            summary = _task_content_summary(task)
            line = f"#{task.id} {'●' if summary else '○'} {summary or '暂无内容'}"
            if task.id == current_task_id:
                line += "　← 当前窗口"
            task_list.insert("end", line)
            if task.id == current_task_id:
                task_list.itemconfig(index, fg=ACCENT)
            elif not summary:
                task_list.itemconfig(index, fg=TEXT_MUTED)
    else:
        task_list.insert("end", "还没有任务；直接输入编号即可新建。")
        task_list.itemconfig(0, fg=TEXT_MUTED)

    entry_row = tk.Frame(window, bg=BG_BODY)
    entry_row.pack(fill="x", padx=18, pady=(10, 2))
    tk.Label(
        entry_row,
        text="任务编号",
        bg=BG_BODY,
        fg=TEXT,
        font=("Microsoft YaHei UI", 10),
    ).pack(side="left")
    entry_value = tk.StringVar(master=window, value=str(current_task_id))
    entry = tk.Entry(
        entry_row,
        textvariable=entry_value,
        width=14,
        bg=BG_PANEL,
        fg=TEXT,
        insertbackground=TEXT,
        relief="flat",
        font=("Segoe UI", 10),
    )
    entry.pack(side="left", padx=(10, 0), ipady=4)

    status_label = tk.Label(
        window,
        text="已有任务会共享便签、待办和计时；不存在的编号会新建任务。",
        bg=BG_BODY,
        fg=TEXT_MUTED,
        font=("Microsoft YaHei UI", 8),
        anchor="w",
    )
    status_label.pack(fill="x", padx=18, pady=(0, 6))

    def submit(_event: tk.Event | None = None) -> None:
        value = entry_value.get().strip()
        if not value.isdigit() or int(value) < 1:
            status_label.configure(text="请输入大于 0 的整数编号。", fg=CLOSE_HOVER)
            return
        result[0] = int(value)
        window.destroy()

    def fill_from_selection(_event: tk.Event | None = None) -> None:
        selection = task_list.curselection()
        if selection:
            entry_value.set(str(task_ids[selection[0]]))

    task_list.bind("<<ListboxSelect>>", fill_from_selection)
    task_list.bind("<Double-Button-1>", fill_from_selection)
    entry.bind("<Return>", submit)

    button_row = tk.Frame(window, bg=BG_BODY)
    button_row.pack(fill="x", padx=18, pady=(0, 14))
    tk.Button(
        button_row,
        text="取消",
        command=window.destroy,
        bg=BG_PANEL,
        fg=TEXT_MUTED,
        relief="flat",
        bd=0,
        padx=14,
        cursor="hand2",
    ).pack(side="right")
    tk.Button(
        button_row,
        text="绑定",
        command=submit,
        bg=BG_TITLE,
        fg=ACCENT,
        relief="flat",
        bd=0,
        padx=14,
        cursor="hand2",
    ).pack(side="right", padx=(0, 8))

    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.bind("<Escape>", lambda _event: window.destroy())
    window.update_idletasks()
    top = parent.winfo_toplevel()
    x = top.winfo_rootx() + (top.winfo_width() - window.winfo_reqwidth()) // 2
    y = top.winfo_rooty() + (top.winfo_height() - window.winfo_reqheight()) // 2
    x = _clamp(x, 0, max(0, window.winfo_screenwidth() - window.winfo_reqwidth()))
    y = _clamp(y, 0, max(0, window.winfo_screenheight() - window.winfo_reqheight()))
    window.geometry(f"+{x}+{y}")
    window.deiconify()
    window.grab_set()
    entry.focus_set()
    entry.selection_range(0, "end")
    parent.wait_window(window)
    return result[0]


def _prompt_todo_due(
    parent: tk.Misc,
    todo_title: str,
    initial_epoch: float | None,
) -> tuple[bool, float | None]:
    initial = time.localtime(
        initial_epoch if initial_epoch is not None else time.time()
    )
    window = tk.Toplevel(parent)
    window.withdraw()
    window.title("设置截止时间")
    window.configure(bg=BG_BODY)
    window.resizable(False, False)
    window.transient(parent.winfo_toplevel())
    window.attributes("-topmost", True)

    result: list[tuple[bool, float | None]] = [(False, None)]

    tk.Label(
        window,
        text="设置截止时间",
        bg=BG_BODY,
        fg=TEXT,
        font=("Microsoft YaHei UI", 12, "bold"),
        anchor="w",
    ).pack(fill="x", padx=18, pady=(14, 2))

    short_title = todo_title[:40] + ("…" if len(todo_title) > 40 else "")
    tk.Label(
        window,
        text=f"待办：{short_title}",
        bg=BG_BODY,
        fg=TEXT_MUTED,
        font=("Microsoft YaHei UI", 9),
        anchor="w",
    ).pack(fill="x", padx=18, pady=(0, 8))

    fields_row = tk.Frame(window, bg=BG_BODY)
    fields_row.pack(fill="x", padx=18)
    specs = (
        ("year", 2000, 2099, 5),
        ("month", 1, 12, 3),
        ("day", 1, 31, 3),
        ("hour", 0, 23, 3),
        ("minute", 0, 59, 3),
        ("second", 0, 59, 3),
    )
    units = ("年", "月", "日", "时", "分", "秒")
    variables: dict[str, tk.IntVar] = {}
    for index, (name, minimum, maximum, width) in enumerate(specs):
        variable = tk.IntVar(master=window, value=initial[index])
        variables[name] = variable
        tk.Spinbox(
            fields_row,
            from_=minimum,
            to=maximum,
            textvariable=variable,
            width=width,
            justify="center",
            bg=BG_PANEL,
            fg=TEXT,
            buttonbackground=BG_TITLE,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(0, 4))
        tk.Label(
            fields_row,
            text=units[index],
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 9),
        ).pack(side="left", padx=(0, 8))

    status_label = tk.Label(
        window,
        text="截止时间到时只提醒一次，并把该事项标红，直到完成或改期。",
        bg=BG_BODY,
        fg=TEXT_MUTED,
        font=("Microsoft YaHei UI", 8),
        anchor="w",
    )
    status_label.pack(fill="x", padx=18, pady=(8, 6))

    def submit(_event: tk.Event | None = None) -> None:
        try:
            values = tuple(int(variables[name].get()) for name, *_rest in specs)
        except (tk.TclError, ValueError):
            status_label.configure(text="请输入有效的年月日时分秒。", fg=CLOSE_HOVER)
            return
        try:
            stamp = _due_epoch_from_fields(*values)
        except ValueError as error:
            status_label.configure(text=str(error), fg=CLOSE_HOVER)
            return
        result[0] = (True, stamp)
        window.destroy()

    def clear(_event: tk.Event | None = None) -> None:
        result[0] = (True, None)
        window.destroy()

    button_row = tk.Frame(window, bg=BG_BODY)
    button_row.pack(fill="x", padx=18, pady=(0, 14))
    tk.Button(
        button_row,
        text="取消",
        command=window.destroy,
        bg=BG_PANEL,
        fg=TEXT_MUTED,
        relief="flat",
        bd=0,
        padx=14,
        cursor="hand2",
    ).pack(side="right")
    tk.Button(
        button_row,
        text="清除截止",
        command=clear,
        bg=BG_PANEL,
        fg=TEXT_MUTED,
        relief="flat",
        bd=0,
        padx=14,
        cursor="hand2",
    ).pack(side="right", padx=(0, 8))
    tk.Button(
        button_row,
        text="确定",
        command=submit,
        bg=BG_TITLE,
        fg=ACCENT,
        relief="flat",
        bd=0,
        padx=14,
        cursor="hand2",
    ).pack(side="right", padx=(0, 8))

    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.bind("<Escape>", lambda _event: window.destroy())
    window.bind("<Return>", submit)
    window.update_idletasks()
    top = parent.winfo_toplevel()
    x = top.winfo_rootx() + (top.winfo_width() - window.winfo_reqwidth()) // 2
    y = top.winfo_rooty() + (top.winfo_height() - window.winfo_reqheight()) // 2
    x = _clamp(x, 0, max(0, window.winfo_screenwidth() - window.winfo_reqwidth()))
    y = _clamp(y, 0, max(0, window.winfo_screenheight() - window.winfo_reqheight()))
    window.geometry(f"+{x}+{y}")
    window.deiconify()
    window.grab_set()
    parent.wait_window(window)
    return result[0]


class WindowStateStore:
    """Persist window presentation separately from shared task content."""

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
                if type(raw_remaining) in (int, float)
                and math.isfinite(raw_remaining)
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
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
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
                    {"version": 2, "windows": windows, "tasks": tasks},
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

    if kind == "capture":
        if -5 <= dx <= 5 and -5 <= dy <= 5:
            if abs(dx) >= 4 or abs(dy) >= 4 or (dx >= 1 and dy >= 1):
                return 245, 184, 92
        return None

    if kind == "visibility":
        ellipse = (dx / 6.3) ** 2 + (dy / 3.5) ** 2
        if abs(ellipse - 1) <= 0.26 or radius <= 1.8:
            return 177, 145, 235
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
        on_capture: Callable[[], None],
        on_toggle_visibility: Callable[[], None],
        on_second_launch: Callable[[], None],
        on_exit: Callable[[], None],
        hide_hotkey: str,
        show_icon: bool = True,
    ) -> None:
        self.root = root
        self.on_add = on_add
        self.on_settings = on_settings
        self.on_update = on_update
        self.on_capture = on_capture
        self.on_toggle_visibility = on_toggle_visibility
        self.on_second_launch = on_second_launch
        self.on_exit = on_exit
        self.show_icon = show_icon
        self._cleaned = False
        self._icon_added = False
        self.hotkey_registered = False
        self.hide_hotkey = _parse_hide_hotkey(hide_hotkey)[0]
        self._hide_hotkey_id: int | None = None
        self._menu_bitmaps: dict[int, int] = {}
        self._pending_actions: deque[Callable[[], None]] = deque()
        self._drain_after_id: str | None = None
        self._instance_handle = kernel32.GetModuleHandleW(None)
        self._class_name = f"DesktopToolsTray_{id(self):x}"
        self._window_proc_callback = WindowProcedure(self._window_proc)
        self._taskbar_created_message = user32.RegisterWindowMessageW(
            "TaskbarCreated"
        )
        self._second_instance_message = user32.RegisterWindowMessageW(
            SECOND_INSTANCE_MESSAGE_NAME
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
            TRAY_COMMAND_CAPTURE: _create_menu_bitmap("capture"),
            TRAY_COMMAND_VISIBILITY: _create_menu_bitmap("visibility"),
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
            self.hotkey_registered = bool(
                user32.RegisterHotKey(
                    self.hwnd,
                    QUICK_CAPTURE_HOTKEY_ID,
                    MOD_CONTROL | MOD_ALT,
                    ord("D"),
                )
            )
            self.set_hide_hotkey(self.hide_hotkey)
        self._drain_after_id = self.root.after(40, self._drain_actions)

    @property
    def hide_hotkey_registered(self) -> bool:
        return self._hide_hotkey_id is not None

    def set_hide_hotkey(self, binding: str) -> bool:
        canonical, modifiers, virtual_key = _parse_hide_hotkey(binding)
        if not self.show_icon:
            self.hide_hotkey = canonical
            return True
        if canonical == self.hide_hotkey and self._hide_hotkey_id is not None:
            return True
        candidate_id = next(
            identifier for identifier in HIDE_HOTKEY_IDS
            if identifier != self._hide_hotkey_id
        )
        if not user32.RegisterHotKey(
            self.hwnd, candidate_id, modifiers | MOD_NOREPEAT, virtual_key
        ):
            return False
        if self._hide_hotkey_id is not None:
            user32.UnregisterHotKey(self.hwnd, self._hide_hotkey_id)
        self._hide_hotkey_id = candidate_id
        self.hide_hotkey = canonical
        return True

    def _add_icon(self) -> None:
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._notify_data)):
            raise RuntimeError("无法创建系统托盘图标")
        self._icon_added = True

    def notify(self, title: str, message: str) -> None:
        if not self._icon_added:
            return
        notice = NotifyIconData()
        notice.cbSize = ctypes.sizeof(NotifyIconData)
        notice.hWnd = self.hwnd
        notice.uID = 1
        notice.uFlags = NIF_INFO
        notice.szInfoTitle = title[:63]
        notice.szInfo = message[:255]
        notice.dwInfoFlags = NIIF_INFO
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(notice))

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

        if message == WM_HOTKEY and int(w_param) == QUICK_CAPTURE_HOTKEY_ID:
            self._schedule(self.on_capture)
            return 0
        if message == WM_HOTKEY and int(w_param) == self._hide_hotkey_id:
            self._schedule(self.on_toggle_visibility)
            return 0
        if message == self._second_instance_message:
            self._schedule(self.on_second_launch)
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
            capture_label = (
                "快速收集（Ctrl+Alt+D）"
                if self.hotkey_registered else "快速收集（快捷键被占用）"
            )
            user32.AppendMenuW(menu, MF_STRING, TRAY_COMMAND_CAPTURE, capture_label)
            visibility_label = (
                f"隐藏/显示全部窗口（{self.hide_hotkey}）"
                if self.hide_hotkey_registered else "隐藏/显示全部窗口（快捷键被占用）"
            )
            user32.AppendMenuW(
                menu, MF_STRING, TRAY_COMMAND_VISIBILITY, visibility_label
            )
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
            TRAY_COMMAND_CAPTURE: self.on_capture,
            TRAY_COMMAND_VISIBILITY: self.on_toggle_visibility,
            TRAY_COMMAND_EXIT: self.on_exit,
        }
        action = actions.get(command)
        if action is not None:
            self._schedule(action)

    def cleanup(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
        if self.hotkey_registered:
            user32.UnregisterHotKey(self.hwnd, QUICK_CAPTURE_HOTKEY_ID)
            self.hotkey_registered = False
        if self._hide_hotkey_id is not None:
            user32.UnregisterHotKey(self.hwnd, self._hide_hotkey_id)
            self._hide_hotkey_id = None
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
        task: TaskState | None = None,
        on_state_change: Callable[["OverlayApp"], None] | None = None,
        on_focus_complete: Callable[["OverlayApp"], None] | None = None,
        on_timer_complete: Callable[["OverlayApp"], None] | None = None,
        on_bind_task: Callable[["OverlayApp", int], None] | None = None,
        on_list_tasks: Callable[[], list[TaskState]] | None = None,
        on_todo_due: Callable[["OverlayApp", int], None] | None = None,
        browser_data_dir: Path | None = None,
        browser_session_factory: Callable[[], object] | None = None,
    ) -> None:
        self.visible = visible
        self.on_close = on_close
        self.on_state_change = on_state_change
        self.on_focus_complete = on_focus_complete
        self.on_timer_complete = on_timer_complete
        self.on_bind_task = on_bind_task
        self.on_list_tasks = on_list_tasks
        self.on_todo_due = on_todo_due
        self.instance_number = instance_number
        self.task = task or TaskState(instance_number)
        self._syncing_task = False
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
        self._browser_first_open = (
            saved_state is None or saved_state.get("mode") != "浏览器"
        )
        self._editing_todo_index: int | None = None
        self._todo_overdue_state: tuple[bool, ...] = ()
        self._switch_targets: list[int] = []
        self._switch_index = 0
        self._tick_after_id: str | None = None
        self.browser_url = (
            str(saved_state.get("browser_url", DEFAULT_BROWSER_URL))
            if saved_state is not None else DEFAULT_BROWSER_URL
        )
        self.browser_data_dir = browser_data_dir or _default_settings_path().parent / "browser"
        self._browser_session_factory = browser_session_factory
        self._browser_owned_session: object | None = None
        self._browser_web: object | None = None
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
        self.browser_address = tk.StringVar(master=self.root, value=self.browser_url)

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
        self._build_shortcut_window()
        self._apply_control_colors()
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

    @property
    def task_id(self) -> int:
        return self.task.id

    @property
    def todo_items(self) -> list[tuple[str, bool, float | None, float | None]]:
        return self.task.todos

    @todo_items.setter
    def todo_items(
        self,
        value: list[tuple[str, bool, float | None, float | None]],
    ) -> None:
        self.task.todos = value

    @property
    def _focus_task_index(self) -> int | None:
        return self.task.focus_task_index

    @_focus_task_index.setter
    def _focus_task_index(self, value: int | None) -> None:
        self.task.focus_task_index = value

    @property
    def _focus_status(self) -> str:
        return self.task.focus_status

    @_focus_status.setter
    def _focus_status(self, value: str) -> None:
        self.task.focus_status = value

    @property
    def _focus_remaining_seconds(self) -> float:
        return self.task.focus_remaining_seconds

    @_focus_remaining_seconds.setter
    def _focus_remaining_seconds(self, value: float) -> None:
        self.task.focus_remaining_seconds = value

    @property
    def _focus_deadline(self) -> float | None:
        return self.task.focus_deadline

    @_focus_deadline.setter
    def _focus_deadline(self, value: float | None) -> None:
        self.task.focus_deadline = value

    @property
    def _timer_duration_minutes(self) -> int:
        return self.task.timer_minutes

    @_timer_duration_minutes.setter
    def _timer_duration_minutes(self, value: int) -> None:
        self.task.timer_minutes = value

    @property
    def _timer_remaining_seconds(self) -> float:
        return self.task.timer_remaining_seconds

    @_timer_remaining_seconds.setter
    def _timer_remaining_seconds(self, value: float) -> None:
        self.task.timer_remaining_seconds = value

    @property
    def _timer_deadline(self) -> float | None:
        return self.task.timer_deadline

    @_timer_deadline.setter
    def _timer_deadline(self, value: float | None) -> None:
        self.task.timer_deadline = value

    def _restore_saved_content(self, saved_state: dict[str, object] | None) -> None:
        del saved_state
        self.refresh_from_task()
        self.timer_minutes.trace_add("write", self._on_timer_duration_changed)

    def refresh_from_task(self) -> None:
        self._syncing_task = True
        try:
            if self.note_text.get("1.0", "end-1c") != self.task.note:
                self.note_text.delete("1.0", "end")
                self.note_text.insert("1.0", self.task.note)
                self.note_text.edit_modified(False)
            expected_todos = tuple(
                _todo_display_text(item)
                for item in self.todo_items
            )
            if self.todo_list.get(0, "end") != expected_todos:
                selected = self._selected_todo_index()
                if self._editing_todo_index is not None:
                    self._cancel_todo_edit()
                self._render_todos(selected)
            if self.timer_minutes.get() != self.task.timer_minutes:
                self.timer_minutes.set(self.task.timer_minutes)
            self._update_focus_display()
            self._update_timer_display()
            if hasattr(self, "lock_button"):
                self._apply_control_colors()
        finally:
            self._syncing_task = False

    def bind_task(self, task: TaskState) -> None:
        if task is self.task:
            return
        if self._editing_todo_index is not None:
            self._cancel_todo_edit()
        self.task = task
        self.refresh_from_task()
        self._notify_state_changed()

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
            "task_id": self.task_id,
            "active": True,
            "mode": self.mode,
            "geometry": list(geometry),
            "collapsed": self.collapsed,
            "locked": self.locked,
            "ball_geometry": list(self._ball_geometry) if self.collapsed else None,
            "dock_edge": self._dock_edge if self.collapsed else None,
            "browser_url": self.browser_url,
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
        self.mode_menu.add_separator()
        self.mode_menu.add_command(
            label="绑定任务编号…",
            command=lambda: self.root.after_idle(self._request_task_binding),
            state="normal" if self.on_bind_task is not None else "disabled",
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
            text=f"●  便签 · 任务 #{self.task_id}",
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
        self.todo_add_button = tk.Button(
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
        self.todo_add_button.pack(side="right", padx=(8, 0), ipady=2)
        self._register_mode_style(self.todo_add_button, bg=ACCENT, fg="#102219")
        self.todo_cancel_button = tk.Button(
            self.todo_entry_row,
            text="取消",
            command=self._cancel_todo_edit,
            bg=BG_BODY,
            fg=TEXT_MUTED,
            relief="flat",
            bd=0,
            padx=8,
            cursor="hand2",
        )
        self._register_mode_style(self.todo_cancel_button, bg=BG_BODY, fg=TEXT_MUTED)

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
        self.todo_list.bind("<Double-Button-1>", self._toggle_todo)
        self.todo_list.bind("<F2>", self._edit_todo)
        self.todo_list.bind("<Delete>", self._delete_todo)
        self._register_mode_style(
            self.todo_list,
            bg=BG_PANEL,
            selectbackground="#3B6557",
        )
        self.todo_actions = tk.Frame(todo_view, bg=BG_PANEL)
        self.todo_actions.pack(side="bottom", fill="x", pady=(4, 0))
        self._register_mode_style(self.todo_actions, bg=BG_PANEL)
        for row_index, row_definitions in enumerate(
            (
                (
                    ("todo_toggle_button", "完成 / 撤销", self._toggle_todo),
                    ("todo_edit_button", "编辑选中", self._edit_todo),
                    ("todo_delete_button", "删除选中", self._delete_todo),
                ),
                (
                    ("todo_due_button", "设置截止", self._request_todo_due),
                    ("todo_focus_button", "开始专注", self._start_focus_for_selected),
                ),
            )
        ):
            row = tk.Frame(self.todo_actions, bg=BG_PANEL)
            row.pack(fill="x", pady=(0, 4) if row_index == 0 else 0)
            self._register_mode_style(row, bg=BG_PANEL)
            for name, label, action in row_definitions:
                button = tk.Button(
                    row,
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
                setattr(self, name, button)
                button.pack(side="left", padx=(0, 8))
                self._register_mode_style(button, bg=BG_BODY, fg=TEXT_MUTED)
        self.todo_list.pack(fill="both", expand=True)

        self.timer_minutes = tk.IntVar(master=self.root, value=25)
        focus_view = self.mode_views["任务胶囊"]
        self.focus_header = tk.Frame(focus_view, bg=BG_PANEL)
        self.focus_header.pack(fill="x")
        self._register_mode_style(self.focus_header, bg=BG_PANEL)
        self.focus_task_label = tk.Label(
            self.focus_header,
            text="从待办中选择任务",
            bg=BG_PANEL,
            fg=TEXT,
            anchor="w",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self.focus_task_label.pack(side="left", fill="x", expand=True)
        self._register_mode_style(self.focus_task_label, bg=BG_PANEL, fg=TEXT)
        self.focus_minutes_input = tk.Spinbox(
            self.focus_header,
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
            font=("Segoe UI", 9),
        )
        # The shared duration variable is created before the focus view is built.
        self.focus_minutes_input.pack(side="right")
        self._register_mode_style(self.focus_minutes_input, bg=BG_BODY, fg=TEXT)
        self.focus_time_label = tk.Label(
            focus_view,
            text="25:00",
            bg=BG_PANEL,
            fg=TEXT,
            font=("Segoe UI", 28, "bold"),
        )
        self._register_mode_style(self.focus_time_label, bg=BG_PANEL, fg=TEXT)
        self.focus_actions = tk.Frame(focus_view, bg=BG_PANEL)
        self.focus_actions.pack(side="bottom", fill="x")
        self._register_mode_style(self.focus_actions, bg=BG_PANEL)
        for name, label, action in (
            ("focus_start_button", "暂停", self._toggle_focus),
            ("focus_reset_button", "重来", self._reset_focus),
            ("focus_complete_button", "完成任务", self._complete_focus),
            ("focus_back_button", "返回待办", lambda: self.set_mode("待办")),
        ):
            button = tk.Button(
                self.focus_actions,
                text=label,
                command=action,
                bg=BG_BODY,
                fg=TEXT_MUTED,
                relief="flat",
                bd=0,
                padx=6,
                font=("Microsoft YaHei UI", 8),
                cursor="hand2",
            )
            setattr(self, name, button)
            button.pack(side="left", padx=(0, 5))
            self._register_mode_style(button, bg=BG_BODY, fg=TEXT_MUTED)
        self.focus_time_label.pack(expand=True)

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

        shortcut_view = self.mode_views["快捷按键"]
        self.shortcut_buttons_frame = tk.Frame(shortcut_view, bg=BG_PANEL)
        self.shortcut_buttons_frame.pack(fill="x")
        self._register_mode_style(self.shortcut_buttons_frame, bg=BG_PANEL)
        self.shortcut_buttons: list[tk.Button] = []
        for label, hint, action, _icon in self._shortcut_definitions():
            button = tk.Button(
                self.shortcut_buttons_frame,
                text=f"{label}（{hint}）",
                command=action,
                bg=ACCENT,
                fg="#102219",
                activebackground=ACCENT_HOVER,
                activeforeground="#102219",
                relief="flat",
                bd=0,
                highlightthickness=0,
                font=("Microsoft YaHei UI", 10, "bold"),
                cursor="hand2",
                takefocus=False,
                pady=9,
            )
            button.pack(fill="x", pady=(0, 8))
            self._register_mode_style(
                button,
                bg=ACCENT,
                fg="#102219",
                activebackground=ACCENT_HOVER,
                activeforeground="#102219",
            )
            self.shortcut_buttons.append(button)

        browser_view = self.mode_views["浏览器"]
        self.browser_toolbar = tk.Frame(browser_view, bg=BG_PANEL)
        self.browser_toolbar.pack(fill="x", pady=(0, 6))
        self._register_mode_style(self.browser_toolbar, bg=BG_PANEL)
        for label, action in (
            ("‹", self._browser_back),
            ("›", self._browser_forward),
            ("↻", self._browser_reload),
        ):
            button = tk.Button(
                self.browser_toolbar,
                text=label,
                command=action,
                bg=BG_BODY,
                fg=TEXT,
                relief="flat",
                bd=0,
                width=3,
                cursor="hand2",
                takefocus=False,
            )
            button.pack(side="left", padx=(0, 4))
            self._register_mode_style(button, bg=BG_BODY, fg=TEXT)
        self.browser_entry = tk.Entry(
            self.browser_toolbar,
            textvariable=self.browser_address,
            bg=BG_BODY,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            bd=0,
        )
        self.browser_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.browser_entry.bind("<Return>", self._browser_navigate)
        self._register_mode_style(self.browser_entry, bg=BG_BODY, fg=TEXT)
        go_button = tk.Button(
            self.browser_toolbar,
            text="前往",
            command=self._browser_navigate,
            bg=ACCENT,
            fg="#102219",
            relief="flat",
            bd=0,
            cursor="hand2",
            takefocus=False,
        )
        go_button.pack(side="left", padx=(4, 0))
        self._register_mode_style(go_button, bg=ACCENT, fg="#102219")
        self.browser_error_label = tk.Label(
            browser_view,
            text="",
            bg=BG_PANEL,
            fg=CLOSE_HOVER,
            justify="left",
            wraplength=430,
        )
        self._register_mode_style(self.browser_error_label, bg=BG_PANEL, fg=CLOSE_HOVER)
        self.browser_host = tk.Frame(browser_view, bg=BG_PANEL)
        self.browser_host.pack(fill="both", expand=True)
        self._register_mode_style(self.browser_host, bg=BG_PANEL)
        self.browser_host.bind(
            "<Map>",
            lambda _event: self.root.after(20, self._ensure_browser_view),
            add="+",
        )

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

    def _shortcut_definitions(
        self,
    ) -> tuple[tuple[str, str, Callable[[], None], str], ...]:
        """Label, key hint, action and icon kind of every shortcut button."""
        return (
            ("切换窗口", "Alt+Tab", self._shortcut_switch_window, "switch"),
        )

    def _shortcut_switch_window(self) -> None:
        if self._closed:
            return
        candidates = _switch_candidates()
        if not candidates:
            return
        if set(candidates) != set(self._switch_targets):
            self._switch_targets = candidates
            # The first window in z-order already sits right behind this
            # overlay, so start cycling from the one below it and wrap around.
            self._switch_index = 1 if len(candidates) > 1 else 0
        else:
            self._switch_index = (self._switch_index + 1) % len(self._switch_targets)
        _activate_window(self._switch_targets[self._switch_index])

    def _show_mode_menu(self) -> None:
        if self.locked or self._background_hidden:
            return
        self.mode_menu.entryconfigure(
            len(WINDOW_MODES) + 1,
            label=f"绑定任务编号…（当前 #{self.task_id}）",
        )
        try:
            self.mode_menu.tk_popup(
                self.mode_button.winfo_rootx(),
                self.mode_button.winfo_rooty() + self.mode_button.winfo_height(),
            )
        finally:
            self.mode_menu.grab_release()

    def _request_task_binding(self) -> None:
        if self._closed or self.on_bind_task is None:
            return
        tasks = self.on_list_tasks() if self.on_list_tasks is not None else []
        task_id = _prompt_task_binding(self.root, self.task_id, tasks)
        if task_id is not None:
            self.on_bind_task(self, task_id)

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
        self._sync_shortcut_window()
        if self._background_hidden:
            self._apply_background_state()
        elif mode == "浏览器":
            self.status_label.pack_forget()
            self.message_label.pack_forget()
        else:
            self.status_label.pack(pady=(10, 2), before=self.mode_container)
            self.message_label.pack(before=self.mode_container)
        self._refresh_outlined_content()
        if mode == "浏览器":
            if self._browser_first_open:
                self._browser_first_open = False
                self._expand_for_browser()
            self.root.after_idle(self._ensure_browser_view)
        self._notify_state_changed()

    def _expand_for_browser(self) -> None:
        if not self.visible or self.collapsed or self.animating:
            return
        width, height, x, y = _native_window_geometry(self.root)
        if width >= BROWSER_MIN_WIDTH and height >= BROWSER_MIN_HEIGHT:
            return
        _, (left, top, right, bottom) = _monitor_areas_at(
            x + width // 2, y + height // 2
        )
        margin = self._restore_margin_pixels()
        width = min(max(width, BROWSER_MIN_WIDTH), max(1, right - left - 2 * margin))
        height = min(max(height, BROWSER_MIN_HEIGHT), max(1, bottom - top - 2 * margin))
        x = _clamp(x, left + margin, right - width - margin)
        y = _clamp(y, top + margin, bottom - height - margin)
        _set_absolute_geometry(self.root, width=width, height=height, x=x, y=y)

    def _browser_navigate(self, _event: tk.Event | None = None) -> None:
        try:
            destination = _browser_destination(self.browser_address.get())
        except ValueError as error:
            self._browser_show_error(str(error))
            return
        self.browser_url = destination
        self.browser_address.set(destination)
        self.browser_error_label.pack_forget()
        self._refresh_outlined_content()
        self._notify_state_changed()
        if self._browser_web is None:
            self._ensure_browser_view()
        else:
            try:
                self._browser_web.load_url(destination)
            except (OSError, RuntimeError, ValueError) as error:
                self._browser_show_error(f"网页打开失败：{error}")

    def _browser_show_error(self, message: str) -> None:
        if self._closed:
            return
        self.browser_error_label.configure(text=message)
        if not self._background_hidden:
            self.browser_error_label.pack(fill="x", pady=(0, 5), before=self.browser_host)

    def _browser_page_loaded(self, _event: object, url: str) -> None:
        if self._closed or urllib.parse.urlsplit(url).scheme not in ("http", "https"):
            return
        if self.browser_url != url:
            self.browser_url = url
            self._refresh_outlined_content()
            self._notify_state_changed()
        if self.root.focus_get() is not self.browser_entry:
            self.browser_address.set(url)

    def _ensure_browser_view(self) -> None:
        if (
            self._closed or self._browser_web is not None or not self.visible
            or self.mode != "浏览器" or self.collapsed or self.animating
            or self._background_hidden or not self.browser_host.winfo_ismapped()
        ):
            return
        try:
            from tkwry import WebSession, WebView

            if self._browser_session_factory is None:
                self.browser_data_dir.mkdir(parents=True, exist_ok=True)
                if self._browser_owned_session is None:
                    self._browser_owned_session = WebSession(
                        data_directory=self.browser_data_dir
                    )
                session = self._browser_owned_session
            else:
                session = self._browser_session_factory()
            self._browser_web = WebView(
                self.browser_host,
                url=self.browser_url,
                session=session,
                bridge_origins=["https://desktoptools.invalid"],
                on_navigation=lambda event: urllib.parse.urlsplit(event.url).scheme
                in ("http", "https"),
                on_download=lambda _download: False,
                on_page_load=self._browser_page_loaded,
                on_creation_failed=lambda error: self._browser_show_error(
                    f"浏览器启动失败：{error}"
                ),
            )
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            self._browser_show_error(
                f"浏览器启动失败：{error}。源码运行请安装 tkwry==0.1.9，"
                "并确认系统已安装 WebView2 Runtime。"
            )

    def _browser_action(self, name: str) -> None:
        if self._browser_web is None:
            self._ensure_browser_view()
            return
        try:
            getattr(self._browser_web, name)()
        except (OSError, RuntimeError, ValueError) as error:
            self._browser_show_error(f"网页操作失败：{error}")

    def _browser_back(self) -> None:
        self._browser_action("go_back")

    def _browser_forward(self) -> None:
        self._browser_action("go_forward")

    def _browser_reload(self) -> None:
        if self._browser_web is not None and getattr(
            self._browser_web, "creation_failed", False
        ):
            self._browser_web.destroy()
            self._browser_web = None
            self.browser_error_label.pack_forget()
            self.browser_host.pack(fill="both", expand=True)
            self._ensure_browser_view()
        else:
            self._browser_action("reload")

    def _on_note_modified(self, _event: tk.Event) -> None:
        if not self.note_text.edit_modified():
            return
        self.note_text.edit_modified(False)
        if self._syncing_task:
            return
        self.task.note = self.note_text.get("1.0", "end-1c")
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
                _todo_display_text(item) for item in self.todo_items
            ) or "暂无待办"
        elif self.mode == "任务胶囊":
            index = self._focus_task_index
            title = self.todo_items[index][0] if index is not None else "未选择任务"
            remaining = max(0, math.ceil(self._focus_remaining_seconds))
            minutes, seconds = divmod(remaining, 60)
            content = (title, f"{minutes:02d}:{seconds:02d}")
        elif self.mode == "倒计时":
            content = str(self.timer_label.cget("text"))
        elif self.mode == "快捷按键":
            content = " · ".join(
                f"{label}（{hint}）"
                for label, hint, _action, _icon in self._shortcut_definitions()
            )
        elif self.mode == "浏览器":
            content = self.browser_url
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
        elif self.mode == "任务胶囊":
            title, remaining = content
            self._draw_outlined_text(
                title,
                canvas_width // 2,
                canvas_height // 3,
                font=("Microsoft YaHei UI", 12, "bold"),
                width=canvas_width - 24,
            )
            self._draw_outlined_text(
                remaining,
                canvas_width // 2,
                canvas_height * 2 // 3,
                font=("Segoe UI", 28, "bold"),
                large=True,
            )
        elif self.mode == "倒计时":
            self._draw_outlined_text(
                content,
                canvas_width // 2,
                canvas_height // 2,
                font=("Segoe UI", 30, "bold"),
                large=True,
            )
        elif self.mode == "快捷按键":
            self._draw_outlined_text(
                content,
                canvas_width // 2,
                canvas_height // 2,
                font=("Microsoft YaHei UI", 12, "bold"),
                width=canvas_width - 24,
            )
        elif self.mode == "浏览器":
            hostname = urllib.parse.urlsplit(content).hostname or "网页"
            self._draw_outlined_text(
                f"{hostname}\n{content}",
                canvas_width // 2,
                canvas_height // 2,
                font=("Microsoft YaHei UI", 11, "bold"),
                width=canvas_width - 24,
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
            self.focus_header.pack_forget()
            self.focus_time_label.pack_forget()
            self.focus_actions.pack_forget()
            self.timer_label.pack_forget()
            self.clock_time_label.pack_forget()
            self.clock_date_label.pack_forget()
            self.shortcut_buttons_frame.pack_forget()
            self.browser_toolbar.pack_forget()
            self.browser_host.pack_forget()
            self.browser_error_label.pack_forget()
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
            self.focus_header.pack(fill="x")
            self.focus_actions.pack(side="bottom", fill="x")
            self.focus_time_label.pack(expand=True)
            self.timer_label.pack(expand=True)
            self.clock_time_label.pack(expand=True)
            self.clock_date_label.pack(pady=(0, 8))
            self.shortcut_buttons_frame.pack(fill="x")
            self.browser_toolbar.pack(fill="x", pady=(0, 6))
            if self.browser_error_label.cget("text"):
                self.browser_error_label.pack(fill="x", pady=(0, 5))
            self.browser_host.pack(fill="both", expand=True)
            self._outline_snapshot = None
            if self.mode == "浏览器":
                self.root.after_idle(self._ensure_browser_view)

    def _add_todo(self, _event: tk.Event | None = None) -> None:
        title = self.todo_input.get().strip()
        if not title:
            return
        editing = self._editing_todo_index
        if editing is not None and 0 <= editing < len(self.todo_items):
            item = self.todo_items[editing]
            self.todo_items[editing] = (title, item[1], item[2], item[3])
            self._cancel_todo_edit()
            self._render_todos(editing)
            self._update_focus_display()
        else:
            self.todo_input.delete(0, "end")
            self.add_todo_text(title)
            return
        self._notify_state_changed()

    def add_todo_text(self, title: str) -> None:
        title = " ".join(title.split())
        if not title:
            return
        self.todo_items.append((title, False, None, time.time()))
        self._render_todos(len(self.todo_items) - 1)
        self._notify_state_changed()

    def append_note_text(self, value: str) -> None:
        value = value.strip()
        if not value:
            return
        existing = self.note_text.get("1.0", "end-1c")
        self.note_text.insert("end", ("\n\n" if existing.strip() else "") + value)
        self.task.note = self.note_text.get("1.0", "end-1c")
        self._refresh_outlined_content()
        self._notify_state_changed()

    def _edit_todo(self, _event: tk.Event | None = None) -> None:
        selected = self._selected_todo_index()
        if selected is None:
            return
        self._editing_todo_index = selected
        self.todo_input.delete(0, "end")
        self.todo_input.insert(0, self.todo_items[selected][0])
        self.todo_add_button.configure(text="保存修改")
        self.todo_cancel_button.pack(side="right", padx=(0, 8), ipady=2)
        self.todo_input.focus_set()
        self.todo_input.selection_range(0, "end")

    def _cancel_todo_edit(self) -> None:
        self._editing_todo_index = None
        self.todo_input.delete(0, "end")
        self.todo_add_button.configure(text="添加")
        self.todo_cancel_button.pack_forget()

    def _selected_todo_index(self) -> int | None:
        selection = self.todo_list.curselection()
        return int(selection[0]) if selection else None

    def _render_todos(self, selected: int | None = None) -> None:
        self.todo_list.delete(0, "end")
        for item in self.todo_items:
            self.todo_list.insert("end", _todo_display_text(item))
        self._apply_todo_styles(force=True)
        if selected is not None and 0 <= selected < len(self.todo_items):
            self.todo_list.selection_set(selected)
        self._refresh_outlined_content()

    def _apply_todo_styles(self, *, notify: bool = False, force: bool = False) -> None:
        now = time.time()
        overdue_states: list[bool] = []
        for index, item in enumerate(self.todo_items):
            overdue = item[2] is not None and not item[1] and item[2] <= now
            overdue_states.append(overdue)
            if overdue and notify and self.on_todo_due is not None:
                self.on_todo_due(self, index)
        states = tuple(overdue_states)
        if force or states != self._todo_overdue_state:
            self._todo_overdue_state = states
            list_count = self.todo_list.size()
            for index, overdue in enumerate(states):
                if index >= list_count:
                    break
                self.todo_list.itemconfig(
                    index,
                    fg=DUE_OVERDUE if overdue else TEXT,
                )

    def _request_todo_due(self) -> None:
        selected = self._selected_todo_index()
        if selected is None:
            return
        title, done, due, created = self.todo_items[selected]
        accepted, value = _prompt_todo_due(
            self.root,
            title,
            due if due is not None else created,
        )
        if not accepted:
            return
        self.todo_items[selected] = (title, done, value, created)
        self._render_todos(selected)
        self._update_focus_display()
        self._notify_state_changed()

    def _toggle_todo(self, _event: tk.Event | None = None) -> None:
        selected = self._selected_todo_index()
        if selected is None:
            return
        title, done, due, created = self.todo_items[selected]
        self.todo_items[selected] = (title, not done, due, created)
        self._render_todos(selected)
        self._update_focus_display()
        self._notify_state_changed()

    def _delete_todo(self, _event: tk.Event | None = None) -> None:
        selected = self._selected_todo_index()
        if selected is None:
            return
        del self.todo_items[selected]
        if self._editing_todo_index == selected:
            self._cancel_todo_edit()
        elif self._editing_todo_index is not None and selected < self._editing_todo_index:
            self._editing_todo_index -= 1
        if self._focus_task_index == selected:
            self._focus_task_index = None
            self._focus_deadline = None
            self._focus_status = "ready"
            if self.mode == "任务胶囊":
                self.set_mode("待办")
        elif self._focus_task_index is not None and selected < self._focus_task_index:
            self._focus_task_index -= 1
        self._render_todos(min(selected, len(self.todo_items) - 1))
        self._update_focus_display()
        self._notify_state_changed()

    def _start_focus_for_selected(self) -> None:
        selected = self._selected_todo_index()
        if selected is None:
            return
        self._focus_task_index = selected
        self._focus_remaining_seconds = self._timer_minutes_value() * 60
        self._focus_deadline = time.monotonic() + self._focus_remaining_seconds
        self._focus_status = "running"
        self._update_focus_display()
        self._notify_state_changed()
        self.set_mode("任务胶囊")

    def _toggle_focus(self) -> None:
        if self._focus_task_index is None:
            return
        if self._focus_deadline is not None:
            self._focus_remaining_seconds = max(
                0, self._focus_deadline - time.monotonic()
            )
            self._focus_deadline = None
            self._focus_status = "paused"
        else:
            if self._focus_status in ("ready", "finished"):
                self._focus_remaining_seconds = self._timer_minutes_value() * 60
            self._focus_deadline = time.monotonic() + self._focus_remaining_seconds
            self._focus_status = "running"
        self._update_focus_display()
        self._notify_state_changed()

    def _reset_focus(self) -> None:
        if self._focus_task_index is None:
            return
        self._focus_deadline = None
        self._focus_remaining_seconds = self._timer_minutes_value() * 60
        self._focus_status = "ready"
        self._update_focus_display()
        self._notify_state_changed()

    def _complete_focus(self) -> None:
        index = self._focus_task_index
        if index is None:
            return
        title, _done, due, created = self.todo_items[index]
        self.todo_items[index] = (title, True, due, created)
        self._focus_deadline = None
        self._focus_status = "finished"
        self._render_todos(index)
        self._update_focus_display()
        self._notify_state_changed()

    def _update_focus_display(self) -> None:
        index = self._focus_task_index
        if index is not None and 0 <= index < len(self.todo_items):
            title, done = self.todo_items[index][0], self.todo_items[index][1]
            short_title = title[:44] + ("…" if len(title) > 44 else "")
            self.focus_task_label.configure(text=f"{'☑' if done else '☐'}  {short_title}")
        else:
            self.focus_task_label.configure(text="从待办中选择任务")
        seconds = max(0, math.ceil(self._focus_remaining_seconds))
        minutes, seconds = divmod(seconds, 60)
        self.focus_time_label.configure(
            text=f"{minutes:02d}:{seconds:02d}",
            fg=ACCENT if self._focus_status == "finished" else TEXT,
        )
        self.focus_start_button.configure(
            text=("暂停" if self._focus_status == "running" else "继续" if self._focus_status == "paused" else "开始"),
            state="normal" if index is not None else "disabled",
        )
        self.focus_reset_button.configure(
            state="normal" if index is not None else "disabled"
        )
        self.focus_complete_button.configure(
            state="normal" if index is not None else "disabled"
        )
        self._refresh_outlined_content()

    def _on_timer_duration_changed(self, *_trace_arguments: str) -> None:
        if self._syncing_task:
            return
        try:
            minutes = int(self.timer_minutes.get())
        except (tk.TclError, ValueError):
            return
        if not 1 <= minutes <= 180:
            return
        self._timer_duration_minutes = minutes
        if self._focus_deadline is None and self._focus_status == "ready":
            self._focus_remaining_seconds = minutes * 60
            self._update_focus_display()
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
            self.task.timer_status = "paused"
        else:
            if self.task.timer_status in ("ready", "finished"):
                self._timer_remaining_seconds = self._timer_minutes_value() * 60
            self._timer_deadline = time.monotonic() + self._timer_remaining_seconds
            self.task.timer_status = "running"
        self._update_timer_display()
        self._notify_state_changed()

    def _reset_timer(self) -> None:
        self._timer_deadline = None
        self._timer_remaining_seconds = self._timer_minutes_value() * 60
        self.task.timer_status = "ready"
        self._update_timer_display()
        self._notify_state_changed()

    def _update_timer_display(self) -> None:
        remaining = max(0, math.ceil(self._timer_remaining_seconds))
        minutes, seconds = divmod(remaining, 60)
        self.timer_start_button.configure(
            text={
                "running": "暂停",
                "paused": "继续",
                "finished": "重新开始",
            }.get(self.task.timer_status, "开始")
        )
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
                self.task.timer_status = "finished"
                if self.visible:
                    self.root.bell()
                if self.on_timer_complete is not None:
                    self.on_timer_complete(self)
                self._notify_state_changed()
            self._update_timer_display()
        if self._focus_deadline is not None:
            self._focus_remaining_seconds = max(
                0, self._focus_deadline - time.monotonic()
            )
            if self._focus_remaining_seconds == 0:
                self._focus_deadline = None
                self._focus_status = "finished"
                if self.visible:
                    self.root.bell()
                if self.on_focus_complete is not None:
                    self.on_focus_complete(self)
                self._notify_state_changed()
            self._update_focus_display()
        self._apply_todo_styles(notify=True)
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

    def _build_shortcut_window(self) -> None:
        """Small icon buttons that appear below the collapsed ball."""
        self.shortcut_window = tk.Toplevel(self.root)
        self.shortcut_window.withdraw()
        self.shortcut_window.overrideredirect(True)
        self.shortcut_window.configure(bg=TRANSPARENT_KEY)
        self.shortcut_window.attributes("-topmost", True)
        try:
            self.shortcut_window.attributes("-toolwindow", True)
            self.shortcut_window.attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            pass

        self.shortcut_icon_shapes: list[tuple[tk.Canvas, int]] = []
        for label, _hint, action, icon in self._shortcut_definitions():
            canvas = tk.Canvas(
                self.shortcut_window,
                width=SHORTCUT_ICON_SIZE,
                height=SHORTCUT_ICON_SIZE,
                bg=TRANSPARENT_KEY,
                bd=0,
                highlightthickness=0,
                cursor="hand2",
            )
            canvas.pack(
                pady=(SHORTCUT_ICON_GAP if self.shortcut_icon_shapes else 0, 0)
            )
            shape = canvas.create_oval(
                2,
                2,
                SHORTCUT_ICON_SIZE - 2,
                SHORTCUT_ICON_SIZE - 2,
                fill=BG_TITLE,
                outline=ACCENT,
                width=2,
            )
            self._draw_shortcut_icon(canvas, icon)
            canvas.bind(
                "<Enter>",
                lambda _event, target=canvas, item=shape: self._shortcut_icon_hover(
                    target, item, True
                ),
            )
            canvas.bind(
                "<Leave>",
                lambda _event, target=canvas, item=shape: self._shortcut_icon_hover(
                    target, item, False
                ),
            )
            canvas.bind(
                "<ButtonRelease-1>",
                lambda _event, run=action: run(),
            )
            self.shortcut_icon_shapes.append((canvas, shape))

    def _shortcut_icon_hover(
        self,
        canvas: tk.Canvas,
        shape: int,
        hovered: bool,
    ) -> None:
        canvas.itemconfigure(
            shape,
            fill="#303844" if hovered else BG_TITLE,
            outline=ACCENT_HOVER if hovered else ACCENT,
        )

    def _draw_shortcut_icon(self, canvas: tk.Canvas, kind: str) -> None:
        unit = SHORTCUT_ICON_SIZE / 46
        if kind == "switch":
            canvas.create_rectangle(
                8 * unit,
                7 * unit,
                26 * unit,
                21 * unit,
                outline=TEXT_MUTED,
                width=2,
            )
            canvas.create_line(
                8 * unit,
                11 * unit,
                26 * unit,
                11 * unit,
                fill=TEXT_MUTED,
                width=2,
            )
            canvas.create_rectangle(
                17 * unit,
                15 * unit,
                35 * unit,
                29 * unit,
                outline=ACCENT,
                width=2,
            )
            canvas.create_line(
                17 * unit,
                19 * unit,
                35 * unit,
                19 * unit,
                fill=ACCENT,
                width=2,
            )

    def _sync_shortcut_window(self) -> None:
        if not hasattr(self, "shortcut_window") or not self.shortcut_window.winfo_exists():
            return
        if (
            not self.visible
            or not self.collapsed
            or self.animating
            or self.mode != "快捷按键"
            or self._ball_geometry is None
            or not self.shortcut_icon_shapes
        ):
            self.shortcut_window.withdraw()
            return

        count = len(self.shortcut_icon_shapes)
        height = count * SHORTCUT_ICON_SIZE + (count - 1) * SHORTCUT_ICON_GAP
        _, _, ball_x, ball_y = self._ball_geometry
        _monitor_area, work_area = _monitor_areas_at(
            ball_x + BALL_SIZE // 2,
            ball_y + BALL_SIZE // 2,
        )
        left, top, right, bottom = work_area
        x = _clamp(
            ball_x + (BALL_SIZE - SHORTCUT_ICON_SIZE) // 2,
            left + BALL_MARGIN,
            right - SHORTCUT_ICON_SIZE - BALL_MARGIN,
        )
        below_y = ball_y + BALL_SIZE + SHORTCUT_ICON_GAP
        above_y = ball_y - height - SHORTCUT_ICON_GAP
        if below_y + height <= bottom - BALL_MARGIN or above_y < top + BALL_MARGIN:
            y = below_y
        else:
            y = above_y
        y = _clamp(y, top + BALL_MARGIN, bottom - height - BALL_MARGIN)
        _set_absolute_geometry(
            self.shortcut_window,
            width=SHORTCUT_ICON_SIZE,
            height=height,
            x=x,
            y=y,
        )
        self.shortcut_window.deiconify()
        self.shortcut_window.attributes("-topmost", True)
        self.shortcut_window.lift()
        _set_native_topmost(self.shortcut_window)

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
        self.shortcut_window.withdraw()
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
        self._sync_shortcut_window()
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
        self.shortcut_window.withdraw()
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
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
        if self.mode == "浏览器":
            self.root.after_idle(self._ensure_browser_view)
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
        self._sync_shortcut_window()
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
            if self.mode != "浏览器":
                self.status_label.pack(pady=(10, 2), before=self.mode_container)
                self.message_label.pack(before=self.mode_container)
            self.todo_entry_row.pack(
                fill="x",
                pady=(0, 5),
            )
            self._set_outlined_view(False)
            self.todo_actions.pack(
                side="bottom",
                fill="x",
                pady=(4, 0),
                before=self.todo_list,
            )
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
                text=f"●  {self.mode} · 任务 #{self.task_id} · 已锁定",
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
                text=f"●  {self.mode} · 任务 #{self.task_id}",
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
            if self.shortcut_window.winfo_exists():
                self.shortcut_window.destroy()
        except (AttributeError, tk.TclError):
            pass
        if self._browser_web is not None:
            self._browser_web.destroy()
            self._browser_web = None
        if self._browser_owned_session is not None:
            self._browser_owned_session.close()
            self._browser_owned_session = None
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

    def set_overlay_visible(self, visible: bool) -> None:
        """Temporarily hide every surface without changing saved window state."""
        if self._closed:
            return
        self.visible = visible
        if not visible:
            for surface in (
                self.root, self.ball_window, self.lock_window,
                self.shortcut_window,
            ):
                surface.withdraw()
            return
        if self.animating:
            # The animation completion handler restores the appropriate surface.
            return
        if self.collapsed:
            self.root.withdraw()
            self.ball_window.deiconify()
            self.ball_window.attributes("-topmost", True)
            _set_native_topmost(self.ball_window)
            self._sync_shortcut_window()
        else:
            self.ball_window.withdraw()
            self.shortcut_window.withdraw()
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            _set_native_topmost(self.root)
            self._sync_lock_window()
            if self.mode == "浏览器":
                self.root.after_idle(self._ensure_browser_view)

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
        self.overlays_hidden = False
        self._hidden_auxiliary: dict[str, bool] = {}
        self._hide_hotkey_error: str | None = None
        self.windows: list[OverlayApp] = []
        self._browser_session: object | None = None
        self.settings_window: tk.Toplevel | None = None
        self.quick_capture_window: tk.Toplevel | None = None
        self.quick_capture_text: tk.Text | None = None

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
        stored_tasks = self.window_store.load_tasks()
        if stored_tasks is None:
            self._tasks = {
                int(record["task_id"]): TaskState.from_record(
                    int(record["task_id"]), record
                )
                for record in self._window_records
            }
            for record in self._window_records:
                for key in (
                    "note", "todos", "focus_task_index", "focus_status",
                    "focus_remaining_seconds", "timer_minutes",
                ):
                    record.pop(key, None)
        else:
            self._tasks = {
                int(record["id"]): TaskState.from_record(int(record["id"]), record)
                for record in stored_tasks
            }
        for record in self._window_records:
            task_id = int(record["task_id"])
            self._tasks.setdefault(task_id, TaskState(task_id))
        self._task_snapshots = {
            task_id: task.snapshot() for task_id, task in self._tasks.items()
        }
        startup_now = time.time()
        self._notified_todo_dues: set[tuple[int, float | None, float]] = {
            (task_id, created, due)
            for task_id, task in self._tasks.items()
            for _title, done, due, created in task.todos
            if not done and due is not None and due <= startup_now
        }
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
        self.hide_hotkey = str(saved_settings["hide_hotkey"])
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
            on_capture=self.open_quick_capture,
            on_toggle_visibility=self.toggle_overlays_hidden,
            on_second_launch=self._handle_second_launch,
            on_exit=self.exit_app,
            hide_hotkey=self.hide_hotkey,
            show_icon=tray_enabled,
        )
        if tray_enabled and not self.tray.hide_hotkey_registered:
            self._hide_hotkey_error = (
                f"{self.hide_hotkey} 已被其他程序占用；请在设置中修改快捷隐藏键。"
            )

        if stored_tasks is None and self._window_records:
            self._schedule_window_states_save()

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

    def _handle_second_launch(self) -> None:
        if self._exiting:
            return
        restored_hidden_windows = self.overlays_hidden
        if self.overlays_hidden:
            self.toggle_overlays_hidden()
        if not self.windows:
            target = self.add_window()
        else:
            target = self.windows[-1]
            target.set_overlay_visible(self.visible)
        if self.visible:
            surface = target.ball_window if target.collapsed else target.root
            try:
                surface.deiconify()
                surface.attributes("-topmost", True)
                surface.lift()
                if not target.collapsed and not target.locked:
                    surface.focus_force()
            except tk.TclError:
                pass
        message = (
            "已恢复原有窗口，不会启动第二个后台实例。"
            if restored_hidden_windows else
            "已切换到正在运行的实例，不会重复启动。"
        )
        self.tray.notify("DesktopTools 已在运行", message)

    def toggle_overlays_hidden(self) -> None:
        if self._exiting:
            return
        self.overlays_hidden = not self.overlays_hidden
        if self.overlays_hidden:
            self._hidden_auxiliary.clear()
            for name in ("settings_window", "quick_capture_window"):
                surface = getattr(self, name)
                try:
                    was_visible = surface is not None and surface.winfo_exists() and surface.state() == "normal"
                    self._hidden_auxiliary[name] = was_visible
                    if was_visible:
                        surface.withdraw()
                except tk.TclError:
                    self._hidden_auxiliary[name] = False
        for window in tuple(self.windows):
            window.set_overlay_visible(self.visible and not self.overlays_hidden)
        if not self.overlays_hidden:
            self._refresh_backgrounds()
            for name, was_visible in self._hidden_auxiliary.items():
                surface = getattr(self, name)
                try:
                    if was_visible and surface is not None and surface.winfo_exists() and surface.state() == "withdrawn":
                        surface.deiconify()
                        surface.attributes("-topmost", True)
                except tk.TclError:
                    pass
            self._hidden_auxiliary.clear()

    def add_window(
        self,
        initial_position: tuple[int, int] | None = None,
        *,
        task_id: int | None = None,
    ) -> OverlayApp:
        saved_state = None
        if initial_position is None and task_id is None:
            saved_state = min(
                (
                    record for record in self._window_records
                    if not record["active"]
                ),
                key=lambda record: int(record["id"]),
                default=None,
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

        return self._open_window(
            None, initial_position=initial_position, task_id=task_id
        )

    def _get_browser_session(self) -> object:
        if self._browser_session is None:
            from tkwry import WebSession

            browser_directory = self.settings_store.path.parent / "browser"
            browser_directory.mkdir(parents=True, exist_ok=True)
            self._browser_session = WebSession(data_directory=browser_directory)
        return self._browser_session

    def _open_window(
        self,
        saved_state: dict[str, object] | None,
        *,
        initial_position: tuple[int, int] | None = None,
        task_id: int | None = None,
    ) -> OverlayApp:
        instance_number = (
            int(saved_state["id"])
            if saved_state is not None
            else self._next_instance_number
        )
        resolved_task_id = (
            int(saved_state["task_id"])
            if saved_state is not None
            else task_id if task_id is not None else instance_number
        )
        task = self._tasks.setdefault(
            resolved_task_id, TaskState(resolved_task_id)
        )

        window = OverlayApp(
            visible=self.visible and not self.overlays_hidden,
            initial_position=initial_position,
            master=self.root,
            on_close=self._on_window_closed,
            opacity_percent=self.opacity_percent,
            edge_collapse_enabled=self.edge_collapse_enabled,
            restore_margin=self.restore_margin,
            no_background=self.no_background,
            instance_number=instance_number,
            saved_state=saved_state,
            task=task,
            on_state_change=self._on_window_state_changed,
            on_focus_complete=self._on_focus_complete,
            on_timer_complete=self._on_timer_complete,
            on_bind_task=self.bind_window_to_task,
            on_list_tasks=self._task_summaries,
            on_todo_due=self._on_todo_due,
            browser_session_factory=self._get_browser_session,
        )
        if saved_state is None:
            self._next_instance_number += 1
        self.windows.append(window)
        self._on_window_state_changed(window)
        self._save_window_states_now()
        self._update_instance_count()
        return window

    def bind_window_to_task(self, window: OverlayApp, task_id: int) -> None:
        if type(task_id) is not int or task_id < 1:
            raise ValueError("任务编号必须是正整数")
        if window not in self.windows:
            return
        task = self._tasks.setdefault(task_id, TaskState(task_id))
        window.bind_task(task)

    def _task_summaries(self) -> list[TaskState]:
        return [task for _task_id, task in sorted(self._tasks.items())]

    def _on_window_state_changed(self, window: OverlayApp) -> None:
        if self._exiting:
            return
        snapshot = window.state_snapshot()
        task_snapshot = window.task.snapshot()
        previous_task = self._task_snapshots.get(window.task_id)
        task_changed = previous_task != task_snapshot
        if task_changed:
            self._task_snapshots[window.task_id] = task_snapshot
            visual_changed = previous_task is None or any(
                previous_task.get(key) != task_snapshot.get(key)
                for key in (
                    "note", "todos", "focus_task_index", "focus_status",
                    "timer_minutes", "timer_status",
                )
            )
            if visual_changed:
                for peer in self.windows:
                    if peer is not window and peer.task is window.task:
                        peer.refresh_from_task()
        window_changed = True
        for index, record in enumerate(self._window_records):
            if record["id"] == window.instance_number:
                window_changed = record != snapshot
                self._window_records[index] = snapshot
                break
        else:
            self._window_records.append(snapshot)
        if task_changed or window_changed:
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
            self.window_store.save(
                self._window_records,
                [task.snapshot() for _, task in sorted(self._tasks.items())],
            )
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
            if not any(peer.task is window.task for peer in self.windows):
                task = window.task
                if task.focus_deadline is not None:
                    task.focus_remaining_seconds = max(
                        0, task.focus_deadline - time.monotonic()
                    )
                    task.focus_deadline = None
                    task.focus_status = "paused"
                if task.timer_deadline is not None:
                    task.timer_remaining_seconds = max(
                        0, task.timer_deadline - time.monotonic()
                    )
                    task.timer_deadline = None
                    task.timer_status = "paused"
                self._task_snapshots[task.id] = task.snapshot()
            for index, record in enumerate(self._window_records):
                if record["id"] == window.instance_number:
                    self._window_records.pop(index)
                    record["active"] = False
                    self._window_records.append(record)
                    break
            self._schedule_window_states_save()
            self._save_window_states_now()
        self._update_instance_count()

    def _on_focus_complete(self, window: OverlayApp) -> None:
        index = window._focus_task_index
        if index is None or not 0 <= index < len(window.todo_items):
            return
        self.tray.notify(
            "专注时间到了",
            f"{window.todo_items[index][0][:100]} —— 可以标记完成了",
        )

    def _on_timer_complete(self, window: OverlayApp) -> None:
        self.tray.notify(
            "倒计时结束",
            f"自由窗口 #{window.instance_number}（任务 #{window.task_id}）的倒计时已结束。",
        )

    def _on_todo_due(self, window: OverlayApp, index: int) -> None:
        task = window.task
        if not 0 <= index < len(task.todos):
            return
        title, done, due, created = task.todos[index]
        if done or due is None or due > time.time():
            return
        key = (task.id, created, due)
        if key in self._notified_todo_dues:
            return
        self._notified_todo_dues.add(key)
        self.tray.notify(
            "待办已到期",
            f"{title[:100]} —— 截止 {_format_due_timestamp(due)}",
        )

    def open_quick_capture(self, *, prefill_clipboard: bool = True) -> None:
        if self._exiting:
            return
        if self.quick_capture_window is not None and self.quick_capture_window.winfo_exists():
            if self.visible:
                self.quick_capture_window.deiconify()
                self.quick_capture_window.lift()
                self.quick_capture_text.focus_force()
            return

        window = tk.Toplevel(self.root)
        self.quick_capture_window = window
        if not self.visible:
            window.withdraw()
        window.title("DesktopTools 快速收集")
        window.configure(bg=BG_BODY)
        window.resizable(False, False)
        window.attributes("-topmost", True)
        try:
            window.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        window.protocol("WM_DELETE_WINDOW", self.close_quick_capture)
        window.bind("<Escape>", lambda _event: self.close_quick_capture())

        tk.Label(
            window,
            text="快速收集",
            bg=BG_BODY,
            fg=TEXT,
            font=("Microsoft YaHei UI", 12, "bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 4))
        tk.Label(
            window,
            text=(
                "Ctrl+Alt+D 随时唤出；复制的文字会自动填入"
                if self.tray.hotkey_registered
                else "可从托盘菜单唤出；复制的文字会自动填入"
            ),
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 8))
        self.quick_capture_text = tk.Text(
            window,
            height=4,
            wrap="word",
            bg=BG_PANEL,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            bd=0,
            font=("Microsoft YaHei UI", 10),
            padx=8,
            pady=6,
        )
        self.quick_capture_text.pack(fill="x", padx=18)
        if prefill_clipboard:
            try:
                copied = self.root.clipboard_get()
            except tk.TclError:
                copied = ""
            if isinstance(copied, str) and len(copied) <= 20_000:
                self.quick_capture_text.insert("1.0", copied)

        self.quick_capture_status = tk.Label(
            window,
            text="存入最近的同类窗口；没有时会新建。",
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 8),
            anchor="w",
        )
        self.quick_capture_status.pack(fill="x", padx=18, pady=(7, 6))
        actions = tk.Frame(window, bg=BG_BODY)
        actions.pack(fill="x", padx=18, pady=(0, 16))
        for label, destination in (
            ("加入待办", "待办"),
            ("追加到便签", "便签"),
        ):
            tk.Button(
                actions,
                text=label,
                command=lambda kind=destination: self._save_quick_capture(kind),
                bg=ACCENT if destination == "待办" else BG_PANEL,
                fg="#102219" if destination == "待办" else TEXT,
                relief="flat",
                bd=0,
                padx=12,
                pady=5,
                font=("Microsoft YaHei UI", 9),
                cursor="hand2",
            ).pack(side="left", padx=(0, 8))
        tk.Button(
            actions,
            text="取消",
            command=self.close_quick_capture,
            bg=BG_PANEL,
            fg=TEXT_MUTED,
            relief="flat",
            bd=0,
            padx=12,
            pady=5,
            font=("Microsoft YaHei UI", 9),
            cursor="hand2",
        ).pack(side="right")

        width, height = 420, 236
        cursor = Point()
        user32.GetCursorPos(ctypes.byref(cursor))
        _monitor, (left, top, right, bottom) = _monitor_areas_at(cursor.x, cursor.y)
        x = _clamp(cursor.x + 14, left, right - width)
        y = _clamp(cursor.y + 14, top, bottom - height)
        _set_absolute_geometry(window, width=width, height=height, x=x, y=y)
        if self.visible:
            window.deiconify()
            window.lift()
            self.quick_capture_text.focus_force()

    def _save_quick_capture(self, destination: str) -> None:
        if self.quick_capture_text is None:
            return
        content = self.quick_capture_text.get("1.0", "end-1c").strip()
        if not content or len(content) > 20_000:
            self.quick_capture_status.configure(
                text="请输入内容（最多 20,000 字符）。",
                fg=CLOSE_HOVER,
            )
            return
        mode = "待办" if destination == "待办" else "便签"
        target = next(
            (
                window
                for window in reversed(self.windows)
                if window.mode == mode
                or (mode == "待办" and window.mode == "任务胶囊")
            ),
            None,
        )
        if target is None:
            cursor = Point()
            user32.GetCursorPos(ctypes.byref(cursor))
            target = self.add_window(initial_position=(cursor.x, cursor.y))
            target.set_mode(mode)
        if mode == "待办":
            target.add_todo_text(content)
        else:
            target.append_note_text(content)
        self._save_window_states_now()
        self.tray.notify("快速收集已保存", f"已存入自由窗口 #{target.instance_number} 的{mode}")
        self.close_quick_capture()

    def close_quick_capture(self) -> None:
        if self.quick_capture_window is not None:
            try:
                if self.quick_capture_window.winfo_exists():
                    self.quick_capture_window.destroy()
            except tk.TclError:
                pass
        self.quick_capture_window = None
        self.quick_capture_text = None

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
        ).pack(fill="x", padx=22, pady=(10, 3))

        self.instance_count_label = tk.Label(
            window,
            text="",
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        )
        self.instance_count_label.pack(fill="x", padx=22, pady=(0, 6))

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
        ).pack(fill="x", padx=20, pady=(1, 5))

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
        ).pack(fill="x", padx=18, pady=(0, 4))

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
        ).pack(fill="x", padx=18, pady=(0, 4))

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
        ).pack(fill="x", padx=18, pady=(0, 4))

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
        ).pack(fill="x", padx=18, pady=(0, 4))

        hotkey_row = tk.Frame(window, bg=BG_BODY)
        hotkey_row.pack(fill="x", padx=22, pady=(0, 3))
        tk.Label(
            hotkey_row,
            text="快捷隐藏快捷键",
            bg=BG_BODY,
            fg=TEXT,
            font=("Microsoft YaHei UI", 10),
        ).pack(side="left")
        self.hide_hotkey_input = tk.StringVar(master=window, value=self.hide_hotkey)
        hotkey_entry = tk.Entry(
            hotkey_row,
            textvariable=self.hide_hotkey_input,
            width=15,
            bg=BG_PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 10),
        )
        hotkey_entry.pack(side="left", padx=(10, 6), ipady=4)
        hotkey_entry.bind("<Return>", lambda _event: self.apply_hide_hotkey())
        tk.Button(
            hotkey_row,
            text="应用",
            command=self.apply_hide_hotkey,
            bg=BG_TITLE,
            fg=ACCENT,
            relief="flat",
            bd=0,
            cursor="hand2",
        ).pack(side="right")
        tk.Label(
            window,
            text="按一次全部隐藏，再按一次恢复；如 Ctrl+K、Ctrl+Shift+H。",
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 8),
            anchor="w",
            justify="left",
            wraplength=400,
        ).pack(fill="x", padx=22, pady=(0, 5))

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
        self.settings_note_label.pack(fill="x", padx=22, pady=(8, 8))
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
        self.update_status_label.pack(fill="x", padx=22, pady=(0, 8))

        actions = tk.Frame(window, bg=BG_BODY)
        actions.pack(fill="x", padx=22, pady=(0, 12))
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
        settings_height = 650
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

    def apply_hide_hotkey(self, binding: str | None = None) -> bool:
        value = binding if binding is not None else self.hide_hotkey_input.get()
        try:
            canonical, _modifiers, _virtual_key = _parse_hide_hotkey(value)
        except ValueError as error:
            self._hide_hotkey_error = str(error)
            self._update_settings_note()
            return False
        if not self.tray.set_hide_hotkey(canonical):
            self._hide_hotkey_error = f"{canonical} 已被其他程序占用，请换一个组合键。"
            self._update_settings_note()
            return False
        self.hide_hotkey = canonical
        if hasattr(self, "hide_hotkey_input"):
            self.hide_hotkey_input.set(canonical)
        self._hide_hotkey_error = None
        self._schedule_settings_save()
        self._update_settings_note()
        return True

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
        elif self._hide_hotkey_error:
            message = self._hide_hotkey_error
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
                    or self._hide_hotkey_error
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

    def _current_settings(self) -> dict[str, int | bool | str]:
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
            "hide_hotkey": self.hide_hotkey,
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
        self.apply_hide_hotkey(str(SettingsStore.DEFAULTS["hide_hotkey"]))
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
        self.close_quick_capture()
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
        if self._browser_session is not None:
            self._browser_session.close()
            self._browser_session = None
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
    mutex_name = (
        f"Local\\FennecMomo.DesktopTools.SelfTest."
        f"{kernel32.GetCurrentProcessId()}.{time.time_ns()}"
    )
    first_guard = SingleInstanceGuard(mutex_name)
    second_guard = SingleInstanceGuard(mutex_name)
    assert first_guard.acquire(), "first process could not acquire instance mutex"
    assert not second_guard.acquire(), "duplicate process acquired instance mutex"
    first_guard.close()
    replacement_guard = SingleInstanceGuard(mutex_name)
    assert replacement_guard.acquire(), "instance mutex was not released on exit"
    replacement_guard.close()

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

    def todo_faces(
        items: list[tuple[str, bool, float | None, float | None]],
    ) -> list[tuple[str, bool]]:
        return [(title, done) for title, done, _due, _created in items]

    app = OverlayApp(visible=False)
    app.root.update()
    assert _position_from_arguments(["--position", "-120", "80"]) == (-120, 80)
    assert _browser_destination("example.com/docs") == "https://example.com/docs"
    assert _parse_hide_hotkey("ctrl+k") == ("Ctrl+K", MOD_CONTROL, ord("K"))
    assert _parse_hide_hotkey("shift + ctrl + f12") == (
        "Ctrl+Shift+F12", MOD_CONTROL | MOD_SHIFT, 0x7B
    )
    for invalid_hotkey in ("K", "Shift+K", "Ctrl+Alt+D", "Ctrl+K+K"):
        try:
            _parse_hide_hotkey(invalid_hotkey)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe hide hotkey was accepted: {invalid_hotkey}")
    assert _browser_destination("localhost:8000") == "http://localhost:8000"
    assert _browser_destination("找资料") == "https://www.bing.com/search?q=%E6%89%BE%E8%B5%84%E6%96%99"
    try:
        _browser_destination("javascript:alert(1)")
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe browser URL was accepted")
    assert app.mode == "便签"
    app.set_mode("浏览器")
    app.browser_address.set("example.com/docs")
    app._browser_navigate()
    assert app.state_snapshot()["browser_url"] == "https://example.com/docs"
    assert app._browser_web is None, "hidden self-test opened a browser"
    app.set_mode("便签")
    app.note_text.insert("1.0", "临时想法")
    app.mode_menu.invoke(1)
    assert app.mode == "待办", "mode menu did not switch the window purpose"
    assert max(
        row.winfo_reqwidth() for row in app.todo_actions.winfo_children()
    ) <= MIN_WIDTH - 60, "待办操作按钮在最小窗口宽度下放不下"
    app.todo_input.insert(0, "检查切换")
    app._add_todo()
    assert todo_faces(app.todo_items) == [("检查切换", False)]
    app.todo_list.selection_set(0)
    assert _due_epoch_from_fields(2026, 9, 22, 21, 30, 15) == time.mktime(
        (2026, 9, 22, 21, 30, 15, 0, 0, -1)
    )
    for invalid_due in ((2026, 2, 30, 0, 0, 0), (2026, 13, 1, 0, 0, 0)):
        try:
            _due_epoch_from_fields(*invalid_due)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid due date was accepted: {invalid_due}")
    original_prompt_due = globals()["_prompt_todo_due"]
    globals()["_prompt_todo_due"] = lambda *_args, **_kwargs: (True, time.time() - 5)
    try:
        app.todo_due_button.invoke()
    finally:
        globals()["_prompt_todo_due"] = original_prompt_due
    assert app.todo_items[0][2] is not None
    assert "⏰" in app.todo_list.get(0)
    app._apply_todo_styles(force=True)
    assert app.todo_list.itemcget(0, "fg") == DUE_OVERDUE
    globals()["_prompt_todo_due"] = lambda *_args, **_kwargs: (True, None)
    try:
        app.todo_due_button.invoke()
    finally:
        globals()["_prompt_todo_due"] = original_prompt_due
    assert app.todo_items[0][2] is None
    assert "⏰" not in app.todo_list.get(0)
    assert app.todo_list.itemcget(0, "fg") == TEXT
    app._toggle_todo()
    assert todo_faces(app.todo_items) == [("检查切换", True)]
    app.todo_edit_button.invoke()
    assert app.todo_input.get() == "检查切换"
    assert app.todo_add_button.cget("text") == "保存修改"
    app.todo_input.delete(0, "end")
    app.todo_input.insert(0, "修改后的待办")
    app.todo_add_button.invoke()
    assert todo_faces(app.todo_items) == [("修改后的待办", True)]
    assert app.todo_add_button.cget("text") == "添加"
    app._edit_todo()
    app.todo_input.delete(0, "end")
    app.todo_input.insert(0, "不保存")
    app.todo_cancel_button.invoke()
    assert todo_faces(app.todo_items) == [("修改后的待办", True)]
    app.todo_input.insert(0, "临时待办")
    app._add_todo()
    app.todo_list.selection_clear(0, "end")
    app.todo_list.selection_set(1)
    app.todo_delete_button.invoke()
    assert todo_faces(app.todo_items) == [("修改后的待办", True)]
    app.todo_list.selection_set(0)
    app._edit_todo()
    app.todo_input.delete(0, "end")
    app.todo_input.insert(0, "检查切换")
    app._add_todo()
    assert todo_faces(app.todo_items) == [("检查切换", True)]
    app.timer_minutes.set(1)
    app.todo_focus_button.invoke()
    assert app.mode == "任务胶囊"
    assert app._focus_task_index == 0
    assert app._focus_status == "running"
    assert app.focus_task_label.cget("text") == "☑  检查切换"
    app._toggle_focus()
    assert app._focus_status == "paused"
    assert 0 < app.task.snapshot()["focus_remaining_seconds"] <= 60
    app._toggle_focus()
    assert app._focus_status == "running"
    app._focus_deadline = time.monotonic() - 1
    focus_test_deadline = time.monotonic() + 1
    while app._focus_status != "finished" and time.monotonic() < focus_test_deadline:
        app.root.update()
        time.sleep(0.01)
    assert app._focus_status == "finished"
    app._complete_focus()
    assert todo_faces(app.todo_items) == [("检查切换", True)]
    app._reset_focus()
    assert app.focus_time_label.cget("text") == "01:00"
    app.set_locked(True)
    app.root.update()
    assert app._background_hidden
    assert "检查切换" in outlined_text(app)
    assert "01:00" in outlined_text(app)
    app.set_locked(False)
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
    app.set_mode("快捷按键")
    assert len(app.shortcut_buttons) == 1
    assert app.shortcut_buttons[0].cget("text") == "切换窗口（Alt+Tab）"
    global _activate_window, _switch_candidates
    assert isinstance(_switch_candidates(), list), "window list failed"
    original_activate_window = _activate_window
    original_switch_candidates = _switch_candidates
    switched_windows = []
    _switch_candidates = lambda: [101, 202, 303]
    _activate_window = lambda hwnd: switched_windows.append(hwnd) or True
    try:
        for _ in range(4):
            app.shortcut_buttons[0].invoke()
    finally:
        _activate_window = original_activate_window
        _switch_candidates = original_switch_candidates
    assert switched_windows == [202, 303, 101, 202], switched_windows
    app.set_mode("便签")
    assert app.note_text.get("1.0", "end-1c") == "临时想法"
    assert todo_faces(app.todo_items) == [("检查切换", True)]

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
    app.set_mode("快捷按键")
    assert app.shortcut_buttons_frame.winfo_manager() == ""
    assert "切换窗口（Alt+Tab）" in outlined_text(app)
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
    assert app.shortcut_buttons_frame.winfo_manager() == "pack"
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
    assert app.shortcut_window.state() == "withdrawn", (
        "invisible window showed shortcut icons"
    )
    app.close()

    shortcut_app = OverlayApp(visible=True)
    shortcut_app.set_mode("快捷按键")
    shortcut_app.root.update()
    assert shortcut_app.shortcut_window.state() == "withdrawn", (
        "shortcut icons appeared before the window collapsed"
    )
    cursor = Point()
    user32.GetCursorPos(ctypes.byref(cursor))
    monitor_area, _work_area = _monitor_areas_at(cursor.x, cursor.y)
    left, top, right, bottom = monitor_area
    dock_target = shortcut_app._ball_target_at_edge(
        right - 1,
        top + (bottom - top) // 2,
    )
    assert dock_target is not None, "display edge was not detected"
    ball_geometry, dock_edge = dock_target
    shortcut_app._collapse_to_ball(ball_geometry, dock_edge)
    deadline = time.monotonic() + 2
    while shortcut_app.animating and time.monotonic() < deadline:
        shortcut_app.root.update()
        time.sleep(0.01)
    assert shortcut_app.collapsed and not shortcut_app.animating
    assert shortcut_app.shortcut_window.state() == "normal", (
        "shortcut icons did not appear below the collapsed ball"
    )
    assert _native_window_geometry(shortcut_app.shortcut_window) == (
        SHORTCUT_ICON_SIZE,
        SHORTCUT_ICON_SIZE,
        ball_geometry[2] + (BALL_SIZE - SHORTCUT_ICON_SIZE) // 2,
        ball_geometry[3] + BALL_SIZE + SHORTCUT_ICON_GAP,
    ), _native_window_geometry(shortcut_app.shortcut_window)
    shortcut_app.set_mode("便签")
    assert shortcut_app.shortcut_window.state() == "withdrawn", (
        "shortcut icons stayed visible in another mode"
    )
    shortcut_app.set_mode("快捷按键")
    assert shortcut_app.shortcut_window.state() == "normal"
    shortcut_app._restore_from_ball()
    deadline = time.monotonic() + 2
    while shortcut_app.animating and time.monotonic() < deadline:
        shortcut_app.root.update()
        time.sleep(0.01)
    assert not shortcut_app.collapsed and not shortcut_app.animating
    assert shortcut_app.shortcut_window.state() == "withdrawn", (
        "shortcut icons stayed visible after restoring the window"
    )
    dock_target = shortcut_app._ball_target_at_edge(
        left + (right - left) // 2,
        bottom - 1,
    )
    assert dock_target is not None, "bottom display edge was not detected"
    ball_geometry, dock_edge = dock_target
    assert dock_edge == "bottom"
    shortcut_app._collapse_to_ball(ball_geometry, dock_edge)
    deadline = time.monotonic() + 2
    while shortcut_app.animating and time.monotonic() < deadline:
        shortcut_app.root.update()
        time.sleep(0.01)
    assert shortcut_app.collapsed and not shortcut_app.animating
    icon_width, icon_height, icon_x, icon_y = _native_window_geometry(
        shortcut_app.shortcut_window
    )
    assert icon_y + icon_height == ball_geometry[3] - SHORTCUT_ICON_GAP, (
        "shortcut icons did not move above the bottom-docked ball",
        (icon_x, icon_y, icon_width, icon_height),
        ball_geometry,
    )
    assert icon_x + icon_width <= right - BALL_MARGIN
    shortcut_app.close()

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

    try:
        from tkwry import WebView as _BrowserProbeDependency
    except ImportError:
        pass
    else:
        del _BrowserProbeDependency
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as browser_temp:
            browser_probe = OverlayApp(
                visible=True,
                master=visible_lock_app.root,
                browser_data_dir=Path(browser_temp) / "profile",
            )
            browser_probe.set_mode("浏览器")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and not (
                browser_probe._browser_web is not None
                and browser_probe._browser_web.ready
            ):
                browser_probe.root.update()
                time.sleep(0.02)
            assert browser_probe._browser_web is not None and browser_probe._browser_web.ready, (
                browser_probe.browser_error_label.cget("text")
            )
            browser_probe.set_locked(True)
            browser_probe.root.update()
            assert not browser_probe.browser_host.winfo_ismapped()
            assert browser_probe.click_through_style_is_set()
            browser_probe.set_locked(False)
            browser_probe.root.update()
            assert browser_probe.browser_host.winfo_ismapped()
            browser_probe.set_overlay_visible(False)
            browser_probe.root.update()
            assert browser_probe.root.state() == "withdrawn"
            browser_probe.set_overlay_visible(True)
            browser_probe.root.update()
            assert browser_probe.browser_host.winfo_ismapped()
            assert browser_probe._browser_web.ready
            browser_probe.close()
            visible_lock_app.root.update()
    visible_lock_app.close()

    temporary_settings_directory = tempfile.TemporaryDirectory()
    test_settings_path = (
        Path(temporary_settings_directory.name) / "DesktopTools" / "settings.json"
    )
    fake_package = b"MZ" + b"desktop-tools-update-test" * 128
    fake_manifest = {
        "version": "3.0.0",
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
    assert _version_numbers("2.3.1") > _version_numbers(APP_VERSION)
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
        user32.AppendMenuW(test_menu, MF_STRING, TRAY_COMMAND_CAPTURE, "快速收集")
        user32.AppendMenuW(test_menu, MF_STRING, TRAY_COMMAND_VISIBILITY, "隐藏/显示全部窗口")
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
    manager.tray._window_proc(
        manager.tray.hwnd,
        manager.tray._second_instance_message,
        0,
        0,
    )
    deadline = time.monotonic() + 1
    while manager.tray._pending_actions and time.monotonic() < deadline:
        manager.root.update()
        time.sleep(0.01)
    assert len(manager.windows) == 2, "second launch created duplicate windows"
    first_window, second_window = manager.windows
    first_window.note_text.insert("1.0", "第一扇便签")
    first_window.set_mode("待办")
    manager.root.update()
    assert first_window.todo_actions.winfo_ismapped(), (
        "todo edit/delete controls are hidden at the default window size"
    )
    assert first_window.todo_edit_button.winfo_ismapped()
    assert first_window.todo_delete_button.winfo_ismapped()
    assert (
        first_window.todo_actions.winfo_y()
        + first_window.todo_actions.winfo_height()
        <= first_window.mode_views["待办"].winfo_height()
    )
    first_window.todo_input.insert(0, "快捷键临时项")
    first_window.todo_add_button.invoke()
    manager.root.update()
    first_window.todo_list.focus_force()
    manager.root.update()
    first_window.todo_list.event_generate("<F2>")
    manager.root.update()
    assert first_window._editing_todo_index == 0
    first_window.todo_cancel_button.invoke()
    first_window.todo_list.focus_force()
    manager.root.update()
    first_window.todo_list.event_generate("<Delete>")
    manager.root.update()
    assert not first_window.todo_items
    first_window.todo_input.insert(0, "只属于第一个窗口")
    first_window._add_todo()
    first_window.todo_list.selection_set(0)
    first_window._toggle_todo()
    first_window._edit_todo()
    first_window.todo_input.delete(0, "end")
    first_window.todo_input.insert(0, "改好的待办")
    first_window._add_todo()
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
    saved_state = json.loads(state_path.read_text(encoding="utf-8"))
    saved_windows = saved_state["windows"]
    saved_tasks = {task["id"]: task for task in saved_state["tasks"]}
    assert saved_state["version"] == 2
    assert len(saved_windows) == 2
    assert saved_windows[0]["mode"] == "待办"
    assert saved_windows[0]["geometry"] == [470, 310, test_x, test_y], saved_windows[0]["geometry"]
    assert saved_windows[0]["task_id"] == first_window.instance_number
    assert saved_windows[1]["task_id"] == second_window.instance_number
    assert saved_tasks[first_window.task_id]["note"] == "第一扇便签"
    saved_todos = saved_tasks[first_window.task_id]["todos"]
    assert len(saved_todos) == 1
    assert saved_todos[0]["text"] == "改好的待办"
    assert saved_todos[0]["done"] is True
    assert saved_todos[0]["due"] is None
    assert type(saved_todos[0]["created"]) is float
    assert saved_tasks[first_window.task_id]["timer_minutes"] == 7
    assert saved_tasks[second_window.task_id]["note"] == "第二扇便签"
    assert not any(record["locked"] for record in saved_windows)
    legacy_state = dict(saved_windows[0])
    legacy_state.update(saved_tasks[first_window.task_id])
    legacy_state["id"] = first_window.instance_number
    legacy_state.pop("task_id")
    del legacy_state["locked"]
    legacy_path = test_settings_path.with_name("legacy-windows.json")
    legacy_path.write_text(
        json.dumps({"version": 1, "windows": [legacy_state]}),
        encoding="utf-8",
    )
    assert WindowStateStore(legacy_path).load()[0]["locked"] is False
    assert WindowStateStore(legacy_path).load_tasks() is None
    migrated_manager = DesktopManager(
        tray_enabled=False,
        visible=False,
        settings_path=test_settings_path.with_name("legacy-settings.json"),
        state_path=legacy_path,
        auto_start_store=MemoryAutoStartStore(),
        update_client=current_client,
    )
    assert migrated_manager.windows[0].task_id == first_window.instance_number
    assert todo_faces(migrated_manager.windows[0].todo_items) == [("改好的待办", True)]
    migrated_manager._save_window_states_now()
    migrated_state = json.loads(legacy_path.read_text(encoding="utf-8"))
    assert migrated_state["version"] == 2
    assert migrated_state["tasks"][0]["note"] == "第一扇便签"
    assert "todos" not in migrated_state["windows"][0]
    migrated_manager.exit_app()
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
    assert manager.settings_window.winfo_reqheight() <= 650, (
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
    assert todo_faces(revived_first.todo_items) == [("改好的待办", True)]
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
    assert todo_faces(reloaded_first.todo_items) == [("改好的待办", True)]
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
    assert reopened.instance_number == first_window.instance_number
    assert reopened.mode == "待办"
    assert reopened.note_text.get("1.0", "end-1c") == "第一扇便签"
    assert not reopened.locked
    second_closed = closed_reopen_manager.add_window()
    assert second_closed.instance_number == second_window.instance_number
    assert second_closed.mode == "便签"
    assert second_closed.note_text.get("1.0", "end-1c") == "第二扇便签"
    assert second_closed.locked
    assert second_closed.unlock_canvas.winfo_ismapped()
    third_window = closed_reopen_manager.add_window()
    assert third_window.instance_number == second_window.instance_number + 1
    reopened.close()
    third_window.close()
    restored_first = closed_reopen_manager.add_window()
    assert restored_first.instance_number == first_window.instance_number
    restored_third = closed_reopen_manager.add_window()
    assert restored_third.instance_number == third_window.instance_number
    assert closed_reopen_manager.auto_start.get() is True
    closed_reopen_manager.exit_app()

    capture_settings_path = (
        Path(temporary_settings_directory.name) / "Capture" / "settings.json"
    )
    capture_manager = DesktopManager(
        tray_enabled=False,
        visible=True,
        create_initial_window=False,
        settings_path=capture_settings_path,
        auto_start_store=MemoryAutoStartStore(),
        update_client=current_client,
    )
    assert not capture_manager.windows
    capture_manager.open_quick_capture(prefill_clipboard=False)
    assert capture_manager.quick_capture_text is not None
    capture_manager.quick_capture_text.insert("1.0", "快速收集的待办")
    capture_manager._save_quick_capture("待办")
    assert len(capture_manager.windows) == 1
    todo_window = capture_manager.windows[0]
    assert todo_window.mode == "待办"
    assert todo_window.task_id == todo_window.instance_number
    assert todo_faces(todo_window.todo_items) == [("快速收集的待办", False)]
    todo_window.timer_minutes.set(3)
    todo_window._start_focus_for_selected()
    assert len(capture_manager.windows) == 1, "开始专注不应额外生成窗口"
    focus_window = todo_window
    assert focus_window.mode == "任务胶囊"
    assert focus_window.instance_number == focus_window.task_id
    assert focus_window._focus_task_index == 0
    assert focus_window._focus_status == "running"
    assert 0 < focus_window._focus_remaining_seconds <= 180
    _set_absolute_geometry(
        focus_window.root,
        width=MIN_WIDTH,
        height=MIN_HEIGHT,
        x=focus_window.root.winfo_x(),
        y=focus_window.root.winfo_y(),
    )
    capture_manager.root.update()
    assert focus_window.focus_header.winfo_ismapped()
    assert focus_window.focus_actions.winfo_ismapped()
    assert (
        focus_window.focus_actions.winfo_x()
        + focus_window.focus_actions.winfo_width()
        <= focus_window.mode_views["任务胶囊"].winfo_width()
    )
    focus_window._toggle_focus()
    assert focus_window._focus_status == "paused"
    capture_manager.open_quick_capture(prefill_clipboard=False)
    capture_manager.quick_capture_text.insert("1.0", "第二项待办")
    capture_manager._save_quick_capture("待办")
    assert len(capture_manager.windows) == 1
    assert todo_faces(focus_window.todo_items) == [
        ("快速收集的待办", False), ("第二项待办", False)
    ]
    capture_manager.open_quick_capture(prefill_clipboard=False)
    capture_manager.quick_capture_text.insert("1.0", "第一段便签")
    capture_manager._save_quick_capture("便签")
    assert len(capture_manager.windows) == 2
    note_window = capture_manager.windows[-1]
    assert note_window.mode == "便签"
    assert note_window.task_id == note_window.instance_number
    capture_manager.open_quick_capture(prefill_clipboard=False)
    capture_manager.quick_capture_text.insert("1.0", "第二段便签")
    capture_manager._save_quick_capture("便签")
    assert len(capture_manager.windows) == 2
    assert note_window.note_text.get("1.0", "end-1c") == "第一段便签\n\n第二段便签"

    linked_window = capture_manager.add_window(initial_position=(100, 100))
    assert linked_window.task_id == linked_window.instance_number
    assert linked_window.task is not todo_window.task
    linked_window.append_note_text("原来的独立内容")
    summary_by_id = {
        task.id: _task_content_summary(task)
        for task in capture_manager._task_summaries()
    }
    assert summary_by_id[todo_window.task_id].startswith("待办 2 项")
    assert "任务胶囊：快速收集的待办（已暂停）" in summary_by_id[todo_window.task_id]
    assert summary_by_id[note_window.task_id] == "便签 10 字"
    assert summary_by_id[linked_window.task_id] == "便签 7 字"
    assert _task_content_summary(TaskState(99)) == ""
    original_prompt = globals()["_prompt_task_binding"]
    prompt_calls: list[tuple[int, list[int]]] = []
    linked_task_id = linked_window.task_id

    def fake_prompt(_parent, current_task_id, tasks):
        prompt_calls.append((current_task_id, [task.id for task in tasks]))
        return todo_window.task_id

    globals()["_prompt_task_binding"] = fake_prompt
    try:
        linked_window.mode_menu.invoke(len(WINDOW_MODES) + 1)
        capture_manager.root.update()
    finally:
        globals()["_prompt_task_binding"] = original_prompt
    assert prompt_calls == [
        (linked_task_id, sorted(capture_manager._tasks))
    ]
    assert linked_window.task is todo_window.task is focus_window.task
    assert linked_window.instance_number != linked_window.task_id
    assert linked_window.note_text.get("1.0", "end-1c") == ""
    linked_window.append_note_text("共享便签")
    assert todo_window.note_text.get("1.0", "end-1c") == "共享便签"
    assert focus_window.note_text.get("1.0", "end-1c") == "共享便签"
    linked_window.note_text.insert("end", "！")
    capture_manager.root.update()
    assert todo_window.note_text.get("1.0", "end-1c") == "共享便签！"
    linked_window.add_todo_text("跨窗口同步事项")
    assert todo_faces(todo_window.todo_items)[-1] == ("跨窗口同步事项", False)
    assert todo_window.todo_list.get("end") == "☐  跨窗口同步事项"
    capture_manager.bind_window_to_task(linked_window, linked_window.instance_number)
    assert linked_window.note_text.get("1.0", "end-1c") == "原来的独立内容"
    assert not linked_window.todo_items
    capture_manager.bind_window_to_task(linked_window, todo_window.task_id)
    linked_window.set_mode("倒计时")
    linked_window.timer_minutes.set(4)
    assert todo_window.timer_minutes.get() == 4
    assert focus_window.timer_minutes.get() == 4
    linked_window._toggle_timer()
    assert todo_window.timer_start_button.cget("text") == "暂停"
    linked_window._toggle_timer()
    assert todo_window.timer_start_button.cget("text") == "继续"
    focus_window._toggle_focus()
    assert focus_window._focus_status == "running"
    notifications: list[tuple[str, str]] = []
    original_notify = capture_manager.tray.notify
    capture_manager.tray.notify = lambda title, message: notifications.append(
        (title, message)
    )
    try:
        overdue = focus_window.todo_items[0]
        focus_window.todo_items[0] = (
            overdue[0], overdue[1], time.time() - 5, overdue[3]
        )
        capture_manager._notified_todo_dues.clear()
        focus_window._apply_todo_styles(notify=True)
        assert any(title == "待办已到期" for title, _message in notifications)
        assert len(capture_manager._notified_todo_dues) == 1
        focus_window._apply_todo_styles(notify=True)
        assert len(capture_manager._notified_todo_dues) == 1, "同一条待办重复提醒"
        assert len(
            [title for title, _message in notifications if title == "待办已到期"]
        ) == 1
        linked_window.timer_minutes.set(4)
        linked_window._toggle_timer()
        linked_window._timer_deadline = time.monotonic() - 1
        timer_deadline = time.monotonic() + 1
        while (
            linked_window.task.timer_status != "finished"
            and time.monotonic() < timer_deadline
        ):
            capture_manager.root.update()
            time.sleep(0.01)
        assert linked_window.task.timer_status == "finished"
        assert any(title == "倒计时结束" for title, _message in notifications)
    finally:
        capture_manager.tray.notify = original_notify
    capture_manager._save_window_states_now()
    capture_manager.exit_app()
    capture_reopened = DesktopManager(
        tray_enabled=False,
        visible=True,
        settings_path=capture_settings_path,
        auto_start_store=MemoryAutoStartStore(),
        update_client=current_client,
    )
    assert len(capture_reopened.windows) == 3
    restored_focus = next(
        window for window in capture_reopened.windows
        if window.mode == "任务胶囊"
    )
    assert restored_focus._focus_status == "paused"
    assert 0 < restored_focus._focus_remaining_seconds <= 180
    assert restored_focus.focus_time_label.cget("text").startswith(("02:", "03:"))
    assert todo_faces(restored_focus.todo_items) == [
        ("快速收集的待办", False),
        ("第二项待办", False),
        ("跨窗口同步事项", False),
    ]
    restored_overdue = restored_focus.todo_items[0]
    assert restored_overdue[2] is not None
    assert (
        restored_focus.task_id, restored_overdue[3], restored_overdue[2]
    ) in capture_reopened._notified_todo_dues
    restored_linked = next(
        window for window in capture_reopened.windows
        if window.mode == "倒计时"
    )
    assert restored_linked.task is restored_focus.task
    assert restored_linked.task_id != restored_linked.instance_number
    assert restored_linked.note_text.get("1.0", "end-1c") == "共享便签！"
    assert restored_linked.timer_minutes.get() == 4
    saved_capture = json.loads(
        capture_settings_path.with_name("windows.json").read_text(encoding="utf-8")
    )
    assert any(
        task["id"] == restored_linked.instance_number
        and task["note"] == "原来的独立内容"
        for task in saved_capture["tasks"]
    )
    restored_focus._complete_focus()
    assert todo_faces(restored_focus.todo_items)[0] == ("快速收集的待办", True)
    restored_linked._toggle_focus()
    assert restored_focus._focus_status == "running"
    restored_focus.close()
    assert restored_linked._focus_status == "running"
    restored_linked.close()
    assert restored_linked.task.focus_status == "paused"
    assert next(
        window for window in capture_reopened.windows
        if window.mode == "便签"
    ).note_text.get("1.0", "end-1c") == "第一段便签\n\n第二段便签"
    capture_reopened.exit_app()

    hide_settings_path = (
        Path(temporary_settings_directory.name) / "Hide" / "settings.json"
    )
    hide_manager = DesktopManager(
        tray_enabled=False,
        visible=True,
        create_initial_window=False,
        settings_path=hide_settings_path,
        auto_start_store=MemoryAutoStartStore(),
        update_client=current_client,
    )
    normal_window = hide_manager.add_window()
    locked_window = hide_manager.add_window()
    locked_window.set_locked(True)
    ball_window = hide_manager.add_window()
    ball_window.set_mode("快捷按键")
    _, hide_work_area = _monitor_areas_at(
        ball_window.root.winfo_x(), ball_window.root.winfo_y()
    )
    hide_ball_target, hide_ball_edge = ball_window._ball_target_at_edge(
        hide_work_area[2] - 1, hide_work_area[1] + 130
    )
    ball_window._collapse_to_ball(hide_ball_target, hide_ball_edge)
    deadline = time.monotonic() + 2
    while ball_window.animating and time.monotonic() < deadline:
        hide_manager.root.update()
        time.sleep(0.01)
    assert ball_window.collapsed
    hide_manager.open_settings()
    hide_manager.open_quick_capture(prefill_clipboard=False)
    hide_manager.root.update()
    assert normal_window.root.state() == "normal"
    assert locked_window.lock_window.state() == "normal"
    assert ball_window.ball_window.state() == "normal"
    assert ball_window.shortcut_window.state() == "normal"
    states_before_hide = {
        overlay.instance_number: overlay.state_snapshot()
        for overlay in (normal_window, locked_window, ball_window)
    }
    hide_manager.toggle_overlays_hidden()
    hide_manager.root.update()
    assert hide_manager.overlays_hidden
    for overlay in (normal_window, locked_window, ball_window):
        assert not overlay.visible
        for surface in (
            overlay.root, overlay.ball_window, overlay.lock_window,
            overlay.shortcut_window,
        ):
            assert surface.state() == "withdrawn"
    assert hide_manager.settings_window.state() == "withdrawn"
    assert hide_manager.quick_capture_window.state() == "withdrawn"
    assert locked_window.locked and ball_window.collapsed
    # Simulate WM_HOTKEY through the same tray message route as a real keypress.
    hide_manager.tray._hide_hotkey_id = HIDE_HOTKEY_IDS[0]
    hide_manager.tray._window_proc(
        hide_manager.tray.hwnd, WM_HOTKEY, HIDE_HOTKEY_IDS[0], 0
    )
    hide_manager.tray._hide_hotkey_id = None
    deadline = time.monotonic() + 1
    while hide_manager.overlays_hidden and time.monotonic() < deadline:
        hide_manager.root.update()
        time.sleep(0.01)
    assert not hide_manager.overlays_hidden
    assert normal_window.root.state() == "normal"
    assert locked_window.root.state() == "normal"
    assert locked_window.lock_window.state() == "normal"
    assert locked_window.locked and locked_window.click_through_style_is_set()
    assert ball_window.ball_window.state() == "normal"
    assert ball_window.shortcut_window.state() == "normal"
    assert ball_window.collapsed
    assert {
        overlay.instance_number: overlay.state_snapshot()
        for overlay in (normal_window, locked_window, ball_window)
    } == states_before_hide
    assert hide_manager.settings_window.state() == "normal"
    assert hide_manager.quick_capture_window.state() == "normal"
    hide_manager.toggle_overlays_hidden()
    hide_manager.tray._window_proc(
        hide_manager.tray.hwnd,
        hide_manager.tray._second_instance_message,
        0,
        0,
    )
    deadline = time.monotonic() + 1
    while hide_manager.overlays_hidden and time.monotonic() < deadline:
        hide_manager.root.update()
        time.sleep(0.01)
    assert not hide_manager.overlays_hidden, "second launch did not restore hidden windows"
    assert len(hide_manager.windows) == 3, "second launch duplicated windows"
    assert hide_manager.hide_hotkey == "Ctrl+K"
    hide_manager.hide_hotkey_input.set("shift + ctrl + f12")
    assert hide_manager.apply_hide_hotkey()
    assert hide_manager.hide_hotkey == "Ctrl+Shift+F12"
    assert not hide_manager.apply_hide_hotkey("Ctrl+Alt+D")
    assert hide_manager.hide_hotkey == "Ctrl+Shift+F12"
    hide_manager._save_settings_now()
    assert json.loads(hide_settings_path.read_text(encoding="utf-8"))[
        "hide_hotkey"
    ] == "Ctrl+Shift+F12"
    hide_manager.tray.dispatch_command_for_test(TRAY_COMMAND_VISIBILITY)
    deadline = time.monotonic() + 1
    while not hide_manager.overlays_hidden and time.monotonic() < deadline:
        hide_manager.root.update()
        time.sleep(0.01)
    assert hide_manager.overlays_hidden
    hidden_new_window = hide_manager.add_window()
    assert hidden_new_window.root.state() == "withdrawn"
    hidden_new_window.close()
    hide_manager.tray.dispatch_command_for_test(TRAY_COMMAND_VISIBILITY)
    deadline = time.monotonic() + 1
    while hide_manager.overlays_hidden and time.monotonic() < deadline:
        hide_manager.root.update()
        time.sleep(0.01)
    assert not hide_manager.overlays_hidden
    assert hidden_new_window not in hide_manager.windows
    hide_manager.exit_app()
    reloaded_hide_manager = DesktopManager(
        tray_enabled=False,
        visible=False,
        create_initial_window=False,
        settings_path=hide_settings_path,
        auto_start_store=MemoryAutoStartStore(),
        update_client=current_client,
    )
    assert reloaded_hide_manager.hide_hotkey == "Ctrl+Shift+F12"
    reloaded_hide_manager.exit_app()
    temporary_settings_directory.cleanup()
    print(
        "Self-test passed: tray manager and icons, persistent settings and windows, "
        "per-user auto-start option, "
        "verified GitHub update index and persistent auto-update option, "
        "independent window/task ids, shared task views and legacy migration, "
        "seven window modes including a per-window browser, persistent task focus and a cycling window switcher, "
        "editable and removable todos, per-todo deadlines with one-off reminders, "
        "timer completion notices, "
        "quick capture to existing or new windows, "
        "empty-note placeholder, "
        "no-background mode, persistent content-visible click-through lock, "
        "background lifetime and single-instance activation, "
        "global hide hotkey restores normal, locked and collapsed windows, "
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
        instance_guard = SingleInstanceGuard()
        if not instance_guard.acquire():
            _signal_existing_instance()
            sys.exit(0)
        try:
            DesktopManager(
                initial_position=_position_from_arguments(sys.argv[1:])
            ).run()
        finally:
            instance_guard.close()
