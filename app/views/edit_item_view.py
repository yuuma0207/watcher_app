from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class EditItemView(ttk.LabelFrame):
    """
    編集UI（1行選択時のみ有効）。
    編集解除ボタンは不要：外部から enable/disable を呼び分ける。
    """

    def __init__(
        self,
        master,
        *,
        on_browse: Callable[[], None],
        on_update: Callable[[], None],
        on_duplicate: Callable[[], None],
        on_validate: Callable[[], bool],
    ):
        super().__init__(master, text="編集（一覧で1行選択すると編集できます）", padding=10)

        self.on_validate = on_validate

        self.var_code = tk.StringVar()
        self.var_folder = tk.StringVar()

        r = ttk.Frame(self)
        r.pack(fill="x")

        ttk.Label(r, text="担当コード(3桁)").pack(side="left")
        ttk.Entry(r, width=10, textvariable=self.var_code).pack(side="left", padx=(8, 12))

        ttk.Label(r, text="監視フォルダ").pack(side="left")
        ttk.Entry(r, width=60, textvariable=self.var_folder).pack(side="left", padx=(8, 6), fill="x", expand=True)

        ttk.Button(r, text="参照…", command=on_browse).pack(side="left")

        r2 = ttk.Frame(self)
        r2.pack(fill="x", pady=(10, 0))

        self.btn_update = ttk.Button(r2, text="上書き保存（更新）", command=on_update, state="disabled")
        self.btn_update.pack(side="left")

        self.btn_dup = ttk.Button(r2, text="複製", command=on_duplicate, state="disabled")
        self.btn_dup.pack(side="left", padx=(8, 0))

        ttk.Label(r2, text="※ 編集：参照は「編集対象のフォルダ」から開きます／白い所クリックで選択解除").pack(side="left", padx=(12, 0))

        self.var_code.trace_add("write", lambda *_: self._refresh_enabled())
        self.var_folder.trace_add("write", lambda *_: self._refresh_enabled())

        # 初期は無効
        self.set_enabled(False)

    def _refresh_enabled(self) -> None:
        ok = bool(self.on_validate())
        self.btn_update.configure(state=("normal" if ok else "disabled"))
        self.btn_dup.configure(state=("normal" if ok else "disabled"))

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._set_children_state(self, state)
        if not enabled:
            self.btn_update.configure(state="disabled")
            self.btn_dup.configure(state="disabled")

    def _set_children_state(self, widget: tk.Widget, state: str) -> None:
        for child in widget.winfo_children():
            try:
                cls = child.winfo_class()
                if cls in ("TEntry", "TSpinbox", "TButton", "TCheckbutton"):
                    child.configure(state=state)
            except Exception:
                pass
            if child.winfo_children():
                self._set_children_state(child, state)

    def set_values(self, code: str, folder: str) -> None:
        self.var_code.set(code)
        self.var_folder.set(folder)

    def clear(self) -> None:
        self.var_code.set("")
        self.var_folder.set("")

    def get_values(self) -> tuple[str, str]:
        return self.var_code.get(), self.var_folder.get()

    def set_folder(self, folder: str) -> None:
        self.var_folder.set(folder)
