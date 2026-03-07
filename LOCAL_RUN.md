# 本地运行音乐生成并上传到 R2

## 前置条件

1. 确保已安装依赖：
```bash
uv sync
```

2. 配置 `.env` 文件（从 `.env copy` 复制或直接编辑）：
```bash
cp ".env copy" .env
```

## 配置 REST API（推荐）

在 `.env` 文件中配置以下变量：

```env
# Cloudflare REST API 配置（使用 Bearer Token）
CLOUDFLARE_ACCOUNT_ID=your-cloudflare-account-id
CLOUDFLARE_API_TOKEN=your-cloudflare-api-token-bearer-token
R2_BUCKET_NAME=music-outputs
R2_PUBLIC_URL=https://your-public-domain.com

# 确保 R2 上传已启用
DISABLE_R2_UPLOAD=false
```

## 运行音乐生成

### 基本用法

```bash
uv run python local_run.py --prompt "a beautiful melody" --duration 30
```

### 完整参数示例

```bash
uv run python local_run.py \
  --prompt "a relaxing jazz piece" \
  --duration 60 \
  --mode simple \
  --inference-steps 8 \
  --guidance-scale 7.0 \
  --seed 42
```

### 自定义模式（带歌词）

```bash
uv run python local_run.py \
  --prompt "a happy song" \
  --duration 30 \
  --mode custom \
  --lyrics "This is a test song, singing along" \
  --bpm 120 \
  --key "C major"
```

## 参数说明

- `--prompt`: 音乐描述（必需）
- `--duration`: 时长（秒），默认 30
- `--mode`: 模式，`simple` 或 `custom`（可选）
- `--lyrics`: 歌词（custom 模式必需）
- `--bpm`: BPM（可选）
- `--key`: 调性（可选）
- `--inference-steps`: 推理步数，默认 8
- `--guidance-scale`: 引导强度，默认 7.0
- `--seed`: 随机种子，默认 -1（随机）
- `--thinking`: 是否启用思考链，默认 true

## 输出

成功后会返回 JSON 格式的结果，包含：
- `status`: "success"
- `output_url`: R2 上的公开 URL
- `mode`: 使用的模式

示例输出：
```json
{
  "output_url": "https://your-public-domain.com/songs/xxx.mp3",
  "status": "success",
  "mode": "simple"
}
```

## 测试 R2 连接

在运行完整生成之前，可以先测试 R2 连接：

```bash
uv run python test_r2_rest_api.py
```

这会：
1. 验证 Cloudflare API Token
2. 测试文件上传功能

## 故障排除

### 如果上传失败

1. 检查 `.env` 文件中的配置是否正确
2. 确认 `DISABLE_R2_UPLOAD` 未设置为 `true`
3. 运行 `test_r2_rest_api.py` 验证连接

### 如果只想本地测试（不上传）

设置环境变量：
```bash
DISABLE_R2_UPLOAD=true uv run python local_run.py --prompt "test"
```

或在 `.env` 中设置：
```env
DISABLE_R2_UPLOAD=true
```
