#!/usr/bin/env python3
"""
Test blob upload for Excel files.

Usage:
    python test_blob_upload.py
"""

import os
import sys
from pathlib import Path
from io import BytesIO

# Load .env file manually
env_file = Path(".env")
if env_file.exists():
    for line in env_file.read_text().strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            os.environ[key.strip()] = value

# Disable SSL verification for testing
os.environ["VERCEL_BLOB_VERIFY_SSL"] = "false"

# Set Blob backend
os.environ["JSON_DB_BACKEND"] = "vercel_blob"

from utils.json_db import upload_file_to_blob

print("Testing blob upload for Excel files...")
print()

# Create a simple test file content
test_content = b"This is a test file content for blob upload"
test_pathname = "reports/test_upload.txt"

print(f"Test 1: Upload simple text file")
print(f"  Pathname: {test_pathname}")

try:
    url = upload_file_to_blob(test_content, test_pathname, "text/plain")
    print(f"  ✓ Upload successful!")
    print(f"  URL: {url}")
except Exception as e:
    print(f"  ✗ Upload failed: {e}")
    sys.exit(1)

print()
print("Test 2: Upload with Excel content type")

# Try with Excel content type
excel_pathname = "reports/test_excel.xlsx"
print(f"  Pathname: {excel_pathname}")

try:
    url = upload_file_to_blob(
        test_content,
        excel_pathname,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    print(f"  ✓ Upload successful!")
    print(f"  URL: {url}")
except Exception as e:
    print(f"  ✗ Upload failed: {e}")
    sys.exit(1)

print()
print("✓ All tests passed! Blob upload is working correctly.")
