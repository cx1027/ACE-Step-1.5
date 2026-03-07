#!/bin/bash
# Fix R2 configuration using Cloudflare API Token from curl command
# This script extracts account ID and API token, then creates R2 API Token

set -e

# Extract account ID and API token from curl command
# Example: curl "https://api.cloudflare.com/client/v4/accounts/your-account-id/tokens/verify" \
#          -H "Authorization: Bearer your-cloudflare-api-token-bearer-token"

ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-your-cloudflare-account-id}"
API_TOKEN="${CLOUDFLARE_API_TOKEN:-your-cloudflare-api-token-bearer-token}"

echo "Using Account ID: $ACCOUNT_ID"
echo "Using API Token: ${API_TOKEN:0:20}..."
echo ""

# Check if Python script exists
if [ ! -f "get_r2_credentials.py" ]; then
    echo "Error: get_r2_credentials.py not found"
    exit 1
fi

# Set environment variables and run Python script
export CLOUDFLARE_ACCOUNT_ID="$ACCOUNT_ID"
export CLOUDFLARE_API_TOKEN="$API_TOKEN"

echo "Running get_r2_credentials.py..."
echo ""

python3 get_r2_credentials.py <<EOF
y
ACE-Step-R2-Token
y
EOF

echo ""
echo "Done! Check your .env file for updated R2 credentials."
