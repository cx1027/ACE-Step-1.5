#!/usr/bin/env python3
"""Test local music generation and R2 upload using .env configuration.

This script tests the complete flow:
1. Load .env configuration
2. Generate music using local handler
3. Upload generated music.mp3 to R2
4. Verify upload success and display public URL

Usage:
    uv run python test_local_r2_upload.py --prompt "a beautiful melody" --duration 30
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

# Load .env before importing handler
try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv is not installed. Install it with: pip install python-dotenv")
    sys.exit(1)

project_root = Path(__file__).resolve().parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(str(env_path), override=False)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f".env file not found at {env_path}")
    logger.info("Please create a .env file with your R2 configuration (see runpod.env.example)")


def _check_r2_config() -> tuple[bool, str]:
    """Check if R2 configuration is available.

    Returns:
        Tuple of (is_configured: bool, method: str).
        method can be "rest_api", "s3", or "none".
    """
    # Method 1: REST API (Bearer Token)
    rest_api_keys = [
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_API_TOKEN",
        "R2_BUCKET_NAME",
        "R2_PUBLIC_URL",
    ]
    has_rest_api = all(os.environ.get(key) for key in rest_api_keys)

    # Method 2: S3-Compatible API
    s3_keys = [
        "R2_ENDPOINT",
        "R2_ACCESS_KEY",
        "R2_SECRET_KEY",
        "R2_BUCKET_NAME",
        "R2_PUBLIC_URL",
    ]
    has_s3_api = all(os.environ.get(key) for key in s3_keys)

    if has_rest_api:
        return True, "rest_api"
    elif has_s3_api:
        return True, "s3"
    else:
        return False, "none"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test local music generation and R2 upload using .env configuration."
    )
    parser.add_argument("--prompt", type=str, default="a beautiful melody", help="Music generation prompt")
    parser.add_argument("--duration", type=float, default=30.0, help="Music duration in seconds")
    parser.add_argument("--mode", type=str, default="", help="Optional: simple/custom")
    parser.add_argument("--lyrics", type=str, default="", help="Optional: lyrics (required for mode=custom)")
    parser.add_argument("--bpm", type=int, default=0, help="Optional: BPM")
    parser.add_argument("--key", type=str, default="", help="Optional: key")
    parser.add_argument("--inference-steps", type=int, default=8, help="Inference steps")
    parser.add_argument("--guidance-scale", type=float, default=7.0, help="Guidance scale")
    parser.add_argument("--seed", type=int, default=-1, help="Random seed (-1 for random)")
    parser.add_argument("--thinking", action=argparse.BooleanOptionalAction, default=True, help="Enable CoT thinking")
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip music generation, only test R2 upload with existing file",
    )
    parser.add_argument(
        "--test-file",
        type=str,
        default="",
        help="Path to existing MP3 file to upload (for testing upload only)",
    )
    return parser.parse_args()


async def _test_r2_upload_only(test_file_path: str) -> bool:
    """Test R2 upload with an existing file.

    Args:
        test_file_path: Path to the file to upload.

    Returns:
        True if upload successful, False otherwise.
    """
    from runpod_handler import generate_music_job

    # Create a dummy job that just uploads the file
    job = {
        "id": str(uuid.uuid4()),
        "input": {
            "prompt": "test upload",
            "duration": 1.0,
            "skip_generation": True,  # Custom flag to skip generation
        },
    }

    # For upload-only test, we need to manually upload
    # Let's use the r2_upload module directly
    try:
        from r2_upload import upload_file_to_r2, upload_file_to_r2_direct

        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
        bucket_name = os.environ.get("R2_BUCKET_NAME")
        public_url = os.environ.get("R2_PUBLIC_URL", "")

        if not all([account_id, api_token, bucket_name]):
            logger.error("Missing R2 REST API configuration in .env")
            return False

        object_key = f"test/test_upload_{uuid.uuid4()}.mp3"
        logger.info(f"Uploading {test_file_path} to R2: {bucket_name}/{object_key}")

        # Try method 1: Pre-signed URL
        success, uploaded_url = upload_file_to_r2(
            test_file_path,
            bucket_name,
            object_key,
            account_id,
            api_token,
            public_url,
        )

        if not success:
            # Try method 2: Direct PUT
            logger.info("Method 1 failed, trying direct PUT...")
            success, uploaded_url = upload_file_to_r2_direct(
                test_file_path,
                bucket_name,
                object_key,
                account_id,
                api_token,
                public_url,
            )

        if success:
            logger.info(f"✓ Upload successful!")
            logger.info(f"  Public URL: {uploaded_url}")
            return True
        else:
            logger.error("✗ Upload failed")
            return False

    except ImportError:
        logger.error("r2_upload module not available")
        return False
    except Exception as e:
        logger.exception(f"Upload error: {e}")
        return False


async def main() -> None:
    """Main test function."""
    args = _parse_args()

    # Check R2 configuration
    has_r2, method = _check_r2_config()
    if not has_r2:
        logger.error("R2 configuration not found in .env file")
        logger.info("Please configure R2 credentials in .env file (see runpod.env.example)")
        sys.exit(1)

    logger.info(f"R2 configuration found: method={method}")
    logger.info(f"  CLOUDFLARE_ACCOUNT_ID: {os.environ.get('CLOUDFLARE_ACCOUNT_ID', 'N/A')}")
    logger.info(f"  R2_BUCKET_NAME: {os.environ.get('R2_BUCKET_NAME', 'N/A')}")
    logger.info(f"  R2_PUBLIC_URL: {os.environ.get('R2_PUBLIC_URL', 'N/A')}")

    # Ensure R2 upload is enabled
    if os.environ.get("DISABLE_R2_UPLOAD", "").lower() in {"1", "true", "yes"}:
        logger.warning("DISABLE_R2_UPLOAD is set, but we'll override it for this test")
        os.environ["DISABLE_R2_UPLOAD"] = "0"

    # Test upload only mode
    if args.skip_generation or args.test_file:
        if args.test_file:
            test_file = Path(args.test_file)
            if not test_file.exists():
                logger.error(f"Test file not found: {test_file}")
                sys.exit(1)
            logger.info(f"Testing R2 upload with existing file: {test_file}")
            success = await _test_r2_upload_only(str(test_file))
            sys.exit(0 if success else 1)
        else:
            logger.error("--skip-generation requires --test-file")
            sys.exit(1)

    # Build job from arguments
    job_input: dict[str, Any] = {
        "prompt": args.prompt,
        "duration": args.duration,
        "inference_steps": args.inference_steps,
        "guidance_scale": args.guidance_scale,
        "seed": args.seed,
        "thinking": args.thinking,
    }

    if args.mode:
        job_input["mode"] = args.mode
    if args.lyrics:
        job_input["lyrics"] = args.lyrics
    if args.bpm:
        job_input["bpm"] = args.bpm
    if args.key:
        job_input["key"] = args.key

    job = {
        "id": os.environ.get("JOB_ID", str(uuid.uuid4())),
        "input": job_input,
    }

    logger.info("=" * 60)
    logger.info("Starting music generation and R2 upload test")
    logger.info("=" * 60)
    logger.info(f"Job ID: {job['id']}")
    logger.info(f"Prompt: {args.prompt}")
    logger.info(f"Duration: {args.duration}s")
    logger.info(f"Mode: {args.mode or 'default'}")
    logger.info("")

    # Import handler after .env is loaded
    from runpod_handler import generate_music_job

    # Run the job
    try:
        result = await generate_music_job(job)
        print("\n" + "=" * 60)
        print("Result:")
        print("=" * 60)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print()

        if result.get("status") == "success":
            output_url = result.get("output_url", "")
            logger.info("✓ Music generation and upload successful!")
            logger.info(f"  Output URL: {output_url}")

            # Verify it's an R2 URL (not local path)
            if output_url.startswith("http"):
                logger.info("✓ File uploaded to R2 (public URL)")
            else:
                logger.warning("⚠ File not uploaded to R2 (local path returned)")
                logger.warning("  This may indicate R2 upload was disabled or failed")

            sys.exit(0)
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"✗ Music generation failed: {error}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"Error during test: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
