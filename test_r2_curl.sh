#!/bin/bash
# Test R2 configuration using curl command
# This script loads .env and generates a curl command to test R2 connection

set -e

# Load .env file
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    exit 1
fi

# Source .env file safely
while IFS= read -r line || [ -n "$line" ]; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$line" ]] && continue
    # Export the variable
    export "$line" 2>/dev/null || true
done < .env

# Check required variables
required_vars=("R2_ENDPOINT" "R2_ACCESS_KEY" "R2_SECRET_KEY" "R2_BUCKET_NAME")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set in .env"
        exit 1
    fi
done

echo "R2 Configuration:"
echo "  R2_ENDPOINT: $R2_ENDPOINT"
echo "  R2_ACCESS_KEY: ${R2_ACCESS_KEY:0:8}..."
echo "  R2_BUCKET_NAME: $R2_BUCKET_NAME"
echo ""

# Method 1: Use AWS CLI (if installed)
if command -v aws &> /dev/null; then
    echo "=== Method 1: Using AWS CLI ==="
    echo ""
    echo "Testing with AWS CLI..."
    
    # Configure AWS CLI for R2
    export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="$R2_SECRET_KEY"
    export AWS_DEFAULT_REGION="auto"
    
    # Test by listing buckets
    echo "Command: aws s3 ls --endpoint-url \"$R2_ENDPOINT\""
    if aws s3 ls --endpoint-url "$R2_ENDPOINT" 2>&1; then
        echo ""
        echo "✓ AWS CLI test successful!"
    else
        echo ""
        echo "✗ AWS CLI test failed"
    fi
    
    # Test bucket access
    echo ""
    echo "Testing bucket access..."
    echo "Command: aws s3 ls s3://$R2_BUCKET_NAME --endpoint-url \"$R2_ENDPOINT\""
    if aws s3 ls "s3://$R2_BUCKET_NAME" --endpoint-url "$R2_ENDPOINT" 2>&1; then
        echo ""
        echo "✓ Bucket access test successful!"
    else
        echo ""
        echo "✗ Bucket access test failed"
    fi
    echo ""
fi

# Method 2: Generate curl command using Python (requires boto3)
echo "=== Method 2: Using curl with Python-generated signature ==="
echo ""
if command -v python3 &> /dev/null && python3 -c "import boto3" 2>/dev/null; then
    echo "Generating curl command with AWS Signature..."
    python3 << 'PYTHON_SCRIPT'
import os
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime
import urllib.parse

# Get credentials from environment
endpoint = os.environ.get("R2_ENDPOINT", "").rstrip("/")
bucket = os.environ.get("R2_BUCKET_NAME", "")
access_key = os.environ.get("R2_ACCESS_KEY", "")
secret_key = os.environ.get("R2_SECRET_KEY", "")

if not all([endpoint, bucket, access_key, secret_key]):
    print("Error: Missing required environment variables")
    exit(1)

# Construct URL
url = f"{endpoint}/{bucket}/"

# Create a request
request = AWSRequest(method="GET", url=url)
request.context = {"is_presign_request": False}

# Sign the request
credentials = {
    "access_key": access_key,
    "secret_key": secret_key,
}
signer = SigV4Auth(credentials, "s3", "auto")
signer.add_auth(request)

# Print curl command
headers = []
for key, value in request.headers.items():
    headers.append(f"-H '{key}: {value}'")

print(f"curl -X GET '{url}' \\")
print("  " + " \\\n  ".join(headers))
print("")
print("Or test bucket listing:")
print(f"curl -X GET '{endpoint}/' \\")
print("  " + " \\\n  ".join(headers))
PYTHON_SCRIPT
else
    echo "Python3 with boto3 not available. Skipping curl signature generation."
    echo ""
    echo "To test with curl manually, you need to:"
    echo "1. Generate AWS Signature Version 4"
    echo "2. Include Authorization header"
    echo ""
    echo "Alternatively, use the Python test script:"
    echo "  python3 test_r2_config.py"
fi

echo ""
echo "=== Method 3: Simple endpoint test (no auth) ==="
echo ""
echo "Testing if R2 endpoint is reachable..."
endpoint_host=$(echo "$R2_ENDPOINT" | sed -E 's|https?://([^/]+).*|\1|')
if curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://$endpoint_host" | grep -q "200\|403\|401"; then
    echo "✓ Endpoint is reachable"
else
    echo "✗ Endpoint may not be reachable or requires authentication"
fi
