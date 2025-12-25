import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_code(code_raw: str) -> Optional[str]:
    s = (code_raw or "").strip()
    if not s:
        return None
    if re.fullmatch(r"\d+", s):
        n = int(s)
        if 0 <= n <= 999:
            return f"{n:03d}"
        return None
    if re.fullmatch(r"\d{3}", s):
        return s
    return None


def is_office_temp_file(name: str) -> bool:
    return name.startswith("~$")


def extract_leading_3digit_code(filename: str) -> Optional[str]:
    """
    VBA互換：
      - 拡張子除去後のベース名先頭3文字が数字
      - ただし4文字目も数字なら除外（0012... は除外）
    """
    base = Path(filename).stem
    if len(base) < 3:
        return None
    head3 = base[:3]
    if not re.fullmatch(r"\d{3}", head3):
        return None
    if len(base) >= 4 and base[3].isdigit():
        return None
    return head3


def folder_key(path: str) -> str:
    # VBA互換（大文字化）
    return str(Path(path).resolve()).upper()


def is_valid_dir(path_str: str) -> bool:
    try:
        p = Path(path_str)
        return p.exists() and p.is_dir()
    except Exception:
        return False
