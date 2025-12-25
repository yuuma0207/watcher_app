from __future__ import annotations

from tkinter import ttk
from typing import Callable, List, Tuple


class WatchListView(ttk.LabelFrame):
    """
    監視一覧の表示と、選択/白クリック解除のイベントだけを提供。
    データ投入（refresh）は外から values を渡す。
    """

    def __init__(
        self,
        master,
        *,
        on_toggle_selected: Callable[[], None],
        on_soft_delete_selected: Callable[[], None],
        on_select_changed: Callable[[List[str]], None],
        on_blank_click: Callable[[], None],
    ):
        super().__init__(master, text="監視一覧（緑=監視中 / 赤=一時停止）", padding=10)

        cols = ("status", "code", "folder")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="extended", height=12)
        self.tree.heading("status", text="状態")
        self.tree.heading("code", text="コード")
        self.tree.heading("folder", text="フォルダ")
        self.tree.column("status", width=70, anchor="center")
        self.tree.column("code", width=80, anchor="center")
        self.tree.column("folder", width=720, anchor="w")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        ops = ttk.Frame(master)
        ops.pack(fill="x", pady=(10, 0))

        ttk.Button(ops, text="選択行を 監視↔停止 切替", command=on_toggle_selected).pack(side="left")
        ttk.Button(ops, text="選択行を 論理削除", command=on_soft_delete_selected).pack(side="left", padx=(8, 0))
        ttk.Label(ops, text="（論理削除した行は「完全削除」タブに移動します）").pack(side="left", padx=(14, 0))

        # 選択変更 → callback
        def handle_select(_evt=None):
            on_select_changed(list(self.tree.selection()))

        self.tree.bind("<<TreeviewSelect>>", handle_select)

        # 白いところクリックで選択解除
        def handle_click(event):
            row = self.tree.identify_row(event.y)
            if not row:
                self.tree.selection_remove(self.tree.selection())
                on_blank_click()

        self.tree.bind("<Button-1>", handle_click, add=True)

        # ダブルクリックは従来通り：toggle
        self.tree.bind("<Double-1>", lambda e: on_toggle_selected())

        # 色
        self.tree.tag_configure("active", foreground="#2ecc71")
        self.tree.tag_configure("paused", foreground="#e74c3c")

    def refresh(self, rows: List[Tuple[str, str, str, bool]]) -> None:
        """
        rows: [(id, code, folder, is_active), ...]
        """
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for item_id, code, folder, is_active in rows:
            self.tree.insert(
                "",
                "end",
                iid=item_id,
                values=("●", code, folder),
                tags=("active" if is_active else "paused",),
            )

    def selected_ids(self) -> List[str]:
        return list(self.tree.selection())

    def select_single(self, item_id: str) -> None:
        self.tree.selection_set([item_id])
