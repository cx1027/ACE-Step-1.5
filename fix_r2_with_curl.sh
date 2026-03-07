#!/bin/bash
# Fix R2 configuration using Cloudflare API Token from curl command
# This script uses curl to create R2 API Token and update .env file

set -e

# Extract account ID and API token from environment variables or use placeholders
ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-your-cloudflare-account-id}"
API_TOKEN="${CLOUDFLARE_API_TOKEN:-your-cloudflare-api-token-bearer-token}"
TOKEN_NAME="ACE-Step-R2-Token"

echo "=========================================="
echo "R2 Credential Setup"
echo "=========================================="
echo ""
echo "Account ID: $ACCOUNT_ID"
echo "API Token: ${API_TOKEN:0:20}..."
echo ""

# Step 1: List existing R2 tokens (using Workers API endpoint)
echo "Step 1: Checking existing R2 API Tokens..."
echo ""

# Try the Workers API endpoint for R2 tokens
LIST_URL="https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/r2/tokens"
LIST_RESPONSE=$(curl -s -X GET "$LIST_URL" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  2>&1)

if echo "$LIST_RESPONSE" | grep -q '"success":true'; then
    TOKEN_COUNT=$(echo "$LIST_RESPONSE" | grep -o '"access_key_id"' | wc -l | tr -d ' ')
    echo "✓ Found $TOKEN_COUNT existing R2 API Token(s)"
    echo ""
    echo "Existing tokens:"
    echo "$LIST_RESPONSE" | grep -o '"name":"[^"]*"' | sed 's/"name":"/  - /' | sed 's/"$//' || echo "  (Unable to parse)"
    echo ""
else
    echo "⚠ Could not list existing tokens (this is okay)"
    echo "Response: $LIST_RESPONSE"
    echo ""
fi

# Step 2: Create new R2 API Token
echo "Step 2: Creating new R2 API Token..."
echo ""

# Note: R2 API Tokens must be created via Cloudflare Dashboard or Workers API
# The standard API endpoint may not work. Let's try both approaches.

CREATE_URL="https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/r2/tokens"
CREATE_PAYLOAD=$(cat <<EOF
{
  "name": "$TOKEN_NAME",
  "permissions": ["Object Read", "Object Write"],
  "resources": {
    "buckets": []
  }
}
EOF
)

CREATE_RESPONSE=$(curl -s -X POST "$CREATE_URL" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PAYLOAD" \
  2>&1)

echo "Response:"
echo "$CREATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CREATE_RESPONSE"
echo ""

if echo "$CREATE_RESPONSE" | grep -q '"success":true'; then
    # Extract credentials from response
    ACCESS_KEY_ID=$(echo "$CREATE_RESPONSE" | grep -o '"access_key_id":"[^"]*"' | cut -d'"' -f4)
    SECRET_ACCESS_KEY=$(echo "$CREATE_RESPONSE" | grep -o '"secret_access_key":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$ACCESS_KEY_ID" ] || [ -z "$SECRET_ACCESS_KEY" ]; then
        echo "✗ Error: Could not extract credentials from response"
        echo "Please check the response above and create token manually in Cloudflare dashboard"
        exit 1
    fi
    
    echo "=========================================="
    echo "✓ Successfully created R2 API Token!"
    echo "=========================================="
    echo ""
    echo "Token Name: $TOKEN_NAME"
    echo "Access Key ID: $ACCESS_KEY_ID"
    echo "Secret Access Key: $SECRET_ACCESS_KEY"
    echo ""
    echo "⚠️  IMPORTANT: Save the Secret Access Key now!"
    echo "   It will not be shown again."
    echo ""
    
    # Step 3: Update .env file
    R2_ENDPOINT="https://${ACCOUNT_ID}.r2.cloudflarestorage.com"
    R2_BUCKET_NAME="${R2_BUCKET_NAME:-music-outputs}"
    
    echo "Step 3: Updating .env file..."
    echo ""
    
    if [ ! -f .env ]; then
        echo "Creating new .env file..."
        touch .env
    fi
    
    # Backup .env
    cp .env .env.backup 2>/dev/null || true
    
    # Update or add R2 variables
    update_env_var() {
        local var=$1
        local value=$2
        local file=$3
        
        if grep -q "^${var}=" "$file" 2>/dev/null; then
            # Update existing variable
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                sed -i '' "s|^${var}=.*|${var}=${value}|" "$file"
            else
                # Linux
                sed -i "s|^${var}=.*|${var}=${value}|" "$file"
            fi
        else
            # Add new variable
            echo "${var}=${value}" >> "$file"
        fi
    }
    
    update_env_var "R2_ENDPOINT" "$R2_ENDPOINT" .env
    update_env_var "R2_ACCESS_KEY" "$ACCESS_KEY_ID" .env
    update_env_var "R2_SECRET_KEY" "$SECRET_ACCESS_KEY" .env
    
    # Only update bucket name if not already set
    if ! grep -q "^R2_BUCKET_NAME=" .env 2>/dev/null; then
        update_env_var "R2_BUCKET_NAME" "$R2_BUCKET_NAME" .env
    fi
    
    echo "✓ .env file updated!"
    echo ""
    echo "=========================================="
    echo "Configuration Summary"
    echo "=========================================="
    echo ""
    echo "R2_ENDPOINT=$R2_ENDPOINT"
    echo "R2_ACCESS_KEY=$ACCESS_KEY_ID"
    echo "R2_SECRET_KEY=$SECRET_ACCESS_KEY"
    echo "R2_BUCKET_NAME=$(grep "^R2_BUCKET_NAME=" .env | cut -d'=' -f2 || echo "$R2_BUCKET_NAME")"
    echo ""
    echo "Next steps:"
    echo "1. Verify the configuration: bash test_r2_curl.sh"
    echo "2. Or test with Python: python3 test_r2_config.py"
    echo ""
    
else
    echo "✗ Error: Failed to create R2 API Token via API"
    echo ""
    echo "The API endpoint may not be available for your account."
    echo "Please create R2 API Token manually:"
    echo ""
    echo "=========================================="
    echo "Manual Steps to Create R2 API Token:"
    echo "=========================================="
    echo ""
    echo "1. Go to Cloudflare Dashboard:"
    echo "   https://dash.cloudflare.com/"
    echo ""
    echo "2. Navigate to: R2 → Manage R2 API Tokens"
    echo ""
    echo "3. Click 'Create API Token'"
    echo ""
    echo "4. Configure:"
    echo "   - Name: $TOKEN_NAME"
    echo "   - Permissions: Object Read & Write"
    echo "   - Buckets: All buckets (or select 'music-outputs')"
    echo ""
    echo "5. Copy the Access Key ID and Secret Access Key"
    echo ""
    echo "6. Update your .env file with:"
    echo "   R2_ENDPOINT=https://${ACCOUNT_ID}.r2.cloudflarestorage.com"
    echo "   R2_ACCESS_KEY=<your-access-key-id>"
    echo "   R2_SECRET_KEY=<your-secret-access-key>"
    echo "   R2_BUCKET_NAME=music-outputs"
    echo ""
    echo "Or run this script again after creating the token manually."
    echo ""
    exit 1
fi
