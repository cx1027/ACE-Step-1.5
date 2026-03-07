#!/usr/bin/env python3
"""Get R2 Access Key ID and Secret Access Key using Cloudflare API Token.

This script uses a Cloudflare API Token to list or create R2 API Tokens
(which provide Access Key ID and Secret Access Key for S3-compatible API).
"""

import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests is not installed. Install it with: pip install requests")
    sys.exit(1)


def get_r2_tokens(account_id: str, api_token: str) -> list[dict]:
    """List all R2 API Tokens for the account.
    
    Args:
        account_id: Cloudflare Account ID
        api_token: Cloudflare API Token (Bearer token)
        
    Returns:
        List of R2 API Token objects
    """
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/r2/tokens"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            return data.get("result", [])
        else:
            print(f"Error: {data.get('errors', [{}])[0].get('message', 'Unknown error')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching R2 tokens: {e}")
        return []


def create_r2_token(
    account_id: str,
    api_token: str,
    token_name: str = "ACE-Step-R2-Token",
    permissions: dict = None,
) -> dict | None:
    """Create a new R2 API Token.
    
    Args:
        account_id: Cloudflare Account ID
        api_token: Cloudflare API Token (Bearer token)
        token_name: Name for the new R2 API Token
        permissions: Permissions dict (default: read/write all buckets)
        
    Returns:
        Token object with access_key_id and secret_access_key, or None on error
    """
    if permissions is None:
        permissions = {
            "permissions": ["Object Read", "Object Write"],
            "resources": {"buckets": []},  # Empty list means all buckets
        }
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/r2/tokens"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "name": token_name,
        **permissions,
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            result = data.get("result", {})
            return {
                "access_key_id": result.get("access_key_id"),
                "secret_access_key": result.get("secret_access_key"),
                "name": result.get("name"),
                "id": result.get("id"),
            }
        else:
            errors = data.get("errors", [])
            if errors:
                print(f"Error creating R2 token: {errors[0].get('message', 'Unknown error')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error creating R2 token: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response text: {e.response.text}")
        return None


