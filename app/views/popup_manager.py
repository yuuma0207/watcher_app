from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional

from ..utils import now_iso


class PopupManager:
    """
    ポップアップは常に1つ。
    新しい通知が来たら内容更新し、オートクローズ時はタイマーをリセット。
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self._win: Optional[tk.Toplevel] = None
        self._text: Optional[tk.Text] = None
        self._time_label: Optional[ttk.Label] = None
        self._timer_id: Optional[str] = None

    def show_or_update(self, hits: Dict[str, List[str]], popup_persistent: bool, popup_seconds: int) -> None:
        self._ensure_window()
        if not self._win or not self._text:
            return

        body = self._format_hits_text(hits)
        if self._time_label:
            try:
                self._time_label.configure(text=now_iso())
            except Exception:
                pass

        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", body)
        self._text.configure(state="disabled")

        try:
            self._win.lift()
        except Exception:
            pass

        self._reset_timer(popup_persistent, popup_seconds)

    def close(self) -> None:
        try:
            if self._timer_id:
                self.root.after_cancel(self._timer_id)
        except Exception:
            pass
        self._timer_id = None

        if self._win is not None:
            try:
                if self._win.winfo_exists():
                    self._win.destroy()
            except Exception:
                pass
        self._win = None
        self._text = None
        self._time_label = None

    # ---- internal ----
    def _format_hits_text(self, hits: Dict[str, List[str]]) -> str:
        lines: List[str] = []
        for folder, files in hits.items():
            lines.append(f"■ {folder}")
            for f in files:
                lines.append(f"  - {f}")
            lines.append("")
        return "\n".join(lines).rstrip()

    def _ensure_window(self) -> None:
        if self._win is not None:
            try:
                if self._win.winfo_exists():
                    return
            except Exception:
                pass
            self._win = None
            self._text = None
            self._time_label = None
            self._timer_id = None

        title = "担当コードファイル検出"
        w = tk.Toplevel(self.root)
        w.title(title)
        w.attributes("-topmost", True)
        w.resizable(True, True)

        def on_close():
            self.close()

        w.protocol("WM_DELETE_WINDOW", on_close)

        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        width, height = 640, 360
        x = max(20, sw - width - 40)
        y = max(20, sh - height - 80)
        w.geometry(f"{width}x{height}+{x}+{y}")

        frame = ttk.Frame(w, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=title, font=("", 14, "bold")).pack(anchor="w")
        tl = ttk.Label(frame, text=now_iso(), foreground="#666")
        tl.pack(anchor="w", pady=(2, 10))

        txt = tk.Text(frame, wrap="word", height=12)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True)

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="閉じる", command=on_close).pack(side="right")

        self._win = w
        self._text = txt
        self._time_label = tl

    def _reset_timer(self, popup_persistent: bool, popup_seconds: int) -> None:
        if popup_persistent:
            if self._timer_id:
                try:
                    self.root.after_cancel(self._timer_id)
                except Exception:
                    pass
                self._timer_id = None
            return

        seconds = max(1, int(popup_seconds))
        if self._timer_id:
            try:
                self.root.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        def closer():
            self.close()

        self._timer_id = self.root.after(seconds * 1000, closer)
