# R2 配置测试指南

本文档提供多种方法来测试 `.env` 文件中的 R2 配置。

## 方法 1: 使用 Python 测试脚本（推荐）

最简单的方法是使用提供的 Python 测试脚本：

```bash
# 使用 uv 运行（推荐）
uv run python test_r2_config.py

# 或直接使用 python（如果已安装依赖）
python3 test_r2_config.py
```

这个脚本会：
- 加载 `.env` 文件中的 R2 配置
- 测试连接和认证
- 验证 bucket 是否存在和可访问
- 显示详细的错误信息

## 方法 2: 使用 AWS CLI（最简单）

如果你已经安装了 AWS CLI，可以直接使用：

```bash
# 加载 .env 文件
export $(grep -v '^#' .env | xargs)

# 测试连接（列出所有 buckets）
aws s3 ls --endpoint-url "$R2_ENDPOINT" \
  --profile default \
  --region auto

# 或者直接设置环境变量
export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$R2_SECRET_KEY"
export AWS_DEFAULT_REGION="auto"

aws s3 ls --endpoint-url "$R2_ENDPOINT"

# 测试特定 bucket
aws s3 ls "s3://$R2_BUCKET_NAME" --endpoint-url "$R2_ENDPOINT"
```

## 方法 3: 使用 curl（需要手动签名）

R2 使用 S3 兼容的 API，需要 AWS Signature Version 4 签名。手动构造 curl 命令比较复杂，但可以使用以下方法：

### 3.1 使用 Python 生成带签名的 curl 命令

```bash
# 运行测试脚本
bash test_r2_curl.sh
```

这个脚本会自动生成带签名的 curl 命令。

### 3.2 手动使用 curl 测试（简单连接测试）

```bash
# 加载 .env
export $(grep -v '^#' .env | xargs)

# 提取 endpoint host
ENDPOINT_HOST=$(echo "$R2_ENDPOINT" | sed -E 's|https?://([^/]+).*|\1|')

# 简单测试 endpoint 是否可达（会返回 403/401，但说明连接正常）
curl -v "https://$ENDPOINT_HOST"
```

注意：这个方法只能测试 endpoint 是否可达，不能测试认证。

### 3.3 使用 awscurl（第三方工具）

安装 `awscurl`：

```bash
pip install awscurl
```

然后使用：

```bash
export $(grep -v '^#' .env | xargs)

awscurl --service s3 \
  --region auto \
  --access-key "$R2_ACCESS_KEY" \
  --secret-key "$R2_SECRET_KEY" \
  "$R2_ENDPOINT/$R2_BUCKET_NAME/"
```

## 方法 4: 使用 boto3 Python 脚本

创建一个简单的测试脚本：

```python
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["R2_ENDPOINT"],
    aws_access_key_id=os.environ["R2_ACCESS_KEY"],
    aws_secret_access_key=os.environ["R2_SECRET_KEY"],
    region_name="auto",
)

# 测试列出 buckets
print("Buckets:", s3.list_buckets())

# 测试访问特定 bucket
bucket_name = os.environ["R2_BUCKET_NAME"]
s3.head_bucket(Bucket=bucket_name)
print(f"Bucket '{bucket_name}' is accessible")
```

## 常见错误和解决方案

### 错误: `InvalidAccessKeyId` 或 `SignatureDoesNotMatch`
- **原因**: R2_ACCESS_KEY 或 R2_SECRET_KEY 不正确
- **解决**: 检查 `.env` 文件中的凭证是否正确

### 错误: `Unauthorized`
- **原因**: 凭证没有权限访问 R2
- **解决**: 检查 Cloudflare R2 中的 API token 权限设置

### 错误: `404 Not Found` (bucket)
- **原因**: Bucket 不存在
- **解决**: 检查 `R2_BUCKET_NAME` 是否正确，或在 Cloudflare 控制台创建 bucket

### 错误: `403 Forbidden`
- **原因**: 凭证没有访问该 bucket 的权限
- **解决**: 检查 R2 API token 的权限设置，确保有该 bucket 的读写权限

## 快速测试命令

最简单的测试方法（如果已安装 AWS CLI）：

```bash
# 一键测试
export $(grep -v '^#' .env | xargs) && \
export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY" && \
export AWS_SECRET_ACCESS_KEY="$R2_SECRET_KEY" && \
aws s3 ls --endpoint-url "$R2_ENDPOINT"
```
