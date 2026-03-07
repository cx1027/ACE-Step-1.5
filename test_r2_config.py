#!/usr/bin/env python3
"""Test R2 configuration from .env file.

This script loads R2 credentials from .env and tests the connection
by attempting to list buckets or perform a simple operation.
"""

import os
import sys
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("Error: boto3 is not installed. Install it with: pip install boto3")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv is not installed. Install it with: pip install python-dotenv")
    sys.exit(1)


def test_r2_config():
    """Test R2 configuration by attempting to connect and list buckets."""
    # Load .env file
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        print("Please create a .env file with your R2 configuration.")
        return False

    load_dotenv(env_path)

    # Check required environment variables
    required_vars = [
        "R2_ENDPOINT",
        "R2_ACCESS_KEY",
        "R2_SECRET_KEY",
        "R2_BUCKET_NAME",
        "R2_PUBLIC_URL",
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        return False

    # Display configuration (mask secrets)
    print("R2 Configuration:")
    print(f"  R2_ENDPOINT: {os.environ['R2_ENDPOINT']}")
    print(f"  R2_ACCESS_KEY: {os.environ['R2_ACCESS_KEY'][:8]}...")
    print(f"  R2_SECRET_KEY: {'*' * 20}...")
    print(f"  R2_BUCKET_NAME: {os.environ['R2_BUCKET_NAME']}")
    print(f"  R2_PUBLIC_URL: {os.environ['R2_PUBLIC_URL']}")
    print()

    # Test connection
    try:
        print("Testing R2 connection...")
        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY"],
            aws_secret_access_key=os.environ["R2_SECRET_KEY"],
            region_name="auto",
        )

        # Try to list buckets (this tests authentication)
        print("Attempting to list buckets...")
        response = s3.list_buckets()
        buckets = [b["Name"] for b in response.get("Buckets", [])]
        print(f"✓ Successfully connected! Found {len(buckets)} bucket(s)")

        # Check if the configured bucket exists
        bucket_name = os.environ["R2_BUCKET_NAME"]
        if bucket_name in buckets:
            print(f"✓ Bucket '{bucket_name}' exists")
        else:
            print(f"⚠ Warning: Bucket '{bucket_name}' not found in your account")
            if buckets:
                print(f"  Available buckets: {', '.join(buckets)}")

        # Try to head the bucket (test permissions)
        print(f"Testing access to bucket '{bucket_name}'...")
        try:
            s3.head_bucket(Bucket=bucket_name)
            print(f"✓ Successfully accessed bucket '{bucket_name}'")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                print(f"✗ Bucket '{bucket_name}' does not exist")
                return False
            elif error_code in ("403", "Forbidden"):
                print(f"✗ Access denied to bucket '{bucket_name}' (check permissions)")
                return False
            else:
                print(f"✗ Error accessing bucket: {error_code}")
                return False

        print("\n✓ All R2 configuration tests passed!")
        return True

    except NoCredentialsError:
        print("✗ Error: No credentials found")
        return False
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_msg = e.response.get("Error", {}).get("Message", str(e))

        if error_code in ("InvalidAccessKeyId", "SignatureDoesNotMatch"):
            print(f"✗ Authentication failed: {error_code}")
            print("  Check your R2_ACCESS_KEY and R2_SECRET_KEY")
            return False
        elif error_code == "Unauthorized":
            print(f"✗ Unauthorized: {error_msg}")
            print("  Check your R2 credentials and permissions")
            return False
        else:
            print(f"✗ Error: {error_code} - {error_msg}")
            return False
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = test_r2_config()
    sys.exit(0 if success else 1)
