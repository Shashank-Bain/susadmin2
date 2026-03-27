import json
import os
import shutil
from datetime import datetime
from typing import Any
import warnings

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def _use_blob() -> bool:
    """Check at runtime if we should use blob storage"""
    return os.getenv("JSON_DB_BACKEND") == "vercel_blob"


def ensure_parent_dir(path: str) -> None:
    """Only used for local file storage"""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def _blob_key_from_path(path: str) -> str:
    """Convert local file path to blob key (e.g., 'data/users.json' -> 'data/users.json')"""
    # Normalize path separators to forward slashes for blob storage
    return path.replace("\\", "/")


def load_json(path: str, default: Any):
    """Load JSON from either local file or Vercel Blob based on JSON_DB_BACKEND"""
    if _use_blob():
        try:
            import requests
            BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip('"')
            BLOB_BASE_URL = os.getenv("VERCEL_BLOB_BASE_URL", "").strip('"')
            
            print(f"[BLOB] Backend enabled for {path}")
            print(f"[BLOB] BLOB_TOKEN: {'SET' if BLOB_TOKEN else 'NOT SET'}")
            print(f"[BLOB] BLOB_BASE_URL: {'SET' if BLOB_BASE_URL else 'NOT SET'}")
            
            if not BLOB_TOKEN or not BLOB_BASE_URL:
                print(f"[BLOB] ERROR: Missing credentials for {path}")
                return default
            
            blob_key = _blob_key_from_path(path)
            
            # Use private store base URL
            url = f"{BLOB_BASE_URL}/{blob_key}"
            print(f"[BLOB] Fetching: {url}")
            headers = {"Authorization": f"Bearer {BLOB_TOKEN}"}
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            print(f"[BLOB] Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"[BLOB] Successfully loaded {blob_key} - {len(data) if isinstance(data, list) else 'dict'} items")
                return data
            else:
                print(f"[BLOB] Fetch failed ({response.status_code}): {blob_key}")
                print(f"[BLOB] Response: {response.text[:200]}")
                return default
        except Exception as e:
            print(f"[BLOB] Error loading from blob {path}: {e}")
            import traceback
            print(f"[BLOB] Traceback: {traceback.format_exc()}")
            return default
    else:
        # Local file storage
        print(f"[LOCAL] Backend enabled - Loading from local file: {path}")
        print(f"[LOCAL] JSON_DB_BACKEND = '{os.getenv('JSON_DB_BACKEND', 'not set')}'")
        if not os.path.exists(path):
            print(f"[LOCAL] File not found: {path}")
            return default
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                print(f"[LOCAL] Loaded {len(data) if isinstance(data, list) else 'dict'} items from {path}")
                return data
            except json.JSONDecodeError as e:
                print(f"[LOCAL] JSON decode error in {path}: {e}")
                return default


def save_json(path: str, data: Any) -> None:
    """Save JSON to either local file or Vercel Blob based on JSON_DB_BACKEND"""
    if _use_blob():
        try:
            import requests
            BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip('"')
            BLOB_BASE_URL = os.getenv("VERCEL_BLOB_BASE_URL", "").strip('"')
            blob_key = _blob_key_from_path(path)
            json_str = json.dumps(data, indent=2)
            
            print(f"[BLOB] Saving to blob: {blob_key}")
            
            # Try uploading directly to the private store URL (same as reading)
            url = f"{BLOB_BASE_URL}/{blob_key}"
            headers = {
                "Authorization": f"Bearer {BLOB_TOKEN}",
                "Content-Type": "application/json",
            }
            response = requests.put(
                url,
                headers=headers,
                data=json_str.encode('utf-8'),
                timeout=30,
                verify=False  # Disable SSL verification for Windows
            )
            
            print(f"[BLOB] Save response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                print(f"[BLOB] Saved successfully: {blob_key}")
            else:
                print(f"[BLOB] Save failed ({response.status_code}): {blob_key}")
                print(f"[BLOB] Response: {response.text[:200]}")
                raise Exception(f"Failed to save to blob: {response.status_code}")
        except Exception as e:
            print(f"[BLOB] Error saving to blob {path}: {e}")
            raise
    else:
        # Local file storage
        print(f"[LOCAL] Saving to local file: {path}")
        ensure_parent_dir(path)
        if os.path.exists(path):
            backup_dir = os.path.join(os.path.dirname(path), "_backups")
            os.makedirs(backup_dir, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(path, os.path.join(backup_dir, f"{os.path.basename(path)}.{stamp}.bak"))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
