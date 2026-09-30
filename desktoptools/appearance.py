"""Shared visual tokens and lightweight Tk controls."""
from pathlib import Path
import tkinter as tk

BG_OUTER = "#0C141D"
BG_TITLE = "#111D29"
BG_BODY = "#152330"
BG_PANEL = "#1C2D3C"
BORDER = "#354A5B"
TEXT = "#ECF3F5"
TEXT_MUTED = "#A1B5C4"
ACCENT = "#6DE7C1"
ACCENT_HOVER = "#92F1D3"
HOVER = "#2B4355"
FONT = "Microsoft YaHei UI"
ASSETS = Path(__file__).resolve().parent.parent / "assets"
ICON_PATH = ASSETS / "DesktopTools.ico"


def set_window_icon(window):
    window.iconbitmap(str(ICON_PATH))


def brand_image(master, size=24):
    return tk.PhotoImage(master=master, file=str(ASSETS / f"app-{size}.png"))


def button(parent, text, command, *, primary=False):
    base = ACCENT if primary else BG_PANEL
    hover = ACCENT_HOVER if primary else HOVER
    widget = tk.Button(
        parent, text=text, command=command, bg=base,
        fg="#123D32" if primary else TEXT,
        activebackground=hover, activeforeground="#123D32" if primary else TEXT,
        font=(FONT, 9, "bold" if primary else "normal"),
        relief="flat", bd=0, highlightthickness=0, padx=14, pady=7, cursor="hand2",
    )
    widget.bind("<Enter>", lambda event: widget.configure(bg=hover))
    widget.bind("<Leave>", lambda event: widget.configure(bg=base))
    return widget


class ScrollableFrame(tk.Frame):
    """A vertically scrolling settings body with widget-local wheel bindings."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_BODY)
        self.scrollbar = tk.Scrollbar(self, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")
        self.canvas = tk.Canvas(
            self, bg=BG_BODY, width=440, height=338, highlightthickness=0,
            yscrollcommand=self.scrollbar.set, yscrollincrement=24,
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.configure(command=self.canvas.yview)
        self.body = tk.Frame(self.canvas, bg=BG_BODY)
        self._body_item = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._update_region)
        self.canvas.bind("<Configure>", self._resize)

    def _update_region(self, _event=None):
        self.canvas.configure(scrollregion=(
            0, 0, self.canvas.winfo_width(),
            max(self.body.winfo_reqheight(), self.canvas.winfo_height()),
        ))

    def _resize(self, event):
        self.canvas.itemconfigure(self._body_item, width=event.width)
        self._update_region()

    def scroll_to_top(self):
        self.update_idletasks()
        self._update_region()
        self.canvas.yview_moveto(0)

    def bind_mousewheel(self):
        # Bind only our descendants, never bind_all: other windows keep their behavior.
        def bind_tree(widget):
            widget.bind("<MouseWheel>", self._on_mousewheel)
            for child in widget.winfo_children():
                bind_tree(child)
        bind_tree(self)

    def _on_mousewheel(self, event):
        if event.delta and self.body.winfo_reqheight() > self.canvas.winfo_height():
            steps = max(1, abs(event.delta) // 120)
            self.canvas.yview_scroll(-steps if event.delta > 0 else steps, "units")
        # Prevent a hovered scale/spinbox from changing settings while scrolling.
        return "break"


class Toggle(tk.Canvas):
    def __init__(self, parent, variable, command=None):
        super().__init__(parent, width=42, height=24, bg=BG_PANEL,
                         highlightthickness=1, highlightbackground=BG_PANEL,
                         highlightcolor=ACCENT, takefocus=True, cursor="hand2")
        self.variable, self.command = variable, command
        self._trace = variable.trace_add("write", self._draw)
        self.bind("<Button-1>", self.invoke)
        self.bind("<space>", self.invoke)
        self.bind("<Return>", self.invoke)
        self.bind("<Destroy>", self._cleanup)
        self._draw()

    def _draw(self, *_):
        self.delete("all")
        enabled = bool(self.variable.get())
        color = ACCENT if enabled else "#486071"
        self.create_oval(2, 2, 22, 22, fill=color, outline=color)
        self.create_oval(20, 2, 40, 22, fill=color, outline=color)
        self.create_rectangle(12, 2, 30, 22, fill=color, outline=color)
        x = 22 if enabled else 4
        self.create_oval(x, 4, x + 16, 20, fill="#153D34" if enabled else TEXT, outline="")

    def invoke(self, _event=None):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()
        return "break"

    def _cleanup(self, event):
        if event.widget is self:
            self.variable.trace_remove("write", self._trace)
