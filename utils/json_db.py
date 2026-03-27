import json
import os
import shutil
from datetime import datetime
from typing import Any
import warnings

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Check if we should use Vercel Blob storage
USE_BLOB = os.getenv("JSON_DB_BACKEND") == "vercel_blob"

if USE_BLOB:
    try:
        from vercel.blob import put, get, list as blob_list
    except ImportError:
        try:
            import vercel_blob
            put = vercel_blob.put
            get = vercel_blob.get
        except ImportError:
            # Try requests-based approach
            import requests
            BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip('"')
            USE_BLOB = False  # Fall back to requests implementation
            print("Warning: vercel-blob not properly installed, using requests fallback")


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
    if USE_BLOB:
        try:
            import requests
            BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip('"')
            BLOB_BASE_URL = os.getenv("VERCEL_BLOB_BASE_URL", "").strip('"')
            blob_key = _blob_key_from_path(path)
            
            # Use private store base URL
            url = f"{BLOB_BASE_URL}/{blob_key}"
            headers = {"Authorization": f"Bearer {BLOB_TOKEN}"}
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Blob fetch failed ({response.status_code}): {blob_key}")
                return default
        except Exception as e:
            print(f"Error loading from blob {path}: {e}")
            return default
    else:
        # Local file storage
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default


def save_json(path: str, data: Any) -> None:
    """Save JSON to either local file or Vercel Blob based on JSON_DB_BACKEND"""
    if USE_BLOB:
        try:
            import requests
            BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip('"')
            blob_key = _blob_key_from_path(path)
            json_str = json.dumps(data, indent=2)
            
            # Upload to Vercel Blob API endpoint
            headers = {
                "Authorization": f"Bearer {BLOB_TOKEN}",
                "x-content-type": "application/json",
                "x-access": "private",  # REQUIRED for private stores
            }
            response = requests.put(
                "https://blob.vercel-storage.com/",
                params={"pathname": blob_key},
                headers=headers,
                data=json_str.encode('utf-8'),
                timeout=30,
                verify=False  # Disable SSL verification for Windows
            )
            
            if response.status_code == 200:
                print(f"Saved to blob: {blob_key}")
            else:
                print(f"Blob save failed ({response.status_code}): {blob_key}")
                print(f"Response: {response.text[:200]}")
                raise Exception(f"Failed to save to blob: {response.status_code}")
        except Exception as e:
            print(f"Error saving to blob {path}: {e}")
            raise
    else:
        # Local file storage
        ensure_parent_dir(path)
        if os.path.exists(path):
            backup_dir = os.path.join(os.path.dirname(path), "_backups")
            os.makedirs(backup_dir, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(path, os.path.join(backup_dir, f"{os.path.basename(path)}.{stamp}.bak"))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
