# R2 配置修复指南

## 问题说明

你的 curl 命令使用的是 **Cloudflare API Token**（Bearer token），但 R2 的 S3 兼容 API 需要的是 **R2 API Token**（Access Key ID + Secret Access Key）。这是两种不同的认证方式。

## 两种认证方式的区别

### 1. Cloudflare API Token（你当前拥有的）
- **用途**: 访问 Cloudflare API（如验证 token、管理账户等）
- **格式**: Bearer token（如 `your-cloudflare-api-token-bearer-token`）
- **你的 curl 命令**: ✅ 工作正常
  ```bash
  curl "https://api.cloudflare.com/client/v4/accounts/your-account-id/tokens/verify" \
    -H "Authorization: Bearer your-cloudflare-api-token-bearer-token"
  ```

### 2. R2 API Token（你需要的）
- **用途**: 访问 R2 存储（S3 兼容 API）
- **格式**: Access Key ID + Secret Access Key（类似 AWS S3）
- **你的 .env 需要**: 
  ```
  R2_ACCESS_KEY=<access-key-id>
  R2_SECRET_KEY=<secret-access-key>
  ```

## 获取 R2 API Token 的步骤

### 方法 1: 通过 Cloudflare Dashboard（推荐）

1. **登录 Cloudflare Dashboard**
   - 访问: https://dash.cloudflare.com/
   - 使用你的账户登录

2. **导航到 R2**
   - 在左侧菜单找到 **R2**
   - 点击进入 R2 页面

3. **管理 R2 API Tokens**
   - 点击 **Manage R2 API Tokens**（通常在页面顶部或设置中）
   - 或者直接访问: https://dash.cloudflare.com/[your-account-id]/r2/api-tokens

4. **创建新的 API Token**
   - 点击 **Create API Token**
   - 填写信息:
     - **Name**: `ACE-Step-R2-Token`（或任何你喜欢的名称）
     - **Permissions**: 选择 `Object Read` 和 `Object Write`
     - **Buckets**: 
       - 选择 `All buckets`（推荐），或
       - 选择特定 bucket `music-outputs`

5. **复制凭证**
   - 创建后，你会看到：
     - **Access Key ID**: 类似 `your-r2-access-key-id`
     - **Secret Access Key**: 类似 `abc123def456...`（**重要：只显示一次！**）
   - ⚠️ **立即复制 Secret Access Key**，关闭页面后无法再次查看

### 方法 2: 使用提供的脚本

运行交互式脚本：

```bash
bash update_r2_config.sh
```

脚本会提示你输入：
- R2 Access Key ID
- R2 Secret Access Key
- Bucket Name（默认: `music-outputs`）
- Public URL（可选）

## 更新 .env 文件

### 手动更新

编辑 `.env` 文件，确保包含以下配置：

```bash
# R2 Configuration
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY=<你的-R2-Access-Key-ID>
R2_SECRET_KEY=<你的-R2-Secret-Access-Key>
R2_BUCKET_NAME=music-outputs
R2_PUBLIC_URL=<你的公共域名，如果有>
```

**重要提示**:
- 确保没有多余的空格或引号
- `R2_SECRET_KEY` 不要包含换行符
- 如果值包含特殊字符，可能需要转义

### 使用脚本自动更新

```bash
bash update_r2_config.sh
```

## 验证配置

更新后，运行测试脚本验证配置：

```bash
# 使用 bash 脚本测试
bash test_r2_curl.sh

# 或使用 Python 脚本测试（需要 boto3）
python3 test_r2_config.py
```

如果测试成功，你会看到：
```
✓ Successfully connected!
✓ Bucket 'music-outputs' exists
✓ Successfully accessed bucket 'music-outputs'
✓ All R2 configuration tests passed!
```

## 常见问题

### Q: 为什么我的 Cloudflare API Token 不能直接用于 R2？

A: Cloudflare API Token 用于 Cloudflare API，而 R2 使用 S3 兼容的 API，需要不同的认证方式（Access Key ID + Secret Access Key）。

### Q: 我忘记了 Secret Access Key 怎么办？

A: Secret Access Key 只在创建时显示一次。如果忘记了，你需要：
1. 删除旧的 R2 API Token
2. 创建新的 R2 API Token
3. 更新 `.env` 文件中的 `R2_SECRET_KEY`

### Q: 如何检查 R2 API Token 的权限？

A: 在 Cloudflare Dashboard → R2 → Manage R2 API Tokens 中查看 token 的权限设置。

### Q: 测试时出现 "Unauthorized" 错误？

可能的原因：
1. `R2_ACCESS_KEY` 或 `R2_SECRET_KEY` 不正确
2. Token 没有正确的权限（需要 Object Read & Write）
3. Token 没有访问目标 bucket 的权限
4. `.env` 文件中的值有空格或格式问题

**解决方法**:
- 检查 `.env` 文件中的值是否正确
- 在 Cloudflare Dashboard 中验证 token 权限
- 重新创建 R2 API Token

## 相关文件

- `test_r2_config.py` - Python 测试脚本
- `test_r2_curl.sh` - Bash 测试脚本
- `update_r2_config.sh` - 交互式配置更新脚本
- `fix_r2_with_curl.sh` - 尝试通过 API 创建 token（可能不可用）

## 下一步

配置完成后，你可以：
1. 运行 `local_run.py` 测试音乐生成和上传
2. 部署到 RunPod 服务器
3. 验证生成的文件是否正确上传到 R2
