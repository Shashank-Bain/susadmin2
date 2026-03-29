#!/usr/bin/env python3
"""
Sync local JSON data files to Vercel Blob storage.
Run this once to populate your Blob store with initial data.

Usage:
    python sync_data_to_blob.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests
import urllib3

# Suppress SSL warnings for Windows certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables from .env
load_dotenv()

# Configure from environment
BLOB_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN", "").strip('"')
BLOB_BASE_URL = os.environ.get("VERCEL_BLOB_BASE_URL", "").strip('"')

DATA_DIR = "data"

if not BLOB_TOKEN:
    print("ERROR: BLOB_READ_WRITE_TOKEN not set in .env file")
    sys.exit(1)

if not BLOB_BASE_URL:
    print("ERROR: VERCEL_BLOB_BASE_URL not set in .env file")
    sys.exit(1)

def upload_file_to_blob(file_path: str, blob_pathname: str) -> bool:
    """Upload a file to Blob and return success."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        
        # Upload to Vercel Blob using requests API
        # Use the standard API endpoint (not the read URL)
        headers = {
            "Authorization": f"Bearer {BLOB_TOKEN}",
            "x-content-type": "application/json",
            "x-access": "private",  # REQUIRED for private stores
        }
        
        response = requests.put(
            "https://blob.vercel-storage.com/",
            params={"pathname": blob_pathname},
            headers=headers,
            data=data,
            timeout=30,
            verify=False  # Disable SSL verification for Windows
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ {file_path} → {blob_pathname}")
            print(f"  URL: {result.get('url', 'N/A')}")
            return True
        else:
            print(f"✗ {file_path} → {blob_pathname}")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ {file_path}: {e}")
        return False

def main():
    print(f"Syncing JSON files to Vercel Blob")
    print(f"  Token: {BLOB_TOKEN[:20]}...")
    print(f"  Base URL: {BLOB_BASE_URL}")
    print()
    
    if not os.path.isdir(DATA_DIR):
        print(f"ERROR: {DATA_DIR}/ directory not found")
        sys.exit(1)
    
    uploaded = 0
    failed = 0
    
    # Upload all JSON files from data/ directory
    for file in sorted(Path(DATA_DIR).glob("*.json")):
        # Blob pathname: data/filename.json
        blob_pathname = f"data/{file.name}"
        if upload_file_to_blob(str(file), blob_pathname):
            uploaded += 1
        else:
            failed += 1
    
    print()
    print(f"Summary: {uploaded} uploaded, {failed} failed")
    
    if failed == 0:
        print("✓ All files synced successfully!")
        return 0
    else:
        print("✗ Some files failed to upload.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
