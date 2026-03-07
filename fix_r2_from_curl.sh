#!/bin/bash
# Fix R2 configuration using Cloudflare API Token from curl command
# This script extracts account ID and API token, then creates R2 API Token

set -e

# Extract account ID and API token from curl command
# Example: curl "https://api.cloudflare.com/client/v4/accounts/13d2f431296ab430eb63df236a1374e2/tokens/verify" \
#          -H "Authorization: Bearer BEsxRu7zHmx-aO4RcMLAnXtlBmegId7MzfH9ElK6"

ACCOUNT_ID="13d2f431296ab430eb63df236a1374e2"
API_TOKEN="BEsxRu7zHmx-aO4RcMLAnXtlBmegId7MzfH9ElK6"

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
