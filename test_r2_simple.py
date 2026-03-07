#!/usr/bin/env python3
"""Simple R2 REST API test using only Python standard library.

This script tests Cloudflare API Token authentication without requiring
external dependencies.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_env_file(env_path: Path) -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    if not env_path.exists():
        return env_vars

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Parse KEY=VALUE
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                env_vars[key] = value
    return env_vars


def verify_cloudflare_token(api_token: str) -> bool:
    """Verify Cloudflare API token is valid using standard library only."""
    url = "https://api.cloudflare.com/client/v4/user/tokens/verify"
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

            if data.get("success"):
                print("✓ Cloudflare API token verified successfully")
                return True
            else:
                errors = data.get("errors", [])
                if errors:
                    print(f"✗ Token verification failed: {errors[0].get('message', 'Unknown error')}")
                return False
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            error_data = json.loads(error_body)
            errors = error_data.get("errors", [])
            if errors:
                print(f"✗ Token verification failed: {errors[0].get('message', 'Unknown error')}")
            else:
                print(f"✗ HTTP {e.code}: {error_body}")
        except json.JSONDecodeError:
            print(f"✗ HTTP {e.code}: {error_body}")
        return False
    except Exception as e:
        print(f"✗ Failed to verify token: {type(e).__name__}: {e}")
        return False


def test_r2_config():
    """Test R2 REST API configuration."""
    # Load .env file
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        return False

    env_vars = load_env_file(env_path)
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value

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

    # Test authentication
    print("=" * 60)
    print("Testing Cloudflare API Token authentication")
    print("=" * 60)
    if not verify_cloudflare_token(api_token):
        print("\n✗ Authentication failed")
        print("\nTroubleshooting:")
        print("1. Check that CLOUDFLARE_API_TOKEN is correct")
        print("2. Verify the token has R2 permissions")
        print("3. Make sure you created an Account API Token (not User API Token)")
        return False

    print("\n✓ All configuration tests passed!")
    print("\nNext steps:")
    print("1. Run 'python3 test_r2_rest_api.py' to test file upload")
    print("2. Or run 'python3 test_local_r2_upload.py' for full integration test")
    return True


if __name__ == "__main__":
    success = test_r2_config()
    sys.exit(0 if success else 1)
