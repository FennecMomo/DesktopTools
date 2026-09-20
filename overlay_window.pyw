from __future__ import annotations

import ctypes
import json
import math
import os
import sys
import tempfile
import time
import tkinter as tk
from collections import deque
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path


APP_TITLE = "DesktopTools 自由窗口"

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
NO_BACKGROUND_TEXT = "#17212D"
NO_BACKGROUND_MUTED = "#344455"
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

        return {
            "opacity_percent": _clamp(round(opacity), 55, 100),
            "edge_collapse_enabled": edge_collapse,
            "restore_margin": _clamp(round(restore_margin), 0, 80),
            "no_background": no_background,
        }

    def save(self, settings: dict[str, int | bool]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "opacity_percent": _clamp(int(settings["opacity_percent"]), 55, 100),
            "edge_collapse_enabled": bool(settings["edge_collapse_enabled"]),
            "restore_margin": _clamp(int(settings["restore_margin"]), 0, 80),
            "no_background": bool(settings["no_background"]),
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
        on_exit: Callable[[], None],
        show_icon: bool = True,
    ) -> None:
        self.root = root
        self.on_add = on_add
        self.on_settings = on_settings
        self.on_exit = on_exit
        self.show_icon = show_icon
        self._cleaned = False
        self._icon_added = False
        self._menu_bitmaps: dict[int, int] = {}
        self._pending_actions: deque[Callable[[], None]] = deque()
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
        self.root.after(40, self._drain_actions)

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
                self.root.after(40, self._drain_actions)
            except tk.TclError:
                pass

    def dispatch_command_for_test(self, command: int) -> None:
        actions = {
            TRAY_COMMAND_ADD: self.on_add,
            TRAY_COMMAND_SETTINGS: self.on_settings,
            TRAY_COMMAND_EXIT: self.on_exit,
        }
        action = actions.get(command)
        if action is not None:
            self._schedule(action)

    def cleanup(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
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
    ) -> None:
        self.visible = visible
        self.on_close = on_close
        self.instance_number = instance_number
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
        self._timer_remaining_seconds = 25 * 60
        self._timer_deadline: float | None = None
        self._tick_after_id: str | None = None
        self.root = tk.Tk() if master is None else tk.Toplevel(master)
        if not visible:
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
        self._place_initial_window(initial_position)
        self.root.update_idletasks()
        self._build_lock_window()
        self._build_ball_window()

        self.root.bind("<Configure>", self._on_main_configure, add="+")
        self.root.bind("<Escape>", lambda _event: self.close())
        self.root.after_idle(self._sync_lock_window)
        self._tick_modes()

        cursor = Point()
        user32.GetCursorPos(ctypes.byref(cursor))
        self.update_background_for_hover(cursor.x, cursor.y)

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
        self.empty_note_label = tk.Label(
            note_view,
            text="空便签",
            bg=BG_PANEL,
            fg=NO_BACKGROUND_MUTED,
            font=("Microsoft YaHei UI", 12, "bold"),
        )
        self._register_mode_style(self.empty_note_label, bg=BG_PANEL)
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
        self._refresh_empty_note_label()

    def _on_note_modified(self, _event: tk.Event) -> None:
        if not self.note_text.edit_modified():
            return
        self.note_text.edit_modified(False)
        self._refresh_empty_note_label()

    def _refresh_empty_note_label(self) -> None:
        show_placeholder = (
            self._background_hidden
            and not self.locked
            and self.mode == "便签"
            and not self.note_text.get("1.0", "end-1c").strip()
        )
        if show_placeholder:
            self.empty_note_label.place(relx=0.5, rely=0.5, anchor="center")
            self.empty_note_label.lift()
        else:
            self.empty_note_label.place_forget()

    def _add_todo(self, _event: tk.Event | None = None) -> None:
        title = self.todo_input.get().strip()
        if not title:
            return
        self.todo_items.append((title, False))
        self.todo_input.delete(0, "end")
        self._render_todos()

    def _selected_todo_index(self) -> int | None:
        selection = self.todo_list.curselection()
        return int(selection[0]) if selection else None

    def _render_todos(self, selected: int | None = None) -> None:
        self.todo_list.delete(0, "end")
        for title, done in self.todo_items:
            self.todo_list.insert("end", f"{'☑' if done else '☐'}  {title}")
        if selected is not None and selected < len(self.todo_items):
            self.todo_list.selection_set(selected)

    def _toggle_todo(self, _event: tk.Event | None = None) -> None:
        selected = self._selected_todo_index()
        if selected is None:
            return
        title, done = self.todo_items[selected]
        self.todo_items[selected] = (title, not done)
        self._render_todos(selected)

    def _delete_todo(self) -> None:
        selected = self._selected_todo_index()
        if selected is None:
            return
        del self.todo_items[selected]
        self._render_todos(min(selected, len(self.todo_items) - 1))

    def _timer_minutes_value(self) -> int:
        try:
            return _clamp(int(self.timer_minutes.get()), 1, 180)
        except (tk.TclError, ValueError):
            return 25

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
            fg=(
                CLOSE_HOVER
                if remaining == 0
                else NO_BACKGROUND_TEXT if self._background_hidden else TEXT
            ),
        )

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
        if self.visible:
            self.root.focus_force()
        self._sync_lock_window()

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
        if event.widget is not self.root or self._sync_scheduled:
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
            or (self.root.state() != "normal" and not self.locked)
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
                before=self.todo_list,
            )
            self.todo_actions.pack(fill="x", pady=(4, 0))
            self.timer_actions.pack(pady=(0, 4))
            self._apply_control_colors()
        self._apply_content_colors()
        self.empty_note_label.configure(
            fg=NO_BACKGROUND_MUTED if self._background_hidden else TEXT_MUTED
        )
        self._refresh_empty_note_label()

    def _apply_content_colors(self) -> None:
        text_color = NO_BACKGROUND_TEXT if self._background_hidden else TEXT
        muted_color = NO_BACKGROUND_MUTED if self._background_hidden else TEXT_MUTED
        self.note_text.configure(fg=text_color)
        self.todo_list.configure(fg=text_color, selectforeground=text_color)
        self.clock_time_label.configure(fg=text_color)
        self.clock_date_label.configure(fg=muted_color)
        self._update_timer_display()

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
            self._refresh_empty_note_label()
            if self.visible:
                # Click-through alone still covers the target visually.
                # Withdraw the main HWND and leave only the unlock control.
                self.root.withdraw()
        else:
            self.unlock_canvas.pack_forget()
            self.lock_button.pack(fill="both", expand=True)
            self.lock_window.configure(bg=BG_TITLE)
            if self.visible:
                self.root.deiconify()
                self.root.attributes("-topmost", True)
                self.root.lift()
                self.root.focus_force()
            cursor = Point()
            if user32.GetCursorPos(ctypes.byref(cursor)):
                self.update_background_for_hover(cursor.x, cursor.y)
            if self._background_hidden:
                self._apply_background_state()

        self._sync_lock_window()

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
    ) -> None:
        self.visible = visible
        self._exiting = False
        self._next_instance_number = 1
        self._settings_save_after_id: str | None = None
        self._settings_dirty = False
        self.windows: list[OverlayApp] = []
        self.settings_window: tk.Toplevel | None = None

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_TITLE)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        self.settings_store = SettingsStore(settings_path)
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
        for setting_variable in (
            self.opacity_percent,
            self.edge_collapse_enabled,
            self.restore_margin,
            self.no_background,
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
            on_exit=self.exit_app,
            show_icon=tray_enabled,
        )

        if create_initial_window:
            self.add_window(initial_position=initial_position)
        self.root.after(HOVER_POLL_MS, self._poll_hover)

    def add_window(
        self,
        initial_position: tuple[int, int] | None = None,
    ) -> OverlayApp:
        if initial_position is None and self.windows:
            previous = self.windows[-1]
            if previous.collapsed and previous._ball_geometry is not None:
                previous_x = previous._ball_geometry[2]
                previous_y = previous._ball_geometry[3]
            else:
                previous_x = previous.root.winfo_x()
                previous_y = previous.root.winfo_y()
            initial_position = previous_x + 36, previous_y + 36

        window = OverlayApp(
            visible=self.visible,
            initial_position=initial_position,
            master=self.root,
            on_close=self._on_window_closed,
            opacity_percent=self.opacity_percent,
            edge_collapse_enabled=self.edge_collapse_enabled,
            restore_margin=self.restore_margin,
            no_background=self.no_background,
            instance_number=self._next_instance_number,
        )
        self._next_instance_number += 1
        self.windows.append(window)
        self._update_instance_count()
        return window

    def _on_window_closed(self, window: OverlayApp) -> None:
        if window in self.windows:
            self.windows.remove(window)
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
        if self._exiting:
            return
        self._refresh_backgrounds()
        self.root.after(HOVER_POLL_MS, self._poll_hover)

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
            text="设置会自动保存到本机，并立即应用到全部实例。",
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 8),
            anchor="w",
        )
        self.settings_note_label.pack(fill="x", padx=22, pady=(16, 12))

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

        settings_width = 400
        settings_height = 366
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
        return {
            "opacity_percent": _clamp(opacity, 55, 100),
            "edge_collapse_enabled": edge_collapse,
            "restore_margin": _clamp(restore_margin, 0, 80),
            "no_background": no_background,
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
            if hasattr(self, "settings_note_label"):
                try:
                    self.settings_note_label.configure(
                        text="设置暂时无法写入磁盘；退出前会再次尝试。",
                        fg=CLOSE_HOVER,
                    )
                except tk.TclError:
                    pass
            return
        self._settings_dirty = False
        if hasattr(self, "settings_note_label"):
            try:
                self.settings_note_label.configure(
                    text="设置会自动保存到本机，并立即应用到全部实例。",
                    fg=TEXT_MUTED,
                )
            except tk.TclError:
                pass

    def reset_settings(self) -> None:
        self.opacity_percent.set(86)
        self.edge_collapse_enabled.set(True)
        self.restore_margin.set(RESTORE_MARGIN)
        self.no_background.set(False)
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
        self._exiting = True
        self.close_settings()
        for window in tuple(self.windows):
            window.on_close = None
            window.close()
        self.windows.clear()
        self.tray.cleanup()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self) -> None:
        self.root.mainloop()


