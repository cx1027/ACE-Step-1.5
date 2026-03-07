# 修复 S3 认证问题

## 当前问题

测试显示配置已加载，但出现 **Access Denied (403)** 错误。

**原因**：R2 API Token 权限不足或配置不正确。

## 解决方案

### 方法 1: 在 Cloudflare Dashboard 手动创建 R2 API Token（推荐）

1. **登录 Cloudflare Dashboard**
   - 访问: https://dash.cloudflare.com/
   - 使用你的账户登录

2. **导航到 R2**
   - 在左侧菜单找到 **R2**
   - 点击进入 R2 页面

3. **管理 R2 API Tokens**
   - 点击 **Manage R2 API Tokens**
   - 或直接访问: https://dash.cloudflare.com/[your-account-id]/r2/api-tokens

4. **创建新的 API Token**
   - 点击 **Create API Token** 或 **Create R2 API Token**
   - 填写信息:
     - **Name**: `ACE-Step-R2-Token`（或任何你喜欢的名称）
     - **Permissions**: 
       - ✅ `Object Read`
       - ✅ `Object Write`
     - **Buckets**: 
       - 选择 `All buckets`（推荐），或
       - 选择特定 bucket `music-outputs`

5. **复制凭证**
   - 创建后，你会看到：
     - **Access Key ID** (类似: `93935a9b...`)
     - **Secret Access Key** (类似: `e8165cab...`)
   - ⚠️ **重要**: Secret Access Key 只会显示一次，请立即保存！

6. **更新 .env 文件**
   
   将复制的凭证添加到 `.env` 文件：
   ```env
   R2_ENDPOINT=https://13d2f431296ab430eb63df236a1374e2.r2.cloudflarestorage.com
   R2_ACCESS_KEY=<你刚复制的 Access Key ID>
   R2_SECRET_KEY=<你刚复制的 Secret Access Key>
   R2_BUCKET_NAME=music-outputs
   R2_PUBLIC_URL=https://pub-41f5517642ad492cbae588b5671e80cb.r2.dev
   ```

### 方法 2: 更新 Cloudflare API Token 权限（用于脚本自动创建）

如果你希望使用脚本自动创建 R2 API Token，需要创建或更新 Cloudflare API Token：

1. **登录 Cloudflare Dashboard**
   - 访问: https://dash.cloudflare.com/profile/api-tokens

2. **创建新的 API Token 或编辑现有 Token**
   - 点击 **Create Token** 创建新的，或找到现有 Token 点击 **Edit**

3. **选择 Token 类型**
   - ⭐ **推荐选择: Account API Tokens**（账户级别）
     - 更安全，权限范围更小
     - 直接绑定到特定账户
     - 选择你的账户: `13d2f431296ab430eb63df236a1374e2`
   - 或者选择: **User API Tokens**（用户级别）
     - 可以访问用户有权限的所有账户
     - 权限范围更广，安全性稍低

4. **配置权限**
   - 在权限设置中，添加：
     - **Account** → **Cloudflare R2** → **Edit**
   - 如果使用 Account API Tokens，确保选择了正确的账户
   - 保存更改

5. **复制 Token**
   - 创建后复制完整的 API Token（Bearer token）
   - 添加到 `.env` 文件：
     ```env
     CLOUDFLARE_ACCOUNT_ID=13d2f431296ab430eb63df236a1374e2
     CLOUDFLARE_API_TOKEN=<你刚复制的 API Token>
     ```

6. **重新运行脚本**
   ```bash
   uv run python get_r2_credentials.py
   ```

## 验证配置

更新 `.env` 后，运行测试验证：

```bash
uv run python test_s3_auth.py
```

**期望结果**：
```
✓ Authentication successful!
✓ Found X bucket(s)
✓ Bucket 'music-outputs' exists in your account
✓ Successfully accessed bucket 'music-outputs'
✓ All authentication tests passed!
```

## 常见问题

### Q: 为什么会出现 Access Denied？

**A**: 可能的原因：
1. R2_ACCESS_KEY 或 R2_SECRET_KEY 不正确
2. R2 API Token 权限不足（需要 Object Read 和 Object Write）
3. R2 API Token 已过期或被删除

### Q: 如何检查 R2 API Token 是否正确？

**A**: 
1. 登录 Cloudflare Dashboard
2. 进入 R2 → Manage R2 API Tokens
3. 检查你的 token 是否存在
4. 如果不存在，需要创建新的 token

### Q: R2_ENDPOINT 格式是什么？

**A**: 格式为 `https://{account-id}.r2.cloudflarestorage.com`
- 你的 Account ID: `13d2f431296ab430eb63df236a1374e2`
- 所以 R2_ENDPOINT: `https://13d2f431296ab430eb63df236a1374e2.r2.cloudflarestorage.com`

### Q: 两种认证方式的区别？

**A**: 
- **Cloudflare API Token** (Bearer token): 用于访问 Cloudflare API，管理账户和创建 R2 API Token
- **R2 API Token** (Access Key + Secret Key): 用于 S3 兼容 API，上传文件到 R2

当前你使用的是 S3 兼容方式，所以需要 R2 API Token（Access Key + Secret Key）。

### Q: 应该选择 Account API Tokens 还是 User API Tokens？

**A**: **推荐选择 Account API Tokens**（账户级别）

**原因**：
1. ✅ **更安全**: 权限范围更小，只绑定到特定账户
2. ✅ **更清晰**: 直接关联到你的账户，权限明确
3. ✅ **符合最小权限原则**: 只授予必要的权限

**Account API Tokens**:
- 绑定到特定账户（如 `13d2f431296ab430eb63df236a1374e2`）
- 只能访问该账户的资源
- 创建时选择你的账户

**User API Tokens**:
- 绑定到用户，可以访问用户有权限的所有账户
- 权限范围更广
- 如果只有一个账户，两者效果相同，但 Account API Tokens 更安全

**对于你的情况**：选择 **Account API Tokens**，然后选择账户 `13d2f431296ab430eb63df236a1374e2`。

## 下一步

配置成功后，你可以：
1. 测试文件上传: `uv run python test_r2_upload_simple.py`
2. 测试完整流程: `uv run python test_local_r2_upload.py --prompt "test" --duration 10`
