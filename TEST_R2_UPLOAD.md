# R2 上传测试说明

本文档说明如何测试从本地生成 music.mp3 并上传到 Cloudflare R2 的完整流程。

## 测试脚本

### 1. `test_r2_upload_simple.py` - 简单上传测试

快速测试 R2 上传功能，不涉及音乐生成。

**用法：**
```bash
# 使用自动生成的测试文件
uv run python test_r2_upload_simple.py

# 使用现有的 MP3 文件
uv run python test_r2_upload_simple.py --file path/to/music.mp3
```

**功能：**
- 验证 .env 配置是否正确加载
- 测试 Cloudflare API Token 认证
- 测试文件上传到 R2
- 如果 REST API 失败，自动尝试 S3-compatible API

### 2. `test_local_r2_upload.py` - 完整流程测试

测试从音乐生成到 R2 上传的完整流程。

**用法：**
```bash
# 基本用法
uv run python test_local_r2_upload.py --prompt "a beautiful melody" --duration 30

# 完整参数
uv run python test_local_r2_upload.py \
    --prompt "a beautiful melody" \
    --duration 30 \
    --inference-steps 8 \
    --guidance-scale 7.0 \
    --seed 42

# 仅测试上传（使用现有文件）
uv run python test_local_r2_upload.py --test-file path/to/music.mp3
```

**功能：**
- 加载 .env 配置
- 生成音乐（使用 ACE-Step）
- 自动上传生成的 music.mp3 到 R2
- 返回 R2 公共 URL

## .env 配置要求

### 方法 1: REST API (推荐)

```env
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_API_TOKEN=your-api-token
R2_BUCKET_NAME=your-bucket-name
R2_PUBLIC_URL=https://your-public-domain.com
```

**注意：** API Token 需要以下权限：
- Account > Cloudflare R2 > Edit
- 如果上传失败（403 Forbidden），可能需要使用 S3-compatible API

### 方法 2: S3-Compatible API (备选)

如果 REST API 权限不足，可以使用 S3-compatible API：

```env
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY=your-r2-access-key-id
R2_SECRET_KEY=your-r2-secret-access-key
R2_BUCKET_NAME=your-bucket-name
R2_PUBLIC_URL=https://your-public-domain.com
```

**获取 R2 Access Key：**
1. 登录 Cloudflare Dashboard
2. 进入 R2 > Manage R2 API Tokens
3. 创建新的 API Token
4. 复制 Access Key ID 和 Secret Access Key

## 测试结果

### 当前测试状态

✅ **配置加载成功**
- .env 文件已正确加载
- R2 配置已检测到（使用 REST API 方法）

✅ **API Token 认证成功**
- Cloudflare API Token 验证通过

❌ **REST API 上传失败**
- 错误：403 Forbidden - Authentication error
- 可能原因：API Token 没有 R2 对象写入权限

### 解决方案

#### 选项 1: 使用 S3-Compatible API

在 .env 文件中添加 S3-compatible 配置：

```env
# 保留 REST API 配置（用于认证验证）
CLOUDFLARE_ACCOUNT_ID=13d2f431296ab430eb63df236a1374e2
CLOUDFLARE_API_TOKEN=your-token

# 添加 S3-compatible 配置（用于文件上传）
R2_ENDPOINT=https://13d2f431296ab430eb63df236a1374e2.r2.cloudflarestorage.com
R2_ACCESS_KEY=your-r2-access-key-id
R2_SECRET_KEY=your-r2-secret-access-key
R2_BUCKET_NAME=music-outputs
R2_PUBLIC_URL=https://pub-41f5517642ad492cbae588b5671e80cb.r2.dev
```

测试脚本会自动在 REST API 失败时尝试 S3-compatible API。

#### 选项 2: 更新 API Token 权限

1. 登录 Cloudflare Dashboard
2. 进入 Profile > API Tokens
3. 编辑你的 API Token
4. 确保权限包括：
   - Account > Cloudflare R2 > Edit
   - 或者创建新的 API Token 并授予完整 R2 权限

## 使用 local_run.py

`local_run.py` 是用于本地开发的脚本，会自动：
- 加载 .env 配置
- 如果没有 R2 配置，默认禁用 R2 上传
- 如果有 R2 配置，自动启用上传

**用法：**
```bash
# 生成音乐并上传到 R2（需要 R2 配置）
uv run python local_run.py --prompt "a beautiful melody" --duration 30

# 禁用 R2 上传（仅本地生成）
DISABLE_R2_UPLOAD=1 uv run python local_run.py --prompt "a beautiful melody" --duration 30
```

## 验证上传成功

上传成功后，你会得到：
1. **输出 URL** - R2 公共 URL，可以直接访问
2. **日志信息** - 包含上传详情和对象键

**验证方法：**
```bash
# 检查上传的文件
curl -I <output_url>

# 或在浏览器中打开
open <output_url>
```

## 故障排除

### 问题 1: 403 Forbidden

**原因：** API Token 权限不足

**解决：**
- 使用 S3-compatible API（推荐）
- 或更新 API Token 权限

### 问题 2: 文件未上传，返回本地路径

**原因：** `DISABLE_R2_UPLOAD` 被设置，或 R2 配置缺失

**解决：**
- 检查 .env 文件中的 R2 配置
- 确保 `DISABLE_R2_UPLOAD` 未设置或设置为 `0`/`false`

### 问题 3: 网络错误

**原因：** 网络连接问题或防火墙阻止

**解决：**
- 检查网络连接
- 检查防火墙设置
- 尝试使用 VPN

## 下一步

1. **配置 S3-compatible API**（如果 REST API 权限不足）
2. **运行完整测试**：`uv run python test_local_r2_upload.py`
3. **验证上传的文件**：访问返回的 R2 URL
