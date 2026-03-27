#!/usr/bin/env python3
"""
Test Blob connectivity and verify users.json can be read from Blob.

Usage:
    python test_blob_connection.py
"""

import os
import sys
from dotenv import load_dotenv
import warnings

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Load environment variables from .env
load_dotenv()

# Set Blob backend for testing
os.environ["JSON_DB_BACKEND"] = "vercel_blob"

# Check required variables
BLOB_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN", "").strip('"')

if not BLOB_TOKEN:
    print("ERROR: BLOB_READ_WRITE_TOKEN not set in .env file")
    sys.exit(1)

print("✓ Environment variables loaded\n")

from utils.json_db import load_json

print(f"Backend: Vercel Blob (Private)")
print(f"Token: {BLOB_TOKEN[:20]}...")
print()

# Test: Load users.json from Blob
print("Test: Loading users.json from Blob...")
print(f"  Path: data/users.json")

users = load_json("data/users.json", [])
print(f"  Loaded {len(users)} users")

if users:
    print("\nUsers found:")
    for user in users:
        print(f"  - {user.get('email')} ({user.get('role')})")
    print("\n✓ Blob connection is working!")
else:
    print("  WARNING: No users loaded. Either:")
    print("    1. Blob is empty (run sync_data_to_blob.py first)")
    print("    2. Connection issue (check token and permissions)")
    sys.exit(1)
