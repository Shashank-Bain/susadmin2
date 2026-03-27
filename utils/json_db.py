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
    print(f"[BLOB] Blob backend ENABLED")
    print(f"[BLOB] Checking environment variables...")
    BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip('"')
    BLOB_BASE_URL = os.getenv("VERCEL_BLOB_BASE_URL", "").strip('"')
    print(f"[BLOB] BLOB_TOKEN: {'SET (' + BLOB_TOKEN[:20] + '...)' if BLOB_TOKEN else 'NOT SET'}")
    print(f"[BLOB] BLOB_BASE_URL: {BLOB_BASE_URL if BLOB_BASE_URL else 'NOT SET'}")
    if not BLOB_TOKEN or not BLOB_BASE_URL:
        print(f"[BLOB] WARNING: Missing blob credentials! Will return empty data.")
else:
    print(f"[BLOB] Blob backend DISABLED - using local files")
    print(f"[BLOB] JSON_DB_BACKEND = {os.getenv('JSON_DB_BACKEND', 'not set')}")

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
            
            if not BLOB_TOKEN or not BLOB_BASE_URL:
                print(f"[BLOB] ERROR: Missing credentials for {path}")
                print(f"[BLOB] BLOB_TOKEN present: {bool(BLOB_TOKEN)}")
                print(f"[BLOB] BLOB_BASE_URL present: {bool(BLOB_BASE_URL)}")
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
        print(f"[LOCAL] Loading from local file: {path}")
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
