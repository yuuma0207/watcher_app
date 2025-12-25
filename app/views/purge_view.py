from __future__ import annotations

from tkinter import ttk
from typing import Callable, List, Tuple


class PurgeView(ttk.LabelFrame):
    def __init__(
        self,
        master,
        *,
        on_purge: Callable[[], None],
        on_restore: Callable[[], None],
    ):
        super().__init__(master, text="論理削除済み一覧（ここから完全削除）", padding=10)

        cols = ("code", "folder", "deleted")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="extended", height=14)
        self.tree.heading("code", text="コード")
        self.tree.heading("folder", text="フォルダ")
        self.tree.heading("deleted", text="論理削除")
        self.tree.column("code", width=80, anchor="center")
        self.tree.column("folder", width=740, anchor="w")
        self.tree.column("deleted", width=120, anchor="center")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        ops = ttk.Frame(master)
        ops.pack(fill="x", pady=(10, 0))
        ttk.Button(ops, text="選択行を 完全削除（JSONから除去）", command=on_purge).pack(side="left")
        ttk.Button(ops, text="選択行を 復元（削除解除）", command=on_restore).pack(side="left", padx=(8, 0))
        ttk.Label(ops, text="※ 完全削除は元に戻せません").pack(side="left", padx=(14, 0))

    def refresh(self, rows: List[Tuple[str, str, str]]) -> None:
        """
        rows: [(id, code, folder), ...]
        """
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for item_id, code, folder in rows:
            self.tree.insert("", "end", iid=item_id, values=(code, folder, "削除済み"))

    def selected_ids(self) -> List[str]:
        return list(self.tree.selection())
