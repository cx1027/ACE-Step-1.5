# RunPod Serverless Deployment Guide

This guide explains how to deploy ACE-Step to RunPod serverless with proper environment variable configuration.

## Environment Variable Configuration

There are **two ways** to configure environment variables for RunPod serverless:

### Method 1: RunPod Console (Recommended for Production)

**Best for**: Sensitive credentials (R2 keys, API keys)

1. Go to your RunPod serverless endpoint settings
2. Navigate to **Environment Variables** section
3. Add each variable individually:
   - `R2_ENDPOINT`
   - `R2_ACCESS_KEY`
   - `R2_SECRET_KEY`
   - `R2_BUCKET_NAME`
   - `R2_PUBLIC_URL`
   - `ACESTEP_CONFIG_PATH` (optional)
   - `ACESTEP_DEVICE` (optional)
   - etc.

**Advantages**:
- ✅ Secure: Credentials stored in RunPod's secure vault
- ✅ Easy to update without redeploying
- ✅ No risk of committing secrets to version control

### Method 2: .env File (For Development/Testing)

**Best for**: Local testing and development

1. Copy the example file:
   ```bash
   cp runpod.env.example .env
   ```

2. Edit `.env` and fill in your values:
   ```bash
   # Required R2 configuration
   R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
   R2_ACCESS_KEY=your-r2-access-key-id
   R2_SECRET_KEY=your-r2-secret-access-key
   R2_BUCKET_NAME=your-bucket-name
   R2_PUBLIC_URL=https://your-public-domain.com
   
   # Optional ACE-Step configuration
   ACESTEP_CONFIG_PATH=acestep-v15-turbo
   ACESTEP_DEVICE=auto
   ```

3. **For RunPod deployment**: Include `.env` in your deployment package
   - The handler will automatically load `.env` if it exists in the same directory as `runpod_handler.py`
   - **Note**: `.env` is in `.gitignore` for security - you'll need to manually include it in your deployment
   - **Alternative**: Use RunPod's environment variable settings (Method 1) instead

**Advantages**:
- ✅ Easy to test locally
- ✅ Version control friendly (use `.env.example` as template)
- ✅ All configuration in one place

**Disadvantages**:
- ⚠️ Risk of committing secrets if not careful
- ⚠️ Need to redeploy when changing values

## Deployment Steps

### 1. Prepare Your Code

