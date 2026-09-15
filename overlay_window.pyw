from __future__ import annotations

import ctypes
import sys
import tkinter as tk
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

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020


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


class OverlayApp:
    def __init__(self, *, visible: bool = True) -> None:
        self.visible = visible
        self.locked = False
        self._drag_origin: tuple[int, int] | None = None
        self._resize_origin: tuple[int, int, int, int] | None = None
        self._sync_scheduled = False

        self.root = tk.Tk()
        if not visible:
            self.root.withdraw()

        self.root.title(APP_TITLE)
        self.root.overrideredirect(True)
        self.root.configure(bg=BG_OUTER)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.86)
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self._build_main_window()
        self._center_window()
        self.root.update_idletasks()
        self._build_lock_window()

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
            text="自由窗口",
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
            text="拖动顶部栏移动窗口\n点击“锁定”后，鼠标操作会穿透到窗口后方",
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

    def _center_window(self) -> None:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, (screen_width - WINDOW_WIDTH) // 2)
        y = max(0, (screen_height - WINDOW_HEIGHT) // 2)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

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
        self.root.geometry(f"+{x}+{y}")

    def _end_drag(self, _event: tk.Event) -> None:
        self._drag_origin = None

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
        self.root.geometry(f"{width}x{height}")

    def _end_resize(self, _event: tk.Event) -> None:
        self._resize_origin = None

    def _on_main_configure(self, event: tk.Event) -> None:
        if event.widget is not self.root or self._sync_scheduled:
            return
        self._sync_scheduled = True
        self.root.after_idle(self._sync_lock_window)

    def _sync_lock_window(self) -> None:
        self._sync_scheduled = False
        if not self.lock_window.winfo_exists():
            return

        if not self.visible or self.root.state() != "normal":
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
        self.lock_window.geometry(f"{LOCK_WIDTH}x{LOCK_HEIGHT}+{x}+{y}")
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
                text="拖动顶部栏移动窗口\n点击“锁定”后，鼠标操作会穿透到窗口后方"
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
        try:
            if self.lock_window.winfo_exists():
                self.lock_window.destroy()
        except (AttributeError, tk.TclError):
            pass
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def _self_test() -> None:
    app = OverlayApp(visible=False)
    app.root.update()
    app.set_locked(True)
    app.root.update()
    assert app.click_through_style_is_set(), "click-through style was not enabled"
    app.set_locked(False)
    app.root.update()
    assert not app.click_through_style_is_set(), "click-through style was not disabled"
    app.close()
    print("Self-test passed: lock/unlock native styles toggle correctly.")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test()
    else:
        OverlayApp().run()
