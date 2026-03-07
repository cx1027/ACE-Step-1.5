#!/usr/bin/env python3
"""Test both R2 authentication methods to see which credentials are configured.

This script tests both S3-compatible API and Cloudflare REST API methods
to help diagnose which authentication method is working.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


def test_s3_compatible_method():
    """Test S3-compatible API authentication."""
    print("=" * 60)
    print("Testing Method 1: S3-Compatible API")
    print("=" * 60)
    
    if not BOTO3_AVAILABLE:
        print("⚠ boto3 not installed - skipping S3-compatible test")
        return False
    
    required_vars = ["R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        print(f"✗ Missing variables: {', '.join(missing)}")
        return False
    
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY"],
            aws_secret_access_key=os.environ["R2_SECRET_KEY"],
            region_name="auto",
        )
        
        response = s3.list_buckets()
        buckets = [b["Name"] for b in response.get("Buckets", [])]
        print(f"✓ S3-Compatible API: SUCCESS")
        print(f"  Found {len(buckets)} bucket(s): {', '.join(buckets)}")
        return True
    except NoCredentialsError:
        print("✗ S3-Compatible API: No credentials")
        return False
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        print(f"✗ S3-Compatible API: {error_code}")
        return False
    except Exception as e:
        print(f"✗ S3-Compatible API: {type(e).__name__}: {e}")
        return False


def test_rest_api_method():
    """Test Cloudflare REST API authentication."""
    print("\n" + "=" * 60)
    print("Testing Method 2: Cloudflare REST API")
    print("=" * 60)
    
    required_vars = ["CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        print(f"✗ Missing variables: {', '.join(missing)}")
        return False
    
    api_token = os.environ["CLOUDFLARE_API_TOKEN"]
    url = "https://api.cloudflare.com/client/v4/user/tokens/verify"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            
            if data.get("success"):
                print("✓ Cloudflare REST API: SUCCESS")
                result = data.get("result", {})
                scopes = result.get("scopes", [])
                if scopes:
                    print(f"  Token scopes: {', '.join(scopes)}")
                return True
            else:
                errors = data.get("errors", [])
                if errors:
                    error = errors[0]
                    print(f"✗ Cloudflare REST API: {error.get('message', 'Unknown error')}")
                return False
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            error_data = json.loads(error_body)
            errors = error_data.get("errors", [])
            if errors:
                print(f"✗ Cloudflare REST API: {errors[0].get('message', 'Unknown error')}")
            else:
                print(f"✗ Cloudflare REST API: HTTP {e.code}")
        except json.JSONDecodeError:
            print(f"✗ Cloudflare REST API: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"✗ Cloudflare REST API: {type(e).__name__}: {e}")
        return False


def main():
    """Main function."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        sys.exit(1)
    
    if DOTENV_AVAILABLE:
        load_dotenv(env_path)
    else:
        # Fallback: manual parsing
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value
    
    print("R2 Authentication Methods Test")
    print("=" * 60)
    print()
    
    method1_works = test_s3_compatible_method()
    method2_works = test_rest_api_method()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Method 1 (S3-Compatible): {'✓ WORKING' if method1_works else '✗ NOT WORKING'}")
    print(f"Method 2 (REST API):      {'✓ WORKING' if method2_works else '✗ NOT WORKING'}")
    print()
    
    if method1_works and not method2_works:
        print("Recommendation: Use Method 1 (S3-Compatible) for your operations.")
        print("  - Your S3 credentials are valid and working")
        print("  - Use test_r2_config.py for testing")
    elif method2_works and not method1_works:
        print("Recommendation: Use Method 2 (REST API) for your operations.")
        print("  - Your Cloudflare API token is valid and working")
        print("  - Use test_r2_simple.py for testing")
    elif method1_works and method2_works:
        print("Both methods work! You can use either one.")
    else:
        print("Neither method is working. Check your .env file configuration.")
    
    sys.exit(0 if (method1_works or method2_works) else 1)


if __name__ == "__main__":
    main()
