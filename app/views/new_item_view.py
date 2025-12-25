from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class NewItemView(ttk.LabelFrame):
    """
    新規作成の入力UI。
    フォーム値の検証は外から渡した関数で行い、ボタン活性もview側で反映。
    """

    def __init__(
        self,
        master,
        *,
        on_browse: Callable[[], None],
        on_add: Callable[[], None],
        on_validate: Callable[[], bool],
    ):
        super().__init__(master, text="新規作成（コード + フォルダ）", padding=10)

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
        self.btn_add = ttk.Button(r2, text="保存（追加）", command=on_add, state="disabled")
        self.btn_add.pack(side="left")
        ttk.Label(r2, text="※ 新規作成：参照は「最後に開いたフォルダ」から開きます").pack(side="left", padx=(12, 0))

        self.var_code.trace_add("write", lambda *_: self._refresh_enabled())
        self.var_folder.trace_add("write", lambda *_: self._refresh_enabled())

    def _refresh_enabled(self) -> None:
        ok = bool(self.on_validate())
        self.btn_add.configure(state=("normal" if ok else "disabled"))

    def clear(self) -> None:
        self.var_code.set("")
        self.var_folder.set("")

    def get_values(self) -> tuple[str, str]:
        return self.var_code.get(), self.var_folder.get()

    def set_folder(self, folder: str) -> None:
        self.var_folder.set(folder)
