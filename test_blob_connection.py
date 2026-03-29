#!/usr/bin/env python3
"""
Test Blob connectivity and verify users.json can be read from Blob.

Usage:
    python test_blob_connection.py
"""

import os
import sys
from pathlib import Path

# Load .env file manually (Python doesn't do this automatically)
env_file = Path(".env")
if env_file.exists():
    for line in env_file.read_text().strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            # Remove quotes if present
            value = value.strip().strip('"').strip("'")
            os.environ[key.strip()] = value

# Disable SSL verification for testing (Windows certificate issue)
os.environ["VERCEL_BLOB_VERIFY_SSL"] = "false"

# Set Blob backend
os.environ["JSON_DB_BACKEND"] = "vercel_blob"

# Make sure env vars are set (pull from Vercel or set manually)
required_vars = {
    "BLOB_READ_WRITE_TOKEN": "Bearer token for auth",
    "VERCEL_BLOB_ACCESS": "public or private",
    "VERCEL_BLOB_BASE_URL": "Base URL for blob store",
}

missing = []
for var, desc in required_vars.items():
    if not os.environ.get(var):
        missing.append(f"  - {var}: {desc}")

if missing:
    print("ERROR: Missing required environment variables:")
    for m in missing:
        print(m)
    print()
    print("To fix, run: vercel env pull")
    sys.exit(1)

print("✓ All required env vars are set\n")

from utils.json_db import load_json, _blob_path_from_local_path, _blob_url_from_path, _blob_token, _blob_access, _blob_path_prefix

print(f"Backend: Vercel Blob (Private)")
print(f"Access: {_blob_access()}")
print(f"Token: {_blob_token()[:20]}...")
print(f"Prefix env var: '{os.environ.get('VERCEL_BLOB_PREFIX', 'NOT_SET')}'")
print(f"Prefix function returns: '{_blob_path_prefix()}'")
print()

# Test 1: Load users.json
print("Test 1: Loading users.json from Blob...")
pathname = _blob_path_from_local_path("data/users.json")
print(f"  Pathname: {pathname}")

url = _blob_url_from_path(pathname)
print(f"  URL: {url}")

users = load_json("data/users.json", [])
print(f"  Loaded {len(users)} users")

if users:
    print("\nUsers found:")
    for user in users:
        print(f"  - {user.get('email')} ({user.get('role')})")
else:
    print("  ERROR: No users loaded! Check Blob connectivity.")
    sys.exit(1)

print("\n✓ Blob connection is working!")
