import queue
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .config import AppConfig, WatchItem, load_config, save_config, config_path
from .constants import APP_TITLE, STARTUP_ENTRY_NAME
from .monitor import MonitorWorker
from .utils import now_iso, normalize_code, is_valid_dir

from .startup import is_supported as startup_supported
from .startup import is_registered as startup_is_registered
from .startup import register as startup_register, unregister as startup_unregister
from .startup import should_show_button_for_debug


from .views.settings_view import SettingsView
from .views.new_item_view import NewItemView
from .views.edit_item_view import EditItemView
from .views.watch_list_view import WatchListView
from .views.purge_view import PurgeView
from .views.popup_manager import PopupManager


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(980, 700)

        self.cfg: AppConfig = load_config()
        self.q: "queue.Queue[dict]" = queue.Queue()
        self.monitor = MonitorWorker(self._get_config_snapshot, self.q)
        self.monitor_running = False

        self.popup = PopupManager(self)

        # 編集中のID（一覧の選択が1行のときのみ）
        self.editing_id: Optional[str] = None

        self._build_ui()
        self._refresh_all()

        # 起動時に自動で監視開始
        self.after(0, self._start_monitor)

        self.after(150, self._poll_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _get_config_snapshot(self) -> AppConfig:
        return self.cfg
    
    # 親フォルダを返す共通関数
    def _parent_dir_or_none(self, path_str: str | None) -> str | None:
        if not path_str:
            return None
        try:
            p = Path(path_str).expanduser().resolve()
            parent = p.parent
            if parent == p:  # ルート対策（C:\ や /）
                return str(p)
            return str(parent)
        except Exception:
            return None

    
    # スタートアップ用のメソッド
    def _refresh_startup_button_text(self) -> None:
        if not getattr(self, "btn_startup", None):
            return
        # ================ DEBUG ================
        if not startup_supported():
            self.btn_startup.configure(text="スタートアップ（Windows専用）")
            return
        try:
            if startup_is_registered(STARTUP_ENTRY_NAME):
                self.btn_startup.configure(text="スタートアップ解除")
            else:
                self.btn_startup.configure(text="スタートアップに登録")
        except Exception:
            # 何かあっても落とさない
            self.btn_startup.configure(text="スタートアップ設定")

    def _toggle_startup(self) -> None:
        # ★ macOS等の動作確認用（UIだけ）
        if not startup_supported():
            messagebox.showinfo("スタートアップ", "スタートアップ登録/解除は Windows版（exe化）でのみ利用できます。")
            return
        try:
            if startup_is_registered(STARTUP_ENTRY_NAME):
                if not messagebox.askyesno("確認", "スタートアップ登録を解除しますか？"):
                    return
                startup_unregister(STARTUP_ENTRY_NAME)
                messagebox.showinfo("完了", "スタートアップ登録を解除しました。")
            else:
                if not messagebox.askyesno("確認", "スタートアップに登録しますか？（次回ログイン時に自動起動）"):
                    return
                startup_register(STARTUP_ENTRY_NAME)
                messagebox.showinfo("完了", "スタートアップに登録しました。")
        except Exception as e:
            messagebox.showerror("失敗", f"スタートアップ設定に失敗しました。\n{e}")
        finally:
            self._refresh_startup_button_text()


    # ----------------------------
    # Build UI
    # ----------------------------
    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        # header
        header = ttk.Frame(root)
        header.pack(fill="x")
        # --- 左側ブロック ---
        left = ttk.Frame(header)
        left.pack(side="left", fill="x")

        self.status_dot = tk.Canvas(left, width=14, height=14, highlightthickness=0)
        self.status_dot.pack(side="left")
        self._set_overall_status(False)

        self.status_label = ttk.Label(left, text="停止中", font=("", 12, "bold"))
        self.status_label.pack(side="left", padx=(8, 16))

        self.btn_start = ttk.Button(left, text="監視開始", command=self._start_monitor)
        self.btn_start.pack(side="left")

        self.btn_stop = ttk.Button(left, text="停止", command=self._stop_monitor, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))

        self.btn_run_once = ttk.Button(left, text="今すぐ1回実行", command=self._run_once)
        self.btn_run_once.pack(side="left", padx=(16, 0))

        # --- 右側ブロック（★ ここがポイント） ---
        right = ttk.Frame(header)
        right.pack(side="right")

        self.btn_startup = None
        if startup_supported() or should_show_button_for_debug():
            self.btn_startup = ttk.Button(right, command=self._toggle_startup)
            self.btn_startup.pack(side="right")
            self._refresh_startup_button_text()

        ttk.Separator(root).pack(fill="x", pady=12)

        # notebook
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)

        tab_main = ttk.Frame(nb, padding=10)
        tab_purge = ttk.Frame(nb, padding=10)
        nb.add(tab_main, text="監視 / 設定")
        nb.add(tab_purge, text="完全削除")

        # --- main tab layout
        self.settings_view = SettingsView(
            tab_main,
            interval_seconds=self.cfg.settings.interval_seconds,
            popup_persistent=self.cfg.settings.popup_persistent,
            popup_seconds=self.cfg.settings.popup_seconds,
            notify_folder_access_error=self.cfg.settings.notify_folder_access_error,
            on_save=self._save_settings,
        )
        self.settings_view.pack(fill="x")

        ttk.Separator(tab_main).pack(fill="x", pady=12)

        self.new_view = NewItemView(
            tab_main,
            on_browse=self._browse_folder_new,
            on_add=self._add_item,
            on_validate=self._validate_new_inputs,
        )
        self.new_view.pack(fill="x")

        self.edit_view = EditItemView(
            tab_main,
            on_browse=self._browse_folder_edit,
            on_update=self._update_item,
            on_duplicate=self._duplicate_current_edit,
            on_validate=self._validate_edit_inputs,
        )
        self.edit_view.pack(fill="x", pady=(10, 0))

        ttk.Separator(tab_main).pack(fill="x", pady=12)

        # watch list + ops
        self.watch_list = WatchListView(
            tab_main,
            on_toggle_selected=self._toggle_selected,
            on_soft_delete_selected=self._soft_delete_selected,
            on_select_changed=self._on_watch_selection_changed,
            on_blank_click=self._exit_edit_mode,
        )
        self.watch_list.pack(fill="both", expand=True)

        # --- purge tab layout
        self.purge_view = PurgeView(
            tab_purge,
            on_purge=self._purge_selected,
            on_restore=self._restore_selected,
        )
        self.purge_view.pack(fill="both", expand=True)

        footer = ttk.Frame(root)
        footer.pack(fill="x", pady=(10, 0))
        ttk.Label(footer, text=f"設定ファイル: {config_path()}").pack(side="left")

    # ----------------------------
    # Header status
    # ----------------------------
    def _set_overall_status(self, running: bool) -> None:
        self.status_dot.delete("all")
        color = "#2ecc71" if running else "#e74c3c"
        self.status_dot.create_oval(2, 2, 12, 12, fill=color, outline=color)

    # ----------------------------
    # Settings save
    # ----------------------------
    def _save_settings(self) -> None:
        try:
            m = int(self.settings_view.var_interval_min.get() or "0")
            s = int(self.settings_view.var_interval_sec.get() or "0")
            if m < 0 or s < 0 or s > 59:
                raise ValueError
            interval = m * 60 + s
            if interval <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("入力エラー", "サイクル間隔が不正です（例：9分0秒 → 9 / 0）")
            return

        popup_persistent = bool(self.settings_view.var_popup_persistent.get())
        popup_seconds = self.cfg.settings.popup_seconds
        if not popup_persistent:
            try:
                popup_seconds = int(self.settings_view.var_popup_sec.get() or "60")
                if popup_seconds <= 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("入力エラー", "ポップアップ表示秒数(秒)が不正です")
                return
            
        notify_folder_access_error = bool(self.settings_view.var_notify_access_error.get())

        self.cfg.settings.interval_seconds = interval
        self.cfg.settings.popup_persistent = popup_persistent
        self.cfg.settings.popup_seconds = int(popup_seconds)
        self.cfg.settings.notify_folder_access_error = notify_folder_access_error


        try:
            save_config(self.cfg)
            messagebox.showinfo("保存", "設定を保存しました。")
        except Exception as e:
            messagebox.showerror("保存失敗", f"設定ファイルの保存に失敗しました。\n{e}")

    # ----------------------------
    # Browse folder (new/edit behavior)
    # ----------------------------
    def _remember_browse_dir(self, selected_dir: str) -> None:
        try:
            self.cfg.settings.last_browse_dir = str(Path(selected_dir).resolve())
            save_config(self.cfg)
        except Exception:
            pass

    def _browse_folder_new(self) -> None:
        base = self.cfg.settings.last_browse_dir if is_valid_dir(self.cfg.settings.last_browse_dir) else None
        initial = self._parent_dir_or_none(base)

        d = filedialog.askdirectory(title="監視フォルダを選択（新規作成）", initialdir=initial or None)
        if d:
            self.new_view.set_folder(d)
            self._remember_browse_dir(d)


    def _browse_folder_edit(self) -> None:
        initial = None
        if self.editing_id:
            it = self._find_item(self.editing_id)
            if it and is_valid_dir(it.folder):
                initial = self._parent_dir_or_none(it.folder)

        if not initial:
            base = self.cfg.settings.last_browse_dir if is_valid_dir(self.cfg.settings.last_browse_dir) else None
            initial = self._parent_dir_or_none(base)

        d = filedialog.askdirectory(title="監視フォルダを選択（編集）", initialdir=initial or None)
        if d:
            self.edit_view.set_folder(d)
            self._remember_browse_dir(d)


    # ----------------------------
    # Validation for views
    # ----------------------------
    def _validate_new_inputs(self) -> bool:
        code_raw, folder = self.new_view.get_values()
        code = normalize_code(code_raw)
        return bool(code) and is_valid_dir((folder or "").strip())

    def _validate_edit_inputs(self) -> bool:
        if not self.editing_id:
            return False
        code_raw, folder = self.edit_view.get_values()
        code = normalize_code(code_raw)
        return bool(code) and is_valid_dir((folder or "").strip())

    # ----------------------------
    # Items operations
    # ----------------------------
    def _find_item(self, item_id: str) -> Optional[WatchItem]:
        for it in self.cfg.items:
            if it.id == item_id:
                return it
        return None

    def _add_item(self) -> None:
        code_raw, folder = self.new_view.get_values()
        code = normalize_code(code_raw)
        folder = (folder or "").strip()

        if not code:
            messagebox.showerror("入力エラー", "担当コードが不正です（3桁数字）")
            return
        if not is_valid_dir(folder):
            messagebox.showerror("入力エラー", "監視フォルダが存在しません")
            return

        item = WatchItem(
            id=str(uuid.uuid4()),
            code=code,
            folder=str(Path(folder).resolve()),
            is_active=True,
            is_deleted=False,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        self.cfg.items.append(item)
        try:
            save_config(self.cfg)
        except Exception as e:
            messagebox.showerror("保存失敗", f"設定ファイルの保存に失敗しました。\n{e}")
            self.cfg.items = [x for x in self.cfg.items if x.id != item.id]
            return

        self.new_view.clear()
        self._refresh_all()

    def _update_item(self) -> None:
        if not self.editing_id:
            return
        it = self._find_item(self.editing_id)
        if not it or it.is_deleted:
            self._exit_edit_mode()
            return

        code_raw, folder = self.edit_view.get_values()
        code = normalize_code(code_raw)
        folder = (folder or "").strip()

        if not code:
            messagebox.showerror("入力エラー", "担当コードが不正です（3桁数字）")
            return
        if not is_valid_dir(folder):
            messagebox.showerror("入力エラー", "監視フォルダが存在しません")
            return

        it.code = code
        it.folder = str(Path(folder).resolve())
        it.touch()

        try:
            save_config(self.cfg)
        except Exception as e:
            messagebox.showerror("保存失敗", f"設定ファイルの保存に失敗しました。\n{e}")
            return

        self._refresh_all()
        self.watch_list.select_single(it.id)

    def _duplicate_current_edit(self) -> None:
        if not self.editing_id:
            return
        src = self._find_item(self.editing_id)
        if not src or src.is_deleted:
            return

        new_item = WatchItem(
            id=str(uuid.uuid4()),
            code=src.code,
            folder=src.folder,
            is_active=src.is_active,
            is_deleted=False,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        self.cfg.items.append(new_item)

        try:
            save_config(self.cfg)
        except Exception as e:
            messagebox.showerror("保存失敗", f"設定ファイルの保存に失敗しました。\n{e}")
            self.cfg.items = [x for x in self.cfg.items if x.id != new_item.id]
            return

        self._refresh_all()
        self.watch_list.select_single(src.id)  # 編集対象は維持

    # ----------------------------
    # Watch list selection → edit mode
    # ----------------------------
    def _on_watch_selection_changed(self, selected_ids: List[str]) -> None:
        if len(selected_ids) == 1:
            self._enter_edit_mode(selected_ids[0])
        else:
            self._exit_edit_mode()

    def _enter_edit_mode(self, item_id: str) -> None:
        it = self._find_item(item_id)
        if not it or it.is_deleted:
            self._exit_edit_mode()
            return
        self.editing_id = item_id
        self.edit_view.set_enabled(True)
        self.edit_view.set_values(it.code, it.folder)

    def _exit_edit_mode(self) -> None:
        self.editing_id = None
        self.edit_view.clear()
        self.edit_view.set_enabled(False)

    # ----------------------------
    # Table operations (toggle/delete/purge)
    # ----------------------------
    def _toggle_selected(self) -> None:
        ids = self.watch_list.selected_ids()
        if not ids:
            return

        changed_rows = {}
        for it in self.cfg.items:
            if it.id in ids and (not it.is_deleted):
                it.is_active = not it.is_active
                it.touch()
                changed_rows[it.id] = it.is_active  # ★ 更新対象だけ覚える

        if not changed_rows:
            return

        try:
            save_config(self.cfg)
        except Exception as e:
            messagebox.showerror("保存失敗", f"設定ファイルの保存に失敗しました。\n{e}")
            return

        # ★全更新しないで、行だけ更新
        self.watch_list.update_status(changed_rows)


    def _soft_delete_selected(self) -> None:
        ids = self.watch_list.selected_ids()
        if not ids:
            return
        if not messagebox.askyesno("確認", "選択行を論理削除しますか？（完全削除タブに移動します）"):
            return

        if self.editing_id and self.editing_id in ids:
            self._exit_edit_mode()

        changed = False
        for it in self.cfg.items:
            if it.id in ids and (not it.is_deleted):
                it.is_deleted = True
                it.is_active = False
                it.touch()
                changed = True

        if changed:
            try:
                save_config(self.cfg)
            except Exception as e:
                messagebox.showerror("保存失敗", f"設定ファイルの保存に失敗しました。\n{e}")
            self._refresh_all()

    def _restore_selected(self) -> None:
        ids = self.purge_view.selected_ids()
        if not ids:
            return
        changed = False
        for it in self.cfg.items:
            if it.id in ids and it.is_deleted:
                it.is_deleted = False
                it.is_active = False
                it.touch()
                changed = True
        if changed:
            try:
                save_config(self.cfg)
            except Exception as e:
                messagebox.showerror("保存失敗", f"設定ファイルの保存に失敗しました。\n{e}")
            self._refresh_all()

    def _purge_selected(self) -> None:
        ids = self.purge_view.selected_ids()
        if not ids:
            return
        if not messagebox.askyesno("最終確認", "選択行を完全削除します。元に戻せません。\nよろしいですか？"):
            return

        before = len(self.cfg.items)
        self.cfg.items = [x for x in self.cfg.items if x.id not in ids]
        if len(self.cfg.items) != before:
            try:
                save_config(self.cfg)
            except Exception as e:
                messagebox.showerror("保存失敗", f"設定ファイルの保存に失敗しました。\n{e}")
            self._refresh_all()

    # ----------------------------
    # Refresh views
    # ----------------------------
    def _refresh_all(self) -> None:
        rows = [(it.id, it.code, it.folder, it.is_active) for it in self.cfg.items if not it.is_deleted]
        self.watch_list.refresh(rows)

        del_rows = [(it.id, it.code, it.folder) for it in self.cfg.items if it.is_deleted]
        self.purge_view.refresh(del_rows)

    # ----------------------------
    # Monitoring controls / queue
    # ----------------------------
    def _start_monitor(self) -> None:
        if self.monitor_running:
            return
        
        # 監視対象がないなら開始しない
        active_items = [it for it in self.cfg.items if (not it.is_deleted) and it.is_active]
        if not active_items:
            return
        
        self.monitor_running = True
        self._set_overall_status(True)
        self.status_label.configure(text="監視中")
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.monitor.start()

    def _stop_monitor(self) -> None:
        if not self.monitor_running:
            return
        self.monitor_running = False
        self._set_overall_status(False)
        self.status_label.configure(text="停止中")
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.monitor.stop()

    def _run_once(self) -> None:
        self.monitor.run_once(show_nohit=True)

    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self.q.get_nowait()
                self._handle_worker_message(msg)
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _handle_worker_message(self, msg: dict) -> None:
        if msg.get("type") != "scan_result":
            return

        hits: Dict[str, List[str]] = msg.get("hits") or {}
        errors: Dict[str, str] = msg.get("errors") or {}
        show_nohit: bool = bool(msg.get("show_nohit", False))

        if hits:
            # hitsがある場合は従来通り（必要なら errors も一緒に表示してもOK）
            self.popup.show_or_update(
                hits,
                popup_persistent=self.cfg.settings.popup_persistent,
                popup_seconds=self.cfg.settings.popup_seconds,
            )
            return

        # hits がない時
        if not show_nohit:
            # フォルダへのアクセスエラーのみ表示
            if errors and self.cfg.settings.notify_folder_access_error:
                lines = [f"{folder}：{reason}" for folder, reason in errors.items()]
                self.popup.show_or_update(
                    {"(アクセスできないフォルダ)": lines},
                    popup_persistent=self.cfg.settings.popup_persistent,
                    popup_seconds=self.cfg.settings.popup_seconds,
                )
            return

        # show_nohit=True（起動直後/今すぐ1回）
        if errors and self.cfg.settings.notify_folder_access_error:
            lines = [f"{folder}：{reason}" for folder, reason in errors.items()]
            self.popup.show_or_update(
                {"(監視結果)": ["該当ファイルはありませんでした。"], "(アクセスできないフォルダ)": lines},
                popup_persistent=self.cfg.settings.popup_persistent,
                popup_seconds=self.cfg.settings.popup_seconds,
            )
        else:
            self.popup.show_or_update(
                {"(監視結果)": ["該当ファイルはありませんでした。"]},
                popup_persistent=self.cfg.settings.popup_persistent,
                popup_seconds=self.cfg.settings.popup_seconds,
            )


    # ----------------------------
    # Close
    # ----------------------------
    def _on_close(self) -> None:
        try:
            self.monitor.stop()
        except Exception:
            pass
        self.popup.close()
        self.destroy()


def run_app() -> None:
    app = App()
    app.mainloop()
