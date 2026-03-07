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

#### Step 2.1: Access RunPod Dashboard

1. 登录 [RunPod Dashboard](https://www.runpod.io/console/serverless)
2. 在左侧导航栏，点击 **Serverless**
3. 点击右上角的 **Create Endpoint** 按钮

#### Step 2.2: Configure Basic Settings

在创建页面的 **Basic Settings** 部分：

1. **Endpoint Name** (必填)
   - 输入一个描述性的名称，例如：`acestep-music-generator`
   - 这个名称会用于识别你的 endpoint

2. **Container Image** (必填)
   - 输入你推送到 Docker Hub 的镜像地址：
     ```
     your-username/acestep-runpod:latest
     ```
   - 替换 `your-username` 为你的 Docker Hub 用户名
   - 例如：`john/acestep-runpod:latest`

3. **Handler Path** (必填)
   - 输入：`runpod_handler.py`
   - 这是 RunPod 会调用的主处理函数文件

#### Step 2.3: Configure GPU Settings

在 **GPU Settings** 部分：

1. **GPU Type** (必填)
   - 推荐选择：**RTX 3090**、**RTX 4090**、**A100** 或 **A6000**
   - 根据你的模型选择：
     - `acestep-5Hz-lm-0.6B`: 至少 16GB VRAM (RTX 3090/4090)
     - `acestep-5Hz-lm-1.7B`: 推荐 24GB VRAM (RTX 4090/A6000)
     - `acestep-5Hz-lm-4B`: 需要 20GB+ VRAM (A100/A6000)

2. **Min Workers** (可选)
   - 推荐设置为 `0`（按需启动，节省成本）
   - 如果希望保持常驻，设置为 `1` 或更高

3. **Max Workers** (可选)
   - 根据你的并发需求设置，例如：`5`

4. **Idle Timeout** (可选)
   - 推荐：`5` 秒（worker 空闲多久后关闭）
   - 可以设置为 `10-30` 秒以平衡响应速度和成本

#### Step 2.4: Configure Environment Variables

在 **Environment Variables** 部分，点击 **Add Environment Variable** 添加以下变量：

**必需的 R2 配置变量**（二选一，推荐方式 1）：

**方式 1: Cloudflare REST API（推荐）**

这种方式使用 Cloudflare API Token，更安全且易于管理。

| 变量名 | 值示例 | 说明 | 如何获取 |
|--------|--------|------|----------|
| `CLOUDFLARE_ACCOUNT_ID` | `your-cloudflare-account-id` | Cloudflare 账户 ID | 在 Cloudflare Dashboard 右上角可以看到 |
| `CLOUDFLARE_API_TOKEN` | `your-cloudflare-api-token-bearer-token` | Cloudflare API Token | [创建 API Token](https://dash.cloudflare.com/profile/api-tokens)，权限：Account > Cloudflare R2 > Edit |
| `R2_BUCKET_NAME` | `music-outputs` | R2 bucket 名称 | 在 R2 Dashboard 中创建或查看 |
| `R2_PUBLIC_URL` | `https://your-public-domain.com` | 公共访问 URL 前缀 | 在 R2 bucket 设置中配置自定义域名或使用默认 R2.dev 域名 |

**方式 2: S3-Compatible API（备选）**

如果方式 1 不可用，可以使用 S3 兼容的 API。

| 变量名 | 值示例 | 说明 | 如何获取 |
|--------|--------|------|----------|
| `R2_ENDPOINT` | `https://your-account-id.r2.cloudflarestorage.com` | R2 endpoint URL | 格式：`https://{账户ID}.r2.cloudflarestorage.com` |
| `R2_ACCESS_KEY` | `your-r2-access-key-id` | R2 访问密钥 ID | [R2 API Tokens](https://dash.cloudflare.com/) → R2 → Manage R2 API Tokens |
| `R2_SECRET_KEY` | `your-r2-secret-access-key` | R2 秘密访问密钥 | 同上，创建 token 时获取 |
| `R2_BUCKET_NAME` | `music-outputs` | R2 bucket 名称 | 在 R2 Dashboard 中创建或查看 |
| `R2_PUBLIC_URL` | `https://your-public-domain.com` | 公共访问 URL 前缀 | 在 R2 bucket 设置中配置自定义域名或使用默认 R2.dev 域名 |

**注意**：
- 两种方式只需要选择一种即可，不需要同时配置
- 推荐使用**方式 1**（Cloudflare REST API），因为它更简单且安全
- 如果两种方式都配置了，代码会优先使用方式 1

**可选的 ACE-Step 配置变量**（根据需要添加）：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `ACESTEP_CONFIG_PATH` | `acestep-v15-turbo` | DiT 模型名称 |
| `ACESTEP_DEVICE` | `auto` | 设备选择 (auto/cuda/cpu) |
| `ACESTEP_USE_FLASH_ATTENTION` | `true` | 启用 flash attention |
| `ACESTEP_COMPILE_MODEL` | `false` | 编译模型以提升速度 |
| `ACESTEP_OFFLOAD_TO_CPU` | `false` | 卸载到 CPU |
| `ACESTEP_OFFLOAD_DIT_TO_CPU` | `false` | 卸载 DiT 到 CPU |
| `ACESTEP_LM_MODEL_PATH` | `acestep-5Hz-lm-0.6B` | LLM 模型路径 |
| `ACESTEP_LM_BACKEND` | `vllm` | LLM 后端 (vllm/pt) |
| `ACESTEP_LM_OFFLOAD_TO_CPU` | `false` | 卸载 LLM 到 CPU |

**详细填写步骤（以方式 1 为例）**：

1. **添加 CLOUDFLARE_ACCOUNT_ID**
   - 点击 **"Add Environment Variable"** 按钮
   - **Key**: `CLOUDFLARE_ACCOUNT_ID`
   - **Value**: 你的 Cloudflare 账户 ID（例如：`your-cloudflare-account-id`）
   - 点击 **"Add"** 或 **"Save"** 保存

2. **添加 CLOUDFLARE_API_TOKEN**
   - 再次点击 **"Add Environment Variable"**
   - **Key**: `CLOUDFLARE_API_TOKEN`
   - **Value**: 你的 API Token（例如：`your-cloudflare-api-token-bearer-token`）
   - 点击 **"Add"** 保存

3. **添加 R2_BUCKET_NAME**
   - **Key**: `R2_BUCKET_NAME`
   - **Value**: 你的 bucket 名称（例如：`music-outputs`）
   - 点击 **"Add"** 保存

4. **添加 R2_PUBLIC_URL**
   - **Key**: `R2_PUBLIC_URL`
   - **Value**: 你的公共访问 URL（例如：`https://your-public-domain.com`）
   - 点击 **"Add"** 保存

**完整示例（方式 1 - 推荐）**：
```
CLOUDFLARE_ACCOUNT_ID = your-cloudflare-account-id
CLOUDFLARE_API_TOKEN = your-cloudflare-api-token-bearer-token
R2_BUCKET_NAME = your-bucket-name
R2_PUBLIC_URL = https://your-public-domain.com
```

**完整示例（方式 2 - 备选）**：
```
R2_ENDPOINT = https://your-account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY = your-r2-access-key-id
R2_SECRET_KEY = your-r2-secret-access-key
R2_BUCKET_NAME = music-outputs
R2_PUBLIC_URL = https://your-public-domain.com
```

**重要提示**：
- 所有变量名都是**大小写敏感**的，请确保完全匹配
- 不要包含引号（`"` 或 `'`），直接填写值
- 如果值中包含空格，不需要特殊处理，直接填写即可
- 保存后，RunPod 会自动应用这些环境变量到容器中

#### Step 2.5: Configure Advanced Settings (可选)

在 **Advanced Settings** 部分：

1. **Container Disk** (可选)
   - 默认值通常足够（20GB）
   - 如果需要下载大型模型，可以增加到 `50GB` 或 `100GB`

2. **Container Registry Credentials** (可选)
   - 如果你的 Docker 镜像是私有的，需要添加 Docker Hub 凭据
   - 对于公共镜像，可以跳过

3. **Network Volume** (可选)
   - 如果需要持久化存储模型文件，可以配置网络卷
   - 通常不需要，因为模型会从 Hugging Face 或 ModelScope 下载

4. **Timeout** (可选)
   - 推荐设置为 `600` 秒（10 分钟）或更长
   - 音乐生成可能需要较长时间

#### Step 2.6: Review and Create

1. 检查所有配置是否正确
2. 确认环境变量都已添加
3. 点击 **Create Endpoint** 按钮

#### Step 2.7: Wait for Deployment

1. RunPod 会开始部署你的 endpoint
2. 首次部署可能需要几分钟来：
   - 拉取 Docker 镜像
   - 启动容器
   - 下载模型文件（如果未缓存）
3. 在 **Serverless** 页面可以看到部署状态：
   - **Deploying**: 正在部署
   - **Ready**: 准备就绪
   - **Error**: 部署失败（查看日志）

#### Step 2.8: Verify Deployment

1. 点击你的 endpoint 名称进入详情页
2. 查看 **Logs** 标签页，确认没有错误
3. 应该看到类似日志：
   ```
   Loaded environment variables from /app/.env (if using .env)
   Initializing ACE-Step handler...
   Handler ready
   ```

#### Step 2.9: Test the Endpoint

1. 在 endpoint 详情页，找到 **Test** 或 **Send Test Request** 按钮
2. 使用以下测试输入：

```json
{
  "input": {
    "prompt": "generate a song for rain within 30 secs",
    "duration": 30
  }
}
```

3. 点击 **Send** 发送测试请求
4. 查看响应，应该返回：
```json
{
  "output_url": "https://your-public-domain.com/songs/uuid.mp3",
  "status": "success",
  "mode": null
}
```

#### 常见问题排查

**问题 1: 镜像拉取失败 - "no matching manifest for linux/amd64"**

这是最常见的错误，通常发生在 macOS (ARM64) 上构建镜像时。

**原因**: 在 macOS 上使用 `docker build` 会默认构建 ARM64 镜像，但 RunPod 需要 AMD64 镜像。

**解决方案**:
1. 使用 `docker buildx` 明确指定平台：
   ```bash
   docker buildx build --platform linux/amd64 -t your-username/acestep-runpod:latest --push .
   ```

2. 或使用部署脚本（已自动处理）：
   ```bash
   ./deploy_to_runpod.sh --username your-username --tag latest
   ```

3. **重要**: 重新 pull 镜像不会解决这个问题，必须重新构建并推送正确的平台镜像。

**问题 2: 镜像拉取失败（其他原因）**
- 检查镜像名称是否正确
- 确认镜像已成功推送到 Docker Hub
- 检查 Docker Hub 镜像是否为公开（或已配置凭据）
- 确认镜像包含 `linux/amd64` 平台（使用 `docker manifest inspect your-username/acestep-runpod:latest` 检查）

**问题 2: Handler 找不到**
- 确认 Handler Path 设置为 `runpod_handler.py`
- 检查 Dockerfile 中是否正确复制了文件

**问题 3: 环境变量缺失错误**
- 确认所有必需的 R2 变量都已添加
- 检查变量名拼写是否正确（区分大小写）

**问题 4: GPU 内存不足**
- 尝试使用更小的 LLM 模型（`acestep-5Hz-lm-0.6B`）
- 启用 CPU offload 选项
- 升级到更大的 GPU

**问题 5: 模型下载超时**
- 增加 Timeout 设置
- 检查网络连接
- 考虑使用网络卷预下载模型

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

A `Dockerfile` is provided for building the container image.

**⚠️ IMPORTANT: Platform Architecture**

RunPod requires **linux/amd64** images. If you're building on macOS (ARM64) or other non-AMD64 platforms, you **must** use `docker buildx` with `--platform linux/amd64`:

```bash
# For RunPod deployment (REQUIRED: specify linux/amd64 platform)
docker buildx build --platform linux/amd64 -t acestep-runpod:latest --push .

# Or use the deployment script (recommended):
./deploy_to_runpod.sh --username your-dockerhub-username --tag latest
```

**If you build without specifying platform on macOS**, the image will be ARM64 and RunPod will fail with:
```
failed to pull image: no matching manifest for linux/amd64 in the manifest list entries
```

**Manual build (if not using the script):**

```bash
# Build and push directly (recommended for macOS)
docker buildx build --platform linux/amd64 -t your-username/acestep-runpod:latest --push .

# Or build locally first (may not work on macOS due to --load limitation)
docker buildx build --platform linux/amd64 -t acestep-runpod:latest --load .
docker tag acestep-runpod:latest your-username/acestep-runpod:latest
docker push your-username/acestep-runpod:latest
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
