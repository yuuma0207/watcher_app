import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from .config import AppConfig
from .constants import STABLE_WAIT_SECONDS
from .utils import (
    extract_leading_3digit_code,
    folder_key,
    is_office_temp_file,
    is_valid_dir,
)


class MonitorWorker:
    """
    バックグラウンドで周期監視し、結果はUI側が渡した queue に dict を put する。
    """

    def __init__(self, get_config_callable, event_queue):
        self._get_config = get_config_callable
        self._q = event_queue
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def run_once(self, show_nohit: bool = True) -> None:
        cfg: AppConfig = self._get_config()
        hits = self._scan_once(cfg)
        self._q.put({"type": "scan_result", "hits": hits, "show_nohit": show_nohit})

    def _run(self) -> None:
        # 監視開始直後の1回（VBA互換）
        cfg: AppConfig = self._get_config()
        hits = self._scan_once(cfg)
        self._q.put({"type": "scan_result", "hits": hits, "show_nohit": True})

        while not self._stop.is_set():
            cfg = self._get_config()
            interval = max(1, int(cfg.settings.interval_seconds))

            end = time.time() + interval
            while time.time() < end:
                if self._stop.is_set():
                    return
                time.sleep(0.2)

            cfg = self._get_config()
            hits = self._scan_once(cfg)
            # 通常サイクル 0件は無通知（VBA互換）
            self._q.put({"type": "scan_result", "hits": hits, "show_nohit": False})

    def _scan_once(self, cfg: AppConfig) -> Dict[str, List[str]]:
        active_items = [x for x in cfg.items if (not x.is_deleted) and x.is_active]
        if not active_items:
            return {}

        folder_to_codes: Dict[str, Set[str]] = {}
        folder_original: Dict[str, str] = {}

        for it in active_items:
            f = it.folder.strip()
            if not f or not is_valid_dir(f):
                continue
            key = folder_key(f)
            folder_to_codes.setdefault(key, set()).add(it.code)
            folder_original[key] = f

        hits: Dict[str, List[str]] = {}

        for fkey, codes in folder_to_codes.items():
            folder = folder_original.get(fkey, fkey)
            p = Path(folder)
            if not p.exists() or not p.is_dir():
                continue

            try:
                for child in p.iterdir():
                    if child.is_dir():
                        continue
                    name = child.name
                    if is_office_temp_file(name):
                        continue

                    # 保存中チェック（固定2秒）
                    try:
                        size1 = child.stat().st_size
                        time.sleep(STABLE_WAIT_SECONDS)
                        size2 = child.stat().st_size
                        if size1 != size2:
                            continue
                    except Exception:
                        continue

                    code = extract_leading_3digit_code(name)
                    if code and (code in codes):
                        hits.setdefault(folder, []).append(name)
            except Exception:
                continue

        for k in list(hits.keys()):
            hits[k] = sorted(set(hits[k]))

        return hits
