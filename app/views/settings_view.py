from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class SettingsView(ttk.LabelFrame):
    """
    監視設定UIだけを持つView。
    値の保存などの「処理」は外からコールバックで渡す。
    """

    def __init__(
        self,
        master,
        *,
        interval_seconds: int,
        popup_persistent: bool,
        popup_seconds: int,
        on_save: Callable[[], None],
    ):
        super().__init__(master, text="監視の設定", padding=10)

        self.var_interval_min = tk.StringVar(value=str(interval_seconds // 60))
        self.var_interval_sec = tk.StringVar(value=str(interval_seconds % 60))
        self.var_popup_persistent = tk.BooleanVar(value=bool(popup_persistent))
        self.var_popup_sec = tk.StringVar(value=str(popup_seconds))

        row1 = ttk.Frame(self)
        row1.pack(fill="x")
        ttk.Label(row1, text="サイクル間隔").pack(side="left")
        ttk.Spinbox(row1, from_=0, to=999, width=5, textvariable=self.var_interval_min).pack(side="left", padx=(8, 2))
        ttk.Label(row1, text="分").pack(side="left")
        ttk.Spinbox(row1, from_=0, to=59, width=5, textvariable=self.var_interval_sec).pack(side="left", padx=(8, 2))
        ttk.Label(row1, text="秒").pack(side="left")

        row2 = ttk.Frame(self)
        row2.pack(fill="x", pady=(10, 0))
        ttk.Checkbutton(
            row2,
            text="閉じるまで表示（常時表示）",
            variable=self.var_popup_persistent,
            command=self._toggle_popup_seconds_ui,
        ).pack(side="left")

        self.popup_seconds_frame = ttk.Frame(row2)
        ttk.Label(self.popup_seconds_frame, text="  常時表示を外した場合：ポップアップ表示(秒)").pack(side="left")
        ttk.Spinbox(self.popup_seconds_frame, from_=1, to=600, width=6, textvariable=self.var_popup_sec).pack(side="left", padx=(8, 0))
        self._toggle_popup_seconds_ui()

        row3 = ttk.Frame(self)
        row3.pack(fill="x", pady=(10, 0))
        ttk.Button(row3, text="設定を保存", command=on_save).pack(side="left")

    def _toggle_popup_seconds_ui(self) -> None:
        if bool(self.var_popup_persistent.get()):
            self.popup_seconds_frame.pack_forget()
        else:
            self.popup_seconds_frame.pack(side="left", padx=(10, 0))
