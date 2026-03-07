"""Cloudflare R2 upload using REST API with Bearer Token authentication.

This module provides R2 upload functionality using Cloudflare REST API
instead of S3-compatible API, allowing the use of Cloudflare API Tokens
(Bearer tokens) for authentication.
"""

import os
from pathlib import Path
from typing import Optional

import requests
from loguru import logger


def verify_cloudflare_token(account_id: str, api_token: str) -> bool:
    """Verify Cloudflare API token is valid.

    Args:
        account_id: Cloudflare Account ID.
        api_token: Cloudflare API Token (Bearer token).

    Returns:
        True if token is valid, False otherwise.
    """
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/tokens/verify"
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            logger.info("✓ Cloudflare API token verified successfully")
            return True
        else:
            errors = data.get("errors", [])
            if errors:
                logger.error(f"Token verification failed: {errors[0].get('message', 'Unknown error')}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to verify token: {e}")
        return False


def upload_file_to_r2(
    file_path: str | Path,
    bucket_name: str,
    object_key: str,
    account_id: str,
    api_token: str,
    public_url_prefix: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Upload a file to Cloudflare R2 using REST API.

    This function uses Cloudflare's REST API to upload files. It first
    creates a pre-signed URL using the API token, then uploads the file
    to that URL.

    Args:
        file_path: Path to the local file to upload.
        bucket_name: R2 bucket name.
        object_key: Object key (path) in the bucket.
        account_id: Cloudflare Account ID.
        api_token: Cloudflare API Token (Bearer token).
        public_url_prefix: Optional public URL prefix for the uploaded file.

    Returns:
        Tuple of (success: bool, public_url: Optional[str]).
        If successful, returns (True, public_url). Otherwise (False, None).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False, None

    # Step 1: Create a pre-signed URL for upload
    # Cloudflare R2 REST API endpoint for creating upload URLs
    create_url_endpoint = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/r2/buckets/{bucket_name}/objects/{object_key}/upload"
    )

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    try:
        # Request a pre-signed upload URL
        logger.info(f"Requesting upload URL for {bucket_name}/{object_key}")
        response = requests.post(create_url_endpoint, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            errors = data.get("errors", [])
            error_msg = errors[0].get("message", "Unknown error") if errors else "Unknown error"
            logger.error(f"Failed to create upload URL: {error_msg}")
            return False, None

        upload_url = data.get("result", {}).get("upload_url")
        if not upload_url:
            logger.error("No upload URL returned from API")
            return False, None

        # Step 2: Upload the file using PUT request
        logger.info(f"Uploading file {file_path} to R2")
        with file_path.open("rb") as f:
            file_content = f.read()

        upload_headers = {
            "Content-Type": "audio/mpeg",  # Default for MP3 files
        }

        upload_response = requests.put(upload_url, data=file_content, headers=upload_headers, timeout=60)
        upload_response.raise_for_status()

        # Step 3: Construct public URL
        if public_url_prefix:
            public_url = f"{public_url_prefix.rstrip('/')}/{object_key}"
        else:
            # Fallback: construct URL from bucket name
            public_url = f"https://pub-{account_id[:8]}.r2.dev/{object_key}"

        logger.info(f"✓ Successfully uploaded to R2: {public_url}")
        return True, public_url

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to upload file to R2: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                logger.error(f"API response: {error_data}")
            except Exception:
                logger.error(f"Response text: {e.response.text}")
        return False, None


def upload_file_to_r2_direct(
    file_path: str | Path,
    bucket_name: str,
    object_key: str,
    account_id: str,
    api_token: str,
    public_url_prefix: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Upload a file to Cloudflare R2 using direct REST API PUT.

    This is an alternative implementation that attempts to upload directly
    to R2 using the REST API endpoint. Note: This may not work if R2
    requires S3-compatible authentication for object uploads.

    Args:
        file_path: Path to the local file to upload.
        bucket_name: R2 bucket name.
        object_key: Object key (path) in the bucket.
        account_id: Cloudflare Account ID.
        api_token: Cloudflare API Token (Bearer token).
        public_url_prefix: Optional public URL prefix for the uploaded file.

    Returns:
        Tuple of (success: bool, public_url: Optional[str]).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False, None

    # Try direct PUT to R2 REST API endpoint
    upload_endpoint = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/r2/buckets/{bucket_name}/objects/{object_key}"
    )

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "audio/mpeg",
    }

    try:
        logger.info(f"Uploading file {file_path} directly to R2")
        with file_path.open("rb") as f:
            file_content = f.read()

        response = requests.put(upload_endpoint, data=file_content, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            errors = data.get("errors", [])
            error_msg = errors[0].get("message", "Unknown error") if errors else "Unknown error"
            logger.error(f"Upload failed: {error_msg}")
            return False, None

        # Construct public URL
        if public_url_prefix:
            public_url = f"{public_url_prefix.rstrip('/')}/{object_key}"
        else:
            public_url = f"https://pub-{account_id[:8]}.r2.dev/{object_key}"

        logger.info(f"✓ Successfully uploaded to R2: {public_url}")
        return True, public_url

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to upload file to R2: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                logger.error(f"API response: {error_data}")
            except Exception:
                logger.error(f"Response text: {e.response.text}")
        return False, None
