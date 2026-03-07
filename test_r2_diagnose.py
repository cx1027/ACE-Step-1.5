#!/usr/bin/env python3
"""Diagnostic script for R2 API Token issues.

This script provides detailed diagnostics for Cloudflare API Token problems.
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
                env_vars[key] = value
    return env_vars


def diagnose_token(api_token: str) -> None:
    """Diagnose API token issues."""
    print("=" * 60)
    print("Token Diagnostics")
    print("=" * 60)
    
    # Check token format
    print(f"\n1. Token length: {len(api_token)} characters")
    print(f"2. Token starts with: {api_token[:10]}...")
    print(f"3. Token ends with: ...{api_token[-10:]}")
    
    # Check for common issues
    if api_token.startswith("Bearer "):
        print("⚠ Warning: Token starts with 'Bearer ' - remove it!")
        print("   Token should NOT include 'Bearer ' prefix")
    if " " in api_token:
        print("⚠ Warning: Token contains spaces - check for extra characters")
    if len(api_token) < 40:
        print("⚠ Warning: Token seems too short (expected ~40+ characters)")
    if len(api_token) > 200:
        print("⚠ Warning: Token seems too long (expected ~40-200 characters)")
    
    # Test token verification
    print("\n4. Testing token verification...")
    url = "https://api.cloudflare.com/client/v4/user/tokens/verify"
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            
            if data.get("success"):
                print("✓ Token is valid!")
                result = data.get("result", {})
                print(f"   Token ID: {result.get('id', 'N/A')}")
                print(f"   Status: {result.get('status', 'N/A')}")
                
                # Check permissions
                scopes = result.get("scopes", [])
                if scopes:
                    print(f"   Scopes: {', '.join(scopes)}")
                    has_r2 = any("r2" in scope.lower() or "r2:" in scope.lower() for scope in scopes)
                    if not has_r2:
                        print("⚠ Warning: Token may not have R2 permissions")
                        print("   Look for scopes containing 'r2' or 'R2'")
                else:
                    print("⚠ Warning: No scopes found in token response")
            else:
                errors = data.get("errors", [])
                if errors:
                    error = errors[0]
                    print(f"✗ Token verification failed:")
                    print(f"   Code: {error.get('code', 'N/A')}")
                    print(f"   Message: {error.get('message', 'N/A')}")
                    
                    if error.get("code") == 6003:
                        print("\n   This error means: Invalid API Token")
                        print("   Possible causes:")
                        print("   1. Token was copied incorrectly (missing characters)")
                        print("   2. Token has been revoked or expired")
                        print("   3. Token was created for a different account")
                        print("   4. Token format is incorrect")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"✗ HTTP {e.code} error")
        try:
            error_data = json.loads(error_body)
            errors = error_data.get("errors", [])
            if errors:
                error = errors[0]
                print(f"   Code: {error.get('code', 'N/A')}")
                print(f"   Message: {error.get('message', 'N/A')}")
        except json.JSONDecodeError:
            print(f"   Response: {error_body}")
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")


def main():
    """Main diagnostic function."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        sys.exit(1)

    env_vars = load_env_file(env_path)
    
    for key, value in env_vars.items():
        os.environ[key] = value

    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not api_token:
        print("Error: CLOUDFLARE_API_TOKEN not found in .env")
        sys.exit(1)

    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "N/A")
    print(f"Account ID: {account_id}")
    print()
    
    diagnose_token(api_token)
    
    print("\n" + "=" * 60)
    print("Recommendations")
    print("=" * 60)
    print("1. Go to: https://dash.cloudflare.com/profile/api-tokens")
    print("2. Create a new Account API Token with:")
    print("   - Account: Cloudflare R2 → Edit")
    print("   - Account Resources: Include → [Your Account ID]")
    print("3. Copy the token immediately (it's only shown once)")
    print("4. Update .env file with the new token")
    print("5. Make sure there are no extra spaces or quotes around the token")


if __name__ == "__main__":
    main()