def main():
    """Main function to get or create R2 credentials."""
    # Try to get account_id and api_token from environment or .env
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    
    # Try loading from .env file
    if not account_id or not api_token:
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
                api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN")
        except ImportError:
            pass
    
    # If still not found, try to extract from R2_ENDPOINT
    if not account_id:
        r2_endpoint = os.environ.get("R2_ENDPOINT", "")
        if ".r2.cloudflarestorage.com" in r2_endpoint:
            # Extract account ID from endpoint: https://<account_id>.r2.cloudflarestorage.com
            account_id = r2_endpoint.split("//")[1].split(".")[0]
            print(f"Extracted Account ID from R2_ENDPOINT: {account_id}")
    
    # Prompt for missing values
    if not account_id:
        account_id = input("Enter Cloudflare Account ID: ").strip()
    
    if not api_token:
        api_token = input("Enter Cloudflare API Token: ").strip()
    
    if not account_id or not api_token:
        print("Error: Account ID and API Token are required")
        sys.exit(1)
    
    print(f"\nAccount ID: {account_id}")
    print(f"API Token: {api_token[:20]}...")
    print()
    
    # List existing R2 tokens
    print("Fetching existing R2 API Tokens...")
    tokens = get_r2_tokens(account_id, api_token)
    
    if tokens:
        print(f"\nFound {len(tokens)} existing R2 API Token(s):")
        for i, token in enumerate(tokens, 1):
            print(f"\n{i}. {token.get('name', 'Unnamed')}")
            print(f"   ID: {token.get('id')}")
            print(f"   Access Key ID: {token.get('access_key_id', 'N/A')}")
            print(f"   Created: {token.get('created_at', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("Note: Secret Access Key is only shown when token is created.")
        print("If you need a new token, we can create one.")
        print("=" * 60)
        
        choice = input("\nCreate a new R2 API Token? (y/n): ").strip().lower()
        if choice != "y":
            print("\nTo use an existing token, you need:")
            print("1. Access Key ID (shown above)")
            print("2. Secret Access Key (only available when token was created)")
            print("\nIf you don't have the Secret Access Key, you'll need to:")
            print("- Create a new token, or")
            print("- Regenerate the existing token (this will invalidate the old one)")
            sys.exit(0)
    else:
        print("No existing R2 API Tokens found.")
        choice = input("Create a new R2 API Token? (y/n): ").strip().lower()
        if choice != "y":
            sys.exit(0)
    
    # Create new token
    print("\nCreating new R2 API Token...")
    token_name = input("Enter token name (default: ACE-Step-R2-Token): ").strip()
    if not token_name:
        token_name = "ACE-Step-R2-Token"
    
    new_token = create_r2_token(account_id, api_token, token_name)
    
    if new_token:
        print("\n" + "=" * 60)
        print("✓ Successfully created R2 API Token!")
        print("=" * 60)
        print(f"\nToken Name: {new_token['name']}")
        print(f"Access Key ID: {new_token['access_key_id']}")
        print(f"Secret Access Key: {new_token['secret_access_key']}")
        print("\n⚠️  IMPORTANT: Save the Secret Access Key now!")
        print("   It will not be shown again.")
        print("\n" + "=" * 60)
        
        # Generate .env configuration
        r2_endpoint = os.environ.get("R2_ENDPOINT") or f"https://{account_id}.r2.cloudflarestorage.com"
        bucket_name = os.environ.get("R2_BUCKET_NAME") or "music-outputs"
        public_url = os.environ.get("R2_PUBLIC_URL") or ""
        
        print("\nAdd these to your .env file:")
        print("-" * 60)
        print(f"R2_ENDPOINT={r2_endpoint}")
        print(f"R2_ACCESS_KEY={new_token['access_key_id']}")
        print(f"R2_SECRET_KEY={new_token['secret_access_key']}")
        print(f"R2_BUCKET_NAME={bucket_name}")
        if public_url:
            print(f"R2_PUBLIC_URL={public_url}")
        print("-" * 60)
        
        # Optionally update .env file
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            update = input("\nUpdate .env file automatically? (y/n): ").strip().lower()
            if update == "y":
                update_env_file(
                    env_path,
                    r2_endpoint,
                    new_token["access_key_id"],
                    new_token["secret_access_key"],
                    bucket_name,
                    public_url,
                )
                print("✓ .env file updated!")
    else:
        print("\n✗ Failed to create R2 API Token")
        print("\nTroubleshooting:")
        print("1. Verify your Cloudflare API Token has R2 permissions")
        print("2. Check that the Account ID is correct")
        print("3. Ensure the API Token is not expired")
        sys.exit(1)


def update_env_file(
    env_path: Path,
    endpoint: str,
    access_key: str,
    secret_key: str,
    bucket_name: str,
    public_url: str = "",
):
    """Update .env file with R2 credentials."""
    # Read existing .env
    lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    # Update or add R2 variables
    r2_vars = {
        "R2_ENDPOINT": endpoint,
        "R2_ACCESS_KEY": access_key,
        "R2_SECRET_KEY": secret_key,
        "R2_BUCKET_NAME": bucket_name,
    }
    if public_url:
        r2_vars["R2_PUBLIC_URL"] = public_url
    
    updated = {var: False for var in r2_vars}
    
    # Update existing lines
    for i, line in enumerate(lines):
        for var, value in r2_vars.items():
            if line.strip().startswith(f"{var}="):
                lines[i] = f"{var}={value}\n"
                updated[var] = True
                break
    
    # Add missing variables
    for var, value in r2_vars.items():
        if not updated[var]:
            lines.append(f"{var}={value}\n")
    
    # Write back
    with open(env_path, "w") as f:
        f.writelines(lines)


if __name__ == "__main__":
    main()
