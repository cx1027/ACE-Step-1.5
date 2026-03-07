#!/usr/bin/env python3
"""Quick test for S3-compatible R2 authentication."""

import os
import sys
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("Error: boto3 is not installed.")
    print("Please install it with: pip install boto3")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv is not installed.")
    print("Please install it with: pip install python-dotenv")
    sys.exit(1)

# Load .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded .env from {env_path}")
else:
    print(f"⚠ .env file not found at {env_path}")
    print("  Using environment variables from system")

# Check required variables
required_vars = {
    "R2_ENDPOINT": os.environ.get("R2_ENDPOINT"),
    "R2_ACCESS_KEY": os.environ.get("R2_ACCESS_KEY"),
    "R2_SECRET_KEY": os.environ.get("R2_SECRET_KEY"),
    "R2_BUCKET_NAME": os.environ.get("R2_BUCKET_NAME"),
    "R2_PUBLIC_URL": os.environ.get("R2_PUBLIC_URL"),
}

print("\n" + "=" * 60)
print("Checking S3-Compatible R2 Configuration")
print("=" * 60)

missing = []
for var, value in required_vars.items():
    if value:
        if "SECRET" in var or "KEY" in var:
            display_value = f"{value[:8]}..." if len(value) > 8 else "***"
        else:
            display_value = value
        print(f"✓ {var}: {display_value}")
    else:
        print(f"✗ {var}: NOT SET")
        missing.append(var)

if missing:
    print(f"\n✗ Missing required variables: {', '.join(missing)}")
    print("\nPlease add these to your .env file:")
    for var in missing:
        print(f"  {var}=your-value-here")
    sys.exit(1)

print("\n" + "=" * 60)
print("Testing S3 Authentication")
print("=" * 60)

try:
    s3 = boto3.client(
        "s3",
        endpoint_url=required_vars["R2_ENDPOINT"],
        aws_access_key_id=required_vars["R2_ACCESS_KEY"],
        aws_secret_access_key=required_vars["R2_SECRET_KEY"],
        region_name="auto",
    )

    print("Attempting to list buckets (tests authentication)...")
    response = s3.list_buckets()
    buckets = [b["Name"] for b in response.get("Buckets", [])]
    print(f"✓ Authentication successful!")
    print(f"✓ Found {len(buckets)} bucket(s)")

    # Check if configured bucket exists
    bucket_name = required_vars["R2_BUCKET_NAME"]
    if bucket_name in buckets:
        print(f"✓ Bucket '{bucket_name}' exists in your account")
    else:
        print(f"⚠ Bucket '{bucket_name}' not found")
        if buckets:
            print(f"  Available buckets: {', '.join(buckets)}")

    # Test bucket access
    print(f"\nTesting access to bucket '{bucket_name}'...")
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"✓ Successfully accessed bucket '{bucket_name}'")
        print("\n" + "=" * 60)
        print("✓ All authentication tests passed!")
        print("=" * 60)
        sys.exit(0)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            print(f"✗ Bucket '{bucket_name}' does not exist")
        elif error_code in ("403", "Forbidden"):
            print(f"✗ Access denied to bucket '{bucket_name}'")
            print("  Check your R2_ACCESS_KEY and R2_SECRET_KEY permissions")
        else:
            print(f"✗ Error accessing bucket: {error_code}")
        sys.exit(1)

except NoCredentialsError:
    print("✗ No credentials found")
    sys.exit(1)
except ClientError as e:
    error_code = e.response.get("Error", {}).get("Code", "")
    error_msg = e.response.get("Error", {}).get("Message", str(e))
    full_error = str(e)

    print(f"\nDetailed error information:")
    print(f"  Error Code: {error_code}")
    print(f"  Error Message: {error_msg}")
    if e.response:
        print(f"  HTTP Status: {e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'N/A')}")

    if error_code in ("InvalidAccessKeyId", "SignatureDoesNotMatch"):
        print(f"\n✗ Authentication failed: {error_code}")
        print("  Please check:")
        print("    - R2_ENDPOINT is correct (format: https://account-id.r2.cloudflarestorage.com)")
        print("    - R2_ACCESS_KEY is correct")
        print("    - R2_SECRET_KEY is correct")
    elif error_code in ("AccessDenied", "Unauthorized", "Forbidden"):
        print(f"\n✗ Access Denied: {error_msg}")
        print("\n  Possible causes:")
        print("    1. R2 API Token permissions are insufficient")
        print("       - Go to Cloudflare Dashboard → R2 → Manage R2 API Tokens")
        print("       - Ensure the token has 'Object Read & Write' permissions")
        print("    2. R2_ACCESS_KEY or R2_SECRET_KEY may be incorrect")
        print("       - Verify the keys match the API Token you created")
        print("    3. The API Token may not have access to the account")
        print("       - Check that the token is for the correct Cloudflare account")
    else:
        print(f"\n✗ Error: {error_code} - {error_msg}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
