#!/usr/bin/env python3
"""Test R2 REST API configuration and upload using Cloudflare API Token.

This script tests:
1. Cloudflare API Token authentication
2. File upload to R2 using REST API

Usage:
    uv run python test_r2_rest_api.py
"""

import os
import sys
import tempfile
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests is not installed. Install it with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv is not installed. Install it with: pip install python-dotenv")
    sys.exit(1)

from r2_upload import verify_cloudflare_token, upload_file_to_r2, upload_file_to_r2_direct


def test_r2_rest_api():
    """Test R2 REST API configuration and upload."""
    # Load .env file
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        print("Please create a .env file with your R2 configuration.")
        return False

    load_dotenv(env_path)

    # Check required environment variables
    required_vars = [
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_API_TOKEN",
        "R2_BUCKET_NAME",
        "R2_PUBLIC_URL",
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nNote: For R2 REST API, you need:")
        print("  - CLOUDFLARE_ACCOUNT_ID (your Cloudflare account ID)")
        print("  - CLOUDFLARE_API_TOKEN (your Cloudflare API Token / Bearer token)")
        print("  - R2_BUCKET_NAME (your R2 bucket name)")
        print("  - R2_PUBLIC_URL (public URL prefix for uploaded files)")
        return False

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    api_token = os.environ["CLOUDFLARE_API_TOKEN"]
    bucket_name = os.environ["R2_BUCKET_NAME"]
    public_url = os.environ.get("R2_PUBLIC_URL", "")

    # Display configuration (mask secrets)
    print("R2 REST API Configuration:")
    print(f"  CLOUDFLARE_ACCOUNT_ID: {account_id}")
    print(f"  CLOUDFLARE_API_TOKEN: {'*' * 20}...")
    print(f"  R2_BUCKET_NAME: {bucket_name}")
    print(f"  R2_PUBLIC_URL: {public_url}")
    print()

    # Step 1: Test authentication
    print("=" * 60)
    print("Step 1: Testing Cloudflare API Token authentication")
    print("=" * 60)
    if not verify_cloudflare_token(account_id, api_token):
        print("✗ Authentication failed")
        return False

    print("✓ Authentication successful")
    print()

    # Step 2: Test file upload
    print("=" * 60)
    print("Step 2: Testing file upload to R2")
    print("=" * 60)

    # Create a test file
    test_content = b"This is a test file for R2 upload.\n" * 100
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as f:
        test_file_path = f.name
        f.write(test_content)

    try:
        object_key = f"test/test_upload_{os.urandom(8).hex()}.txt"
        print(f"Uploading test file to: {bucket_name}/{object_key}")

        # Try method 1: Pre-signed URL upload
        print("\nTrying method 1: Pre-signed URL upload...")
        success, uploaded_url = upload_file_to_r2(
            test_file_path,
            bucket_name,
            object_key,
            account_id,
            api_token,
            public_url,
        )

        if success:
            print(f"✓ Upload successful!")
            print(f"  Public URL: {uploaded_url}")
            return True

        # If method 1 fails, try method 2: Direct PUT
        print("\nMethod 1 failed. Trying method 2: Direct PUT upload...")
        success, uploaded_url = upload_file_to_r2_direct(
            test_file_path,
            bucket_name,
            object_key,
            account_id,
            api_token,
            public_url,
        )

        if success:
            print(f"✓ Upload successful!")
            print(f"  Public URL: {uploaded_url}")
            return True
        else:
            print("✗ Both upload methods failed")
            print("\nNote: Cloudflare R2 file uploads may require S3-compatible")
            print("authentication. Consider using R2 Access Key ID + Secret Access Key")
            print("instead of API Token for file uploads.")
            return False

    finally:
        # Clean up test file
        try:
            os.unlink(test_file_path)
        except Exception:
            pass


if __name__ == "__main__":
    success = test_r2_rest_api()
    sys.exit(0 if success else 1)
