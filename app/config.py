import json
import sys
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

from .constants import CONFIG_FILENAME
from .utils import now_iso


def app_base_dir() -> Path:
    """
    将来exe化したときに「exeが入っているフォルダ直下にjson」を置くための基準。
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return Path(sys.executable).resolve().parent
    # 開発時：main.py があるフォルダ（watcher_app/）
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return app_base_dir() / CONFIG_FILENAME


@dataclass
class WatchItem:
    id: str
    code: str
    folder: str
    is_active: bool = True
    is_deleted: bool = False
    created_at: str = ""
    updated_at: str = ""

    def touch(self) -> None:
        self.updated_at = now_iso()


@dataclass
class AppSettings:
    interval_seconds: int = 900
    popup_persistent: bool = True
    popup_seconds: int = 60
    last_browse_dir: str = ""


@dataclass
class AppConfig:
    version: int
    settings: AppSettings
    items: List[WatchItem]


def default_config() -> AppConfig:
    return AppConfig(version=1, settings=AppSettings(), items=[])


def load_config() -> AppConfig:
    p = config_path()
    if not p.exists():
        return default_config()

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default_config()

    s = data.get("settings", {}) or {}
    settings = AppSettings(
        interval_seconds=int(s.get("interval_seconds", 900)),
        popup_persistent=bool(s.get("popup_persistent", True)),
        popup_seconds=int(s.get("popup_seconds", 60)),
        last_browse_dir=str(s.get("last_browse_dir", "") or ""),
    )

    items: List[WatchItem] = []
    for it in (data.get("items", []) or []):
        try:
            items.append(
                WatchItem(
                    id=str(it.get("id") or uuid.uuid4()),
                    code=str(it.get("code") or "000"),
                    folder=str(it.get("folder") or ""),
                    is_active=bool(it.get("is_active", True)),
                    is_deleted=bool(it.get("is_deleted", False)),
                    created_at=str(it.get("created_at") or ""),
                    updated_at=str(it.get("updated_at") or ""),
                )
            )
        except Exception:
            continue

    return AppConfig(version=int(data.get("version", 1)), settings=settings, items=items)


def save_config(cfg: AppConfig) -> None:
    payload = {
        "version": cfg.version,
        "settings": asdict(cfg.settings),
        "items": [asdict(x) for x in cfg.items],
    }
    config_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
