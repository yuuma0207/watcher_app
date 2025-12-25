from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# Windows専用
if sys.platform == "win32":
    import winreg


def should_show_button_for_debug() -> bool:
    """
    macOS等でもUI確認したいとき用。
    STARTUP_DEBUG=1 でボタンを強制表示（実処理は行わない）。
    """
    return os.environ.get("STARTUP_DEBUG", "").strip() == "1"


def is_supported() -> bool:
    """Windows かつ PyInstaller等で固められた実行ファイルのときだけ対応"""
    return (sys.platform == "win32") and bool(getattr(sys, "frozen", False))


def _run_key():
    # 現在ユーザーのみ（管理者権限不要）
    return winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_registered(entry_name: str) -> bool:
    if not is_supported():
        return False
    hive, subkey = _run_key()
    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, entry_name)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def register(entry_name: str, exe_path: Optional[str] = None) -> None:
    """
    スタートアップ登録（ログイン時に起動）
    - exe_path省略時は sys.executable を使用
    """
    if not is_supported():
        raise RuntimeError("Startup registration is supported only on frozen Windows builds.")

    exe = exe_path or sys.executable
    exe = str(Path(exe).resolve())

    # パスにスペースがあってもOKなように引用符を付ける
    value = f"\"{exe}\""

    hive, subkey = _run_key()
    with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, entry_name, 0, winreg.REG_SZ, value)


def unregister(entry_name: str) -> None:
    if not is_supported():
        raise RuntimeError("Startup unregistration is supported only on frozen Windows builds.")

    hive, subkey = _run_key()
    with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as k:
        try:
            winreg.DeleteValue(k, entry_name)
        except FileNotFoundError:
            pass