def _self_test() -> None:
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
    assert app.note_text.cget("fg") == NO_BACKGROUND_TEXT
    assert app.note_text.get("1.0", "end-1c") == "临时想法"
    app.note_text.delete("1.0", "end")
    app.root.update()
    assert app.empty_note_label.winfo_manager() == "place"
    assert app.empty_note_label.cget("text") == "空便签"
    app.note_text.insert("1.0", "再次写入")
    app.root.update()
    assert app.empty_note_label.winfo_manager() == ""
    app.set_mode("待办")
    assert app.todo_entry_row.winfo_manager() == ""
    assert app.todo_actions.winfo_manager() == ""
    assert app.todo_list.cget("fg") == NO_BACKGROUND_TEXT
    app.set_mode("倒计时")
    assert app.timer_actions.winfo_manager() == ""
    assert app.timer_label.cget("fg") == NO_BACKGROUND_TEXT
    app.set_mode("时钟")
    assert app.clock_time_label.cget("bg") == TRANSPARENT_KEY
    assert app.clock_time_label.cget("fg") == NO_BACKGROUND_TEXT
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
    visible_lock_app.root.update()
    original_position = (
        visible_lock_app.root.winfo_x(),
        visible_lock_app.root.winfo_y(),
    )
    visible_lock_app.set_locked(True)
    visible_lock_app.root.update()
    assert visible_lock_app.root.state() == "withdrawn"
    assert visible_lock_app.lock_window.state() == "normal"
    assert visible_lock_app.unlock_canvas.winfo_manager() == "pack"
    assert visible_lock_app.lock_button.winfo_manager() == ""
    assert visible_lock_app.lock_window.winfo_width() == UNLOCK_ICON_SIZE
    assert visible_lock_app.lock_window.winfo_height() == UNLOCK_ICON_SIZE
    visible_lock_app.update_background_for_hover(*original_position)
    visible_lock_app.root.update()
    assert visible_lock_app.root.state() == "withdrawn", (
        "hover unexpectedly revealed a locked window"
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
    visible_lock_app.close()

    temporary_settings_directory = tempfile.TemporaryDirectory()
    test_settings_path = (
        Path(temporary_settings_directory.name) / "DesktopTools" / "settings.json"
    )
    manager = DesktopManager(
        tray_enabled=True,
        visible=False,
        create_initial_window=False,
        settings_path=test_settings_path,
    )
    assert manager.tray.hwnd, "tray message window was not created"
    assert all(manager.tray._menu_bitmaps.values()), "tray menu icons were not created"
    test_menu = user32.CreatePopupMenu()
    assert test_menu, "test popup menu was not created"
    try:
        user32.AppendMenuW(test_menu, MF_STRING, TRAY_COMMAND_ADD, "添加自由窗口")
        user32.AppendMenuW(test_menu, MF_STRING, TRAY_COMMAND_SETTINGS, "设置")
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
    first_window.set_mode("待办")
    first_window.todo_input.insert(0, "只属于第一个窗口")
    first_window._add_todo()
    assert second_window.mode == "便签"
    assert not second_window.todo_items
    manager.tray.dispatch_command_for_test(TRAY_COMMAND_SETTINGS)
    deadline = time.monotonic() + 1
    while manager.settings_window is None and time.monotonic() < deadline:
        manager.root.update()
        time.sleep(0.01)
    assert manager.settings_window is not None
    manager._on_opacity_changed("73")
    assert abs(float(first_window.root.attributes("-alpha")) - 0.73) < 0.01
    assert abs(float(second_window.root.attributes("-alpha")) - 0.73) < 0.01
    manager.reset_settings()
    assert manager.opacity_percent.get() == 86
    assert manager.no_background.get() is False
    manager.opacity_percent.set(77)
    manager.edge_collapse_enabled.set(False)
    manager.restore_margin.set(17)
    manager.no_background.set(True)
    assert first_window._background_hidden, "no-background state was not shared"
    manager._save_settings_now()
    saved_settings = json.loads(test_settings_path.read_text(encoding="utf-8"))
    assert saved_settings["opacity_percent"] == 77
    assert saved_settings["edge_collapse_enabled"] is False
    assert saved_settings["restore_margin"] == 17
    assert saved_settings["no_background"] is True
    manager.close_settings()
    first_window.close()
    assert len(manager.windows) == 1, "closing one instance stopped the manager"
    second_window.close()
    assert len(manager.windows) == 0, "closed instance remained registered"
    assert manager.root.winfo_exists(), "manager stopped with the last instance"
    manager.open_settings()
    assert manager.settings_window is not None
    manager.exit_app()

    reloaded_manager = DesktopManager(
        tray_enabled=False,
        visible=False,
        create_initial_window=False,
        settings_path=test_settings_path,
    )
    assert reloaded_manager.opacity_percent.get() == 77
    assert reloaded_manager.edge_collapse_enabled.get() is False
    assert reloaded_manager.restore_margin.get() == 17
    assert reloaded_manager.no_background.get() is True
    reloaded_manager.exit_app()
    temporary_settings_directory.cleanup()
    print(
        "Self-test passed: tray manager and icons, persistent settings, "
        "four independent window modes, empty-note placeholder, "
        "no-background mode, icon-only lock, background lifetime, "
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
    if "--self-test" in sys.argv:
        _self_test()
    else:
        DesktopManager(
            initial_position=_position_from_arguments(sys.argv[1:])
        ).run()
