# R2 Authentication Methods Explained

## Why `test_r2_config.py` Works But `test_r2_simple.py` Doesn't

Cloudflare R2 supports **two different authentication methods**, and these two test scripts use different ones:

### Method 1: S3-Compatible API (Used by `test_r2_config.py`)

**Credentials Required:**
- `R2_ENDPOINT` - Your R2 endpoint URL
- `R2_ACCESS_KEY` - S3-compatible access key ID
- `R2_SECRET_KEY` - S3-compatible secret access key

**How it works:**
- Uses `boto3` library (AWS S3 SDK)
- Compatible with S3 API
- Works with standard S3 tools and libraries

**Status:** ✅ **Working** - Your S3-compatible credentials are valid

### Method 2: Cloudflare REST API (Used by `test_r2_simple.py`)

**Credentials Required:**
- `CLOUDFLARE_ACCOUNT_ID` - Your Cloudflare account ID
- `CLOUDFLARE_API_TOKEN` - Cloudflare API token with R2 permissions

**How it works:**
- Uses Cloudflare's REST API directly
- Uses Bearer token authentication
- More native to Cloudflare ecosystem

**Status:** ❌ **Not Working** - Your API token is invalid or missing

## How to Fix `test_r2_simple.py`

You have two options:

### Option A: Create a Valid Cloudflare API Token

1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token"
3. Select "Account API Tokens" (not User API Tokens)
4. Configure:
   - **Account**: Select your account (`13d2f431296ab430eb63df236a1374e2`)
   - **Permissions**: Account → Cloudflare R2 → Edit
5. Copy the token immediately (shown only once)
6. Update `.env`:
   ```
   CLOUDFLARE_API_TOKEN=<your-new-token>
   ```

### Option B: Use S3-Compatible Method Instead

Since `test_r2_config.py` already works, you can use the S3-compatible method for all operations. This is often simpler and more compatible with existing tools.

## Which Method Should You Use?

- **S3-Compatible (Method 1)**: Better if you're using boto3, have existing S3 tools, or want maximum compatibility
- **REST API (Method 2)**: Better if you want to use Cloudflare-specific features or prefer REST API over S3 API

Both methods work equally well for basic R2 operations (upload, download, list).
