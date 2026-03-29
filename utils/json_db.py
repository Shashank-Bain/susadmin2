import json
import os
import shutil
from datetime import datetime
from typing import Any


def ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def load_json(path: str, default: Any):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def save_json(path: str, data: Any) -> None:
    ensure_parent_dir(path)
    if os.path.exists(path):
        backup_dir = os.path.join(os.path.dirname(path), "_backups")
        os.makedirs(backup_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, os.path.join(backup_dir, f"{os.path.basename(path)}.{stamp}.bak"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