Ensure your deployment package includes:
- `runpod_handler.py` (main handler)
- `.env` file (if using Method 2)
- All ACE-Step dependencies (handled by RunPod's Docker build)

### 2. Create RunPod Serverless Endpoint

1. Go to RunPod dashboard → **Serverless** → **Create Endpoint**
2. Configure:
   - **Container Image**: Use a base image with Python 3.11-3.12
   - **Handler Path**: `runpod_handler.py`
   - **Environment Variables**: Add all required variables (Method 1)

### 3. Install Dependencies

In your Dockerfile or startup script, install required packages:

```dockerfile
# Example Dockerfile snippet
RUN pip install runpod boto3 python-dotenv
# ... other dependencies
```

Or add to `requirements.txt`:
```
runpod
boto3
python-dotenv
```

### 4. Build Docker Image

A `Dockerfile` is provided for building the container image:

```bash
# Build the image
docker build -t acestep-runpod .

# Or if you want to include .env file (for development/testing):
# 1. First, create .env from the example:
cp runpod.env.example .env
# 2. Edit .env with your values
# 3. Uncomment the COPY .env line in Dockerfile
# 4. Build:
docker build -t acestep-runpod .
```

**Note**: Including `.env` in the Docker image embeds secrets. For production, use RunPod's environment variable settings (Method 1) instead.

### 5. Upload .env File (If Using Method 2)

If you prefer using `.env` file:

1. **Option A**: Include in Docker image (see above)
   - Uncomment `COPY .env /app/.env` in `Dockerfile`
   - Build the image with `.env` included

2. **Option B**: Upload via RunPod's file system
   - Use RunPod's volume mount or file upload feature
   - Place `.env` in the working directory

3. **Option C**: Use RunPod's secrets management
   - Store `.env` content as a secret
   - Mount it at runtime

## Required Environment Variables

### Cloudflare R2 (Required)

| Variable | Description | Example |
|----------|-------------|---------|
| `R2_ENDPOINT` | R2 API endpoint URL | `https://xxx.r2.cloudflarestorage.com` |
| `R2_ACCESS_KEY` | R2 access key ID | `your-access-key-id` |
| `R2_SECRET_KEY` | R2 secret access key | `your-secret-key` |
| `R2_BUCKET_NAME` | R2 bucket name | `music-storage` |
| `R2_PUBLIC_URL` | Public URL prefix for files | `https://cdn.example.com` |

### ACE-Step Configuration (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `ACESTEP_PROJECT_ROOT` | Current directory | Project root path |
| `ACESTEP_CONFIG_PATH` | `acestep-v15-turbo` | DiT model name |
| `ACESTEP_DEVICE` | `auto` | Device (auto/cuda/cpu) |
| `ACESTEP_USE_FLASH_ATTENTION` | `true` | Enable flash attention |
| `ACESTEP_COMPILE_MODEL` | `false` | Compile model for speed |
| `ACESTEP_OFFLOAD_TO_CPU` | `false` | Offload to CPU |
| `ACESTEP_OFFLOAD_DIT_TO_CPU` | `false` | Offload DiT to CPU |
| `ACESTEP_LM_MODEL_PATH` | `acestep-5Hz-lm-0.6B` | LLM model path (options: `acestep-5Hz-lm-0.6B`, `acestep-5Hz-lm-1.7B`, `acestep-5Hz-lm-4B`) |
| `ACESTEP_LM_BACKEND` | `vllm` | LLM backend (vllm/pt) |
| `ACESTEP_LM_OFFLOAD_TO_CPU` | `false` | Offload LLM to CPU |

### LLM Model Selection Guide

Choose the appropriate LLM model based on your GPU memory:

- **`acestep-5Hz-lm-0.6B`** (default): Smallest model, suitable for GPUs with limited VRAM (< 16GB)
- **`acestep-5Hz-lm-1.7B`** (recommended): Balanced model, recommended for 16-24GB GPUs
- **`acestep-5Hz-lm-4B`**: Largest model, requires 20GB+ VRAM

**Example**: To use the 1.7B model, set:
```bash
ACESTEP_LM_MODEL_PATH=acestep-5Hz-lm-1.7B
```

## Testing Your Deployment

The RunPod handler `generate_music_job` supports **three main functions**:

- **1. Caption → song**: Use `prompt`/`caption` to generate a song (lyrics optional, defaults to instrumental).
- **2. Caption + lyrics → song**: Provide both `prompt`/`caption` and explicit `lyrics` for custom songs.
- **3. Progress updates / checking**: Pass `callback_url` to receive JSON progress updates while the job runs.

### 1. Caption → song (仅用 caption 生歌)

**RunPod test job input (caption only, lyrics optional/instrumental by default):**

```json
{
  "input": {
    "prompt": "generate a song for rain within 30 secs",
    "duration": 30
  }
}
```

**Expected output:**

```json
{
  "output_url": "https://your-public-domain.com/songs/uuid.mp3",
  "status": "success",
  "mode": null
}
```

**Local zsh example (same behavior via `local_run.py`):**

```bash
uv run python local_run.py \
  --prompt "generate a song for rain within 30 secs" \
  --duration 30
```

### 2. Caption + lyrics → song (caption + lyrics 生歌)

To force using your own lyrics, set `mode` to `"custom"` and provide `lyrics`:

```json
{
  "input": {
    "prompt": "a powerful rock ballad",
    "duration": 60,
    "mode": "custom",
    "lyrics": "Here are my custom lyrics for the song",
    "bpm": 120,
    "key": "C Major"
  }
}
```

If `mode` is `"custom"` and `lyrics` is missing or empty, the handler returns an error:

```json
{
  "status": "error",
  "error": "Custom mode requires 'lyrics' in job input."
}
```

### 3. Progress updates / check progress (进度查询)

The handler can send **progress callbacks** to your own HTTP endpoint.  
Include a `callback_url` field in the RunPod job `input`:

```json
{
  "input": {
    "prompt": "a beautiful melody",
    "duration": 30,
    "callback_url": "https://your-api.example.com/runpod/progress"
  }
}
```

During generation, the handler posts JSON payloads like:

```json
{
  "job_id": "runpod-job-id",
  "status": "generating",
  "progress": 10,
  "mode": null
}
```

Final success callback example:

```json
{
  "job_id": "runpod-job-id",
  "status": "success",
  "progress": 100,
  "output_url": "https://your-public-domain.com/songs/uuid.mp3",
  "mode": null
}
```

You can also use the standard RunPod Serverless API to query job status by `job_id` if you prefer polling instead of callbacks.

## Troubleshooting

### Error: "Missing required environment variable"

- Check that all R2 variables are set in RunPod console (Method 1) or `.env` file (Method 2)
- Verify variable names match exactly (case-sensitive)

### Error: "Failed to initialize handlers"

- Check model paths are correct
- Verify device configuration matches your GPU
- Check logs for specific initialization errors

### .env file not loading

- Ensure `python-dotenv` is installed: `pip install python-dotenv`
- Verify `.env` file is in the same directory as `runpod_handler.py`
- Check file permissions

## Security Best Practices

1. **Never commit `.env` to version control**
   - Add `.env` to `.gitignore`
   - Use `.env.example` as a template

2. **Use RunPod secrets for sensitive data**
   - Store R2 credentials in RunPod's environment variables (Method 1)
   - Rotate keys regularly

3. **Limit R2 bucket permissions**
   - Use IAM policies to restrict access
   - Only allow necessary operations (PutObject, GetObject)

4. **Monitor usage**
   - Set up alerts for unusual activity
   - Review RunPod logs regularly

## Additional Resources

- [RunPod Serverless Documentation](https://docs.runpod.io/serverless)
- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [ACE-Step Documentation](./README.md)
