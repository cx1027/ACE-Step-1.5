#!/bin/bash
# Update R2 configuration in .env file
# This script helps you update R2 credentials manually

set -e

ACCOUNT_ID="13d2f431296ab430eb63df236a1374e2"

echo "=========================================="
echo "R2 Configuration Updater"
echo "=========================================="
echo ""
echo "Account ID: $ACCOUNT_ID"
echo "R2 Endpoint: https://${ACCOUNT_ID}.r2.cloudflarestorage.com"
echo ""
echo "Note: You need R2 API Token (Access Key ID + Secret Access Key)"
echo "      This is different from Cloudflare API Token."
echo ""
echo "To get R2 API Token:"
echo "1. Go to: https://dash.cloudflare.com/"
echo "2. Navigate to: R2 → Manage R2 API Tokens"
echo "3. Create a new token or use existing one"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating new .env file..."
    touch .env
fi

# Backup .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
echo "✓ Backed up .env to .env.backup.*"
echo ""

# Function to update env variable
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
        echo "✓ Updated $var"
    else
        # Add new variable
        echo "${var}=${value}" >> "$file"
        echo "✓ Added $var"
    fi
}

# Get R2 credentials
read -p "Enter R2 Access Key ID: " ACCESS_KEY_ID
read -sp "Enter R2 Secret Access Key: " SECRET_ACCESS_KEY
echo ""
read -p "Enter R2 Bucket Name (default: music-outputs): " BUCKET_NAME
BUCKET_NAME=${BUCKET_NAME:-music-outputs}

read -p "Enter R2 Public URL (optional, press Enter to skip): " PUBLIC_URL

if [ -z "$ACCESS_KEY_ID" ] || [ -z "$SECRET_ACCESS_KEY" ]; then
    echo ""
    echo "✗ Error: Access Key ID and Secret Access Key are required"
    exit 1
fi

echo ""
echo "Updating .env file..."

# Update R2 configuration
R2_ENDPOINT="https://${ACCOUNT_ID}.r2.cloudflarestorage.com"
update_env_var "R2_ENDPOINT" "$R2_ENDPOINT" .env
update_env_var "R2_ACCESS_KEY" "$ACCESS_KEY_ID" .env
update_env_var "R2_SECRET_KEY" "$SECRET_ACCESS_KEY" .env
update_env_var "R2_BUCKET_NAME" "$BUCKET_NAME" .env

if [ -n "$PUBLIC_URL" ]; then
    update_env_var "R2_PUBLIC_URL" "$PUBLIC_URL" .env
fi

echo ""
echo "=========================================="
echo "✓ Configuration Updated!"
echo "=========================================="
echo ""
echo "Updated values:"
echo "  R2_ENDPOINT=$R2_ENDPOINT"
echo "  R2_ACCESS_KEY=$ACCESS_KEY_ID"
echo "  R2_SECRET_KEY=***hidden***"
echo "  R2_BUCKET_NAME=$BUCKET_NAME"
if [ -n "$PUBLIC_URL" ]; then
    echo "  R2_PUBLIC_URL=$PUBLIC_URL"
fi
echo ""
echo "Next step: Test the configuration"
echo "  bash test_r2_curl.sh"
echo "  or"
echo "  python3 test_r2_config.py"
echo ""
