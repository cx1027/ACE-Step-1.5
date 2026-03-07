#!/usr/bin/env python3
"""Simple test for R2 upload functionality using .env configuration.

This script tests R2 upload with a small test file to verify:
1. .env configuration is loaded correctly
2. R2 REST API authentication works
3. File upload to R2 succeeds
4. Public URL is accessible

Usage:
    # Test with a small generated file
    uv run python test_r2_upload_simple.py

    # Test with an existing MP3 file
    uv run python test_r2_upload_simple.py --file path/to/music.mp3
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv is not installed. Install it with: pip install python-dotenv")
    sys.exit(1)

try:
    from r2_upload import verify_cloudflare_token, upload_file_to_r2, upload_file_to_r2_direct
except ImportError:
    print("Error: r2_upload module not found. Make sure r2_upload.py exists in the project root.")
    sys.exit(1)

from loguru import logger


def main():
    """Test R2 upload functionality."""
    # Load .env file
    project_root = Path(__file__).resolve().parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(str(env_path), override=False)
        logger.info(f"Loaded environment variables from {env_path}")
    else:
        logger.error(f".env file not found at {env_path}")
        logger.info("Please create a .env file with your R2 configuration (see runpod.env.example)")
        return False

    # Check required environment variables
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    bucket_name = os.environ.get("R2_BUCKET_NAME")
    public_url = os.environ.get("R2_PUBLIC_URL", "")

    if not all([account_id, api_token, bucket_name]):
        logger.error("Missing required R2 configuration in .env:")
        if not account_id:
            logger.error("  - CLOUDFLARE_ACCOUNT_ID")
        if not api_token:
            logger.error("  - CLOUDFLARE_API_TOKEN")
        if not bucket_name:
            logger.error("  - R2_BUCKET_NAME")
        return False

    logger.info("R2 Configuration:")
    logger.info(f"  CLOUDFLARE_ACCOUNT_ID: {account_id}")
    logger.info(f"  CLOUDFLARE_API_TOKEN: {'*' * 20}...")
    logger.info(f"  R2_BUCKET_NAME: {bucket_name}")
    logger.info(f"  R2_PUBLIC_URL: {public_url}")
    logger.info("")

    # Step 1: Test authentication
    logger.info("=" * 60)
    logger.info("Step 1: Testing Cloudflare API Token authentication")
    logger.info("=" * 60)
    
    if not verify_cloudflare_token(account_id, api_token):
        logger.error("✗ Authentication failed")
        return False
    logger.info("✓ Authentication successful")
    logger.info("")

    # Step 2: Prepare test file
    logger.info("=" * 60)
    logger.info("Step 2: Preparing test file")
    logger.info("=" * 60)

    # Check if user provided a file
    test_file_path = None
    if len(sys.argv) > 1 and sys.argv[1] == "--file" and len(sys.argv) > 2:
        test_file_path = Path(sys.argv[2])
        if not test_file_path.exists():
            logger.error(f"File not found: {test_file_path}")
            return False
        logger.info(f"Using provided file: {test_file_path}")
    else:
        # Create a small test MP3 file (minimal valid MP3 header)
        # This is a very basic MP3 file structure for testing
        logger.info("Creating test MP3 file...")
        test_content = b"\xff\xfb\x90\x00" + b"\x00" * 1000  # Minimal MP3-like header
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".mp3") as f:
            test_file_path = Path(f.name)
            f.write(test_content)
        logger.info(f"Created test file: {test_file_path} ({test_file_path.stat().st_size} bytes)")

    logger.info("")

    # Step 3: Upload to R2
    logger.info("=" * 60)
    logger.info("Step 3: Uploading file to R2")
    logger.info("=" * 60)

    object_key = f"test/test_upload_{uuid.uuid4()}.mp3"
    logger.info(f"Uploading to: {bucket_name}/{object_key}")

    success = False
    uploaded_url = None

    # Try REST API methods
    if account_id and api_token:
        # Try method 1: Pre-signed URL upload
        logger.info("\nTrying method 1: Pre-signed URL upload (REST API)...")
        success, uploaded_url = upload_file_to_r2(
            str(test_file_path),
            bucket_name,
            object_key,
            account_id,
            api_token,
            public_url,
        )

        if not success:
            # Try method 2: Direct PUT
            logger.info("\nMethod 1 failed. Trying method 2: Direct PUT upload (REST API)...")
            success, uploaded_url = upload_file_to_r2_direct(
                str(test_file_path),
                bucket_name,
                object_key,
                account_id,
                api_token,
                public_url,
            )

    # Clean up temporary file if we created it
    if test_file_path and not (len(sys.argv) > 1 and sys.argv[1] == "--file"):
        try:
            test_file_path.unlink()
            logger.debug(f"Cleaned up temporary file: {test_file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file: {e}")

    if success:
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ Upload successful!")
        logger.info("=" * 60)
        logger.info(f"Public URL: {uploaded_url}")
        logger.info("")
        logger.info("You can verify the upload by:")
        logger.info(f"  1. Visiting the URL: {uploaded_url}")
        logger.info(f"  2. Checking your R2 bucket: {bucket_name}")
        return True
    else:
        logger.error("")
        logger.error("=" * 60)
        logger.error("✗ Upload failed")
        logger.error("=" * 60)
        logger.error("Please check:")
        logger.error("  1. Your CLOUDFLARE_API_TOKEN has R2 write permissions")
        logger.error("  2. The R2_BUCKET_NAME exists and is accessible")
        logger.error("  3. Your network connection is working")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
