from __future__ import annotations

import ctypes
import sys
import time
import tkinter as tk
from collections import deque
from collections.abc import Callable
from ctypes import wintypes


APP_TITLE = "DesktopTools 自由窗口"

WINDOW_WIDTH = 560
WINDOW_HEIGHT = 320
MIN_WIDTH = 380
MIN_HEIGHT = 220
TITLE_HEIGHT = 48
LOCK_WIDTH = 68
LOCK_HEIGHT = 32
CLOSE_AREA_WIDTH = 48
BALL_SIZE = 58
BALL_MARGIN = 6
RESTORE_MARGIN = 10
EDGE_TRIGGER_DISTANCE = 28
ANIMATION_STEPS = 10
ANIMATION_DELAY_MS = 14

BG_OUTER = "#11141A"
BG_TITLE = "#20242D"
BG_BODY = "#292E39"
BG_PANEL = "#222730"
BORDER = "#4B5262"
TEXT = "#F5F7FA"
TEXT_MUTED = "#AAB2C0"
ACCENT = "#66D9A6"
ACCENT_HOVER = "#80E5B7"
LOCKED_ACCENT = "#F5B85C"
LOCKED_HOVER = "#FFC873"
CLOSE_HOVER = "#E05260"
TRANSPARENT_KEY = "#010203"

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
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

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
shell32.Shell_NotifyIconW.argtypes = [
    wintypes.DWORD,
    ctypes.POINTER(NotifyIconData),
]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL

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
        instance_number: int = 1,
    ) -> None:
        self.visible = visible
        self.on_close = on_close
        self.instance_number = instance_number
        self._closed = False
        self.locked = False
        self.collapsed = False
        self.animating = False
        self._drag_origin: tuple[int, int] | None = None
        self._resize_origin: tuple[int, int, int, int] | None = None
        self._restore_geometry: tuple[int, int, int, int] | None = None
        self._ball_geometry: tuple[int, int, int, int] | None = None
        self._dock_edge: str | None = None
        self._sync_scheduled = False
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
        panel.pack(fill="both", expand=True, padx=24, pady=24)

        self.status_label = tk.Label(
            panel,
            text="●  可操作",
            bg=BG_PANEL,
            fg=ACCENT,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self.status_label.pack(pady=(34, 12))

        self.message_label = tk.Label(
            panel,
            text="拖动顶部栏移动，拖到屏幕边缘可收起\n点击“锁定”后，鼠标操作会穿透到窗口后方",
            bg=BG_PANEL,
            fg=TEXT,
            justify="center",
            font=("Microsoft YaHei UI", 11),
            padx=24,
        )
        self.message_label.pack()

        hint = tk.Label(
            panel,
            text="窗口将始终保持在最前方",
            bg=BG_PANEL,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 9),
        )
        hint.pack(pady=(14, 0))

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

    def _build_lock_window(self) -> None:
        self.lock_window = tk.Toplevel(self.root)
        if not self.visible:
            self.lock_window.withdraw()

        self.lock_window.overrideredirect(True)
        self.lock_window.configure(bg=BG_TITLE)
        self.lock_window.attributes("-topmost", True)
        try:
            self.lock_window.attributes("-toolwindow", True)
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
            or self.root.state() != "normal"
        ):
            self.lock_window.withdraw()
            return

        x = (
            self.root.winfo_x()
            + self.root.winfo_width()
            - CLOSE_AREA_WIDTH
            - LOCK_WIDTH
            - 10
        )
        y = self.root.winfo_y() + (TITLE_HEIGHT - LOCK_HEIGHT) // 2 + 1
        _set_absolute_geometry(
            self.lock_window,
            width=LOCK_WIDTH,
            height=LOCK_HEIGHT,
            x=x,
            y=y,
        )
        self.lock_window.deiconify()
        self.lock_window.attributes("-topmost", True)
        self.lock_window.lift()
        _set_native_topmost(self.lock_window)

    def toggle_lock(self) -> None:
        self.set_locked(not self.locked)

    def set_locked(self, locked: bool) -> None:
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

        if locked:
            self.lock_button.configure(
                text="解锁",
                bg=LOCKED_ACCENT,
                activebackground=LOCKED_HOVER,
                fg="#30200A",
                activeforeground="#30200A",
            )
            self.status_label.configure(text="●  已锁定 · 鼠标穿透", fg=LOCKED_ACCENT)
            self.message_label.configure(
                text="现在可以直接点击窗口后方的内容\n点击右上角“解锁”恢复窗口操作"
            )
            self.close_button.configure(state="disabled", cursor="arrow")
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
            self.status_label.configure(text="●  可操作", fg=ACCENT)
            self.message_label.configure(
                text="拖动顶部栏移动，拖到屏幕边缘可收起\n点击“锁定”后，鼠标操作会穿透到窗口后方"
            )
            self.close_button.configure(state="normal", cursor="hand2")
            self.resize_grip.configure(cursor="size_nw_se")
            self.title_bar.configure(cursor="fleur")
            self.title_label.configure(cursor="fleur")
            if self.visible:
                self.root.attributes("-topmost", True)
                self.root.lift()
                self.root.focus_force()

        self._sync_lock_window()

    def click_through_style_is_set(self) -> bool:
        hwnd = _top_level_handle(self.root)
        style = int(_get_window_long(wintypes.HWND(hwnd), GWL_EXSTYLE))
        return bool(style & WS_EX_TRANSPARENT and style & WS_EX_NOACTIVATE)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
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
        self.root.attributes("-alpha", self.opacity_percent.get() / 100)

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
    ) -> None:
        self.visible = visible
        self._exiting = False
        self._next_instance_number = 1
        self.windows: list[OverlayApp] = []
        self.settings_window: tk.Toplevel | None = None

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_TITLE)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        self.opacity_percent = tk.IntVar(master=self.root, value=86)
        self.edge_collapse_enabled = tk.BooleanVar(master=self.root, value=True)
        self.restore_margin = tk.IntVar(master=self.root, value=RESTORE_MARGIN)

        self.tray = SystemTrayIcon(
            self.root,
            on_add=self.add_window,
            on_settings=self.open_settings,
            on_exit=self.exit_app,
            show_icon=tray_enabled,
        )

        if create_initial_window:
            self.add_window(initial_position=initial_position)

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

        tk.Label(
            window,
            text="设置在后台进程退出前有效，并立即应用到全部实例。",
            bg=BG_BODY,
            fg=TEXT_MUTED,
            font=("Microsoft YaHei UI", 8),
            anchor="w",
        ).pack(fill="x", padx=22, pady=(16, 12))

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
        settings_height = 330
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

    def reset_settings(self) -> None:
        self.opacity_percent.set(86)
        self.edge_collapse_enabled.set(True)
        self.restore_margin.set(RESTORE_MARGIN)
        self._on_opacity_changed("86")

    def close_settings(self) -> None:
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
    app.set_locked(False)
    app.root.update()
    assert not app.click_through_style_is_set(), "click-through style was not disabled"

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

    manager = DesktopManager(
        tray_enabled=True,
        visible=False,
        create_initial_window=False,
    )
    assert manager.tray.hwnd, "tray message window was not created"
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
    manager.close_settings()
    first_window.close()
    assert len(manager.windows) == 1, "closing one instance stopped the manager"
    second_window.close()
    assert len(manager.windows) == 0, "closed instance remained registered"
    assert manager.root.winfo_exists(), "manager stopped with the last instance"
    manager.open_settings()
    assert manager.settings_window is not None
    manager.exit_app()
    print(
        "Self-test passed: tray manager, background lifetime, settings, "
        "lock styles, and ball collapse/restore work correctly."
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
