import json
import os
import shutil
from datetime import datetime
from typing import Optional
from typing import Any

import requests


_VERCEL_BLOB_API_BASE_URL = "https://blob.vercel-storage.com"
_VERCEL_BLOB_API_VERSION = "10"


def _blob_backend_enabled() -> bool:
    return (os.environ.get("JSON_DB_BACKEND", "local") or "local").strip().lower() == "vercel_blob"


def _blob_timeout_seconds() -> int:
    raw = (os.environ.get("VERCEL_BLOB_TIMEOUT_SECONDS", "10") or "10").strip()
    try:
        return max(int(raw), 1)
    except ValueError:
        return 10


def _blob_token() -> str:
    return (os.environ.get("BLOB_READ_WRITE_TOKEN", "") or "").strip()


def _blob_path_prefix() -> str:
    # Keep folder-style paths in Blob to mirror the old local data directory.
    prefix = (os.environ.get("VERCEL_BLOB_PREFIX", "data/") or "data/").strip()
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"
    return prefix


def _blob_access() -> str:
    access = (os.environ.get("VERCEL_BLOB_ACCESS", "public") or "public").strip().lower()
    if access not in {"public", "private"}:
        return "public"
    return access


def _blob_base_url() -> str:
    # Prefer generic base URL var; keep old public-only var for backward compatibility.
    base = (os.environ.get("VERCEL_BLOB_BASE_URL", "") or "").strip().rstrip("/")
    if base:
        return base
    return (os.environ.get("VERCEL_BLOB_PUBLIC_BASE_URL", "") or "").strip().rstrip("/")


def _blob_path_overrides() -> dict[str, str]:
    raw = (os.environ.get("VERCEL_BLOB_PATH_OVERRIDES", "") or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v).lstrip("/") for k, v in parsed.items()}
    except json.JSONDecodeError:
        pass
    return {}


def _blob_path_from_local_path(path: str) -> str:
    file_name = os.path.basename(path)
    overrides = _blob_path_overrides()
    if file_name in overrides:
        return overrides[file_name]
    return f"{_blob_path_prefix()}{file_name}".lstrip("/")


_BLOB_URL_CACHE: dict[str, str] = {}


def _blob_url_from_path(pathname: str) -> Optional[str]:
    if pathname in _BLOB_URL_CACHE:
        return _BLOB_URL_CACHE[pathname]

    base_url = _blob_base_url()
    if base_url:
        url = f"{base_url}/{pathname}"
        _BLOB_URL_CACHE[pathname] = url
        return url

    token = _blob_token()
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    params = {"prefix": pathname, "limit": "1000", "mode": "expanded"}

    try:
        response = requests.get(_VERCEL_BLOB_API_BASE_URL, headers=headers, params=params, timeout=_blob_timeout_seconds())
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError):
        return None

    for blob in result.get("blobs", []):
        if blob.get("pathname") == pathname and blob.get("url"):
            url = str(blob["url"])
            _BLOB_URL_CACHE[pathname] = url
            return url

    return None


def _blob_get_json(path: str, default: Any):
    pathname = _blob_path_from_local_path(path)
    url = _blob_url_from_path(pathname)
    if not url:
        return default

    headers = {}
    token = _blob_token()
    if token and _blob_access() == "private":
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(url, headers=headers, timeout=_blob_timeout_seconds())
        if response.status_code == 404:
            return default
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return default


def _blob_put_json(path: str, data: Any) -> None:
    pathname = _blob_path_from_local_path(path)
    payload = json.dumps(data, indent=2).encode("utf-8")

    token = _blob_token()
    if not token:
        raise RuntimeError("BLOB_READ_WRITE_TOKEN must be set when JSON_DB_BACKEND=vercel_blob")

    headers = {
        "Authorization": f"Bearer {token}",
        "access": _blob_access(),
        "x-api-version": _VERCEL_BLOB_API_VERSION,
        "x-content-type": "application/json",
        "x-cache-control-max-age": "60",
        "x-allow-overwrite": "1",
    }

    try:
        response = requests.put(
            f"{_VERCEL_BLOB_API_BASE_URL}/",
            params={"pathname": pathname},
            headers=headers,
            data=payload,
            timeout=_blob_timeout_seconds(),
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"Failed to write JSON to Vercel Blob path '{pathname}': {exc}") from exc

    url = result.get("url")
    if url:
        _BLOB_URL_CACHE[pathname] = str(url)


def ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def load_json(path: str, default: Any):
    if _blob_backend_enabled():
        return _blob_get_json(path, default)

    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def save_json(path: str, data: Any) -> None:
    if _blob_backend_enabled():
        _blob_put_json(path, data)
        return

    ensure_parent_dir(path)
    if os.path.exists(path):
        backup_dir = os.path.join(os.path.dirname(path), "_backups")
        os.makedirs(backup_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, os.path.join(backup_dir, f"{os.path.basename(path)}.{stamp}.bak"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
