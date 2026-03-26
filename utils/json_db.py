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


def _blob_ssl_verify() -> bool:
    # Allow disabling SSL verification for testing/diagnostics
    return os.environ.get("VERCEL_BLOB_VERIFY_SSL", "true").lower() not in ("false", "0", "no")


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
    # Must check if key exists to distinguish between unset (default) vs empty string
    if "VERCEL_BLOB_PREFIX" in os.environ:
        prefix = os.environ["VERCEL_BLOB_PREFIX"].strip()
    else:
        prefix = "data/"
    
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
        response = requests.get(_VERCEL_BLOB_API_BASE_URL, headers=headers, params=params, timeout=_blob_timeout_seconds(), verify=_blob_ssl_verify())
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
    access = _blob_access()
    
    # For private blobs, add authorization header and download parameter
    if token and access == "private":
        headers["Authorization"] = f"Bearer {token}"
        # Add download parameter to ensure response is treated as file
        if "?" not in url:
            url = f"{url}?download=1"
        else:
            url = f"{url}&download=1"

    try:
        response = requests.get(url, headers=headers, timeout=_blob_timeout_seconds(), verify=_blob_ssl_verify())
        if response.status_code == 404:
            return default
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        # Log error for debugging
        import sys
        print(f"Blob read error for {pathname}: {e}", file=sys.stderr)
        return default


def _blob_put_json(path: str, data: Any) -> None:
    pathname = _blob_path_from_local_path(path)
    payload = json.dumps(data, indent=2).encode("utf-8")

    token = _blob_token()
    if not token:
        raise RuntimeError("BLOB_READ_WRITE_TOKEN must be set when JSON_DB_BACKEND=vercel_blob")

    access = _blob_access()
    headers = {
        "Authorization": f"Bearer {token}",
        "access": access,
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
            verify=_blob_ssl_verify(),
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        import sys
        print(f"Blob write error for {pathname}: {exc}", file=sys.stderr)
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


def upload_file_to_blob(file_content: bytes, blob_pathname: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload a binary file to Vercel Blob storage.
    
    Args:
        file_content: The binary content of the file
        blob_pathname: The pathname in blob storage (e.g., "reports/insync_2026-03.xlsx")
        content_type: MIME type of the file (default: application/octet-stream)
    
    Returns:
        The URL of the uploaded blob
    
    Raises:
        RuntimeError: If upload fails or BLOB_READ_WRITE_TOKEN is not set
    """
    token = _blob_token()
    if not token:
        raise RuntimeError("BLOB_READ_WRITE_TOKEN must be set to upload files to blob storage")
    
    if not file_content:
        raise ValueError("file_content cannot be empty")
    
    # Don't send 'access' header - let the store use its configured access level
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-version": "10",
        "x-content-type": content_type,
        "x-cache-control-max-age": "60",
        "x-allow-overwrite": "1",
    }
    
    import sys
    print(f"[BLOB DEBUG] Uploading to: {blob_pathname}", file=sys.stderr)
    print(f"[BLOB DEBUG] File size: {len(file_content)} bytes", file=sys.stderr)
    print(f"[BLOB DEBUG] Content-Type: {content_type}", file=sys.stderr)
    
    try:
        response = requests.put(
            "https://blob.vercel-storage.com/",
            params={"pathname": blob_pathname},
            headers=headers,
            data=file_content,
            timeout=30,
            verify=_blob_ssl_verify(),
        )
        
        print(f"[BLOB DEBUG] Response status: {response.status_code}", file=sys.stderr)
        
        if response.status_code != 200:
            error_body = response.text
            print(f"[BLOB DEBUG] Error response:\n{error_body}", file=sys.stderr)
            raise RuntimeError(f"Blob upload failed with status {response.status_code}: {error_body}")
        
        result = response.json()
        print(f"[BLOB DEBUG] Upload successful!", file=sys.stderr)
        
    except requests.RequestException as exc:
        print(f"[BLOB DEBUG] Request exception: {type(exc).__name__}: {exc}", file=sys.stderr)
        if hasattr(exc, 'response') and exc.response is not None:
            print(f"[BLOB DEBUG] Response status: {exc.response.status_code}", file=sys.stderr)
            print(f"[BLOB DEBUG] Response headers: {dict(exc.response.headers)}", file=sys.stderr)
            print(f"[BLOB DEBUG] Response body: {exc.response.text}", file=sys.stderr)
        raise RuntimeError(f"Failed to upload file to Vercel Blob path '{blob_pathname}': {exc}") from exc
    except ValueError as exc:
        print(f"[BLOB DEBUG] JSON decode error: {exc}", file=sys.stderr)
        raise RuntimeError(f"Failed to parse response from blob upload for '{blob_pathname}': {exc}") from exc
    
    url = result.get("url")
    if url:
        _BLOB_URL_CACHE[blob_pathname] = str(url)
        print(f"[BLOB DEBUG] Cached URL: {url}", file=sys.stderr)
        return str(url)
    else:
        raise RuntimeError(f"No URL returned from blob upload for '{blob_pathname}'")


def get_blob_download_url(blob_pathname: str) -> Optional[str]:
    """
    Get the download URL for a blob file.
    
    Args:
        blob_pathname: The pathname in blob storage
    
    Returns:
        The download URL, or None if not found
    """
    url = _blob_url_from_path(blob_pathname)
    if not url:
        return None
    
    token = _blob_token()
    access = _blob_access()
    
    # For private blobs, add download parameter
    if token and access == "private":
        if "?" not in url:
            url = f"{url}?download=1"
        else:
            url = f"{url}&download=1"
    
    return url


def download_blob_file(blob_pathname: str) -> Optional[bytes]:
    """
    Download a binary file from Vercel Blob storage.
    
    Args:
        blob_pathname: The pathname in blob storage
    
    Returns:
        The file content as bytes, or None if not found
    """
    url = _blob_url_from_path(blob_pathname)
    if not url:
        return None
    
    headers = {}
    token = _blob_token()
    access = _blob_access()
    
    # For private blobs, add authorization header and download parameter
    if token and access == "private":
        headers["Authorization"] = f"Bearer {token}"
        if "?" not in url:
            url = f"{url}?download=1"
        else:
            url = f"{url}&download=1"
    
    try:
        response = requests.get(url, headers=headers, timeout=_blob_timeout_seconds(), verify=_blob_ssl_verify())
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        import sys
        print(f"Blob download error for {blob_pathname}: {e}", file=sys.stderr)
        return None
