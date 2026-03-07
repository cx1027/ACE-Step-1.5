# RunPod 部署完整指南

本指南将帮助你完成从代码到 RunPod Serverless 的完整部署流程。

## 部署流程概览

1. ✅ **合并代码到 main 分支**
2. ✅ **构建 Docker 镜像**
3. ✅ **推送镜像到容器注册表**
4. ✅ **在 RunPod 控制台创建/更新 Endpoint**
5. ✅ **配置环境变量**

---

## 步骤 1: 合并 runpod 分支到 main

### 1.1 确保代码已提交

```bash
# 检查当前分支状态
git status

# 如果有未提交的更改，先提交
git add .
git commit -m "feat: add async support for RunPod serverless with concurrency"
```

### 1.2 切换到 main 分支并合并

```bash
# 切换到 main 分支
git checkout main

# 拉取最新的 main 分支代码
git pull origin main

# 合并 runpod 分支
git merge runpod

# 如果有冲突，解决冲突后：
git add .
git commit -m "merge: merge runpod branch into main"

# 推送到远程仓库
git push origin main
```

---

## 步骤 2: 构建 Docker 镜像

### 2.1 准备构建环境

确保你在项目根目录（包含 `Dockerfile` 的目录）：

```bash
cd /Users/xiu/Documents/LLMApp/ACE-Step-1.5
```

### 2.2 构建镜像

```bash
# 构建 Docker 镜像（使用项目名称和版本标签）
docker build -t acestep-runpod:latest .

# 或者使用更具体的标签（推荐）
docker build -t acestep-runpod:v1.5.0 .
```

**构建时间**: 首次构建可能需要 15-30 分钟，因为需要下载和安装所有依赖。

**注意**: 
- 确保 Docker 有足够的磁盘空间（建议至少 20GB）
- 如果构建失败，检查网络连接和 Docker 资源限制

---

## 步骤 3: 推送镜像到容器注册表

RunPod 支持多种容器注册表。选择其中一种：

### 选项 A: Docker Hub（推荐，最简单）

#### 3.1 登录 Docker Hub

```bash
docker login
# 输入你的 Docker Hub 用户名和密码
```

#### 3.2 标记镜像

```bash
# 格式: docker tag <本地镜像名> <DockerHub用户名>/<镜像名>:<标签>
docker tag acestep-runpod:latest <你的DockerHub用户名>/acestep-runpod:latest

# 例如：
# docker tag acestep-runpod:latest username/acestep-runpod:latest
```

#### 3.3 推送镜像

```bash
docker push <你的DockerHub用户名>/acestep-runpod:latest
```

**推送时间**: 根据镜像大小（通常 5-10GB），可能需要 10-30 分钟。

### 选项 B: RunPod Container Registry

RunPod 也提供自己的容器注册表，通常更快且更安全。

#### 3.1 获取 RunPod Registry 凭证

1. 登录 RunPod 控制台
2. 进入 **Settings** → **Container Registry**
3. 获取你的 Registry URL 和认证信息

#### 3.2 登录 RunPod Registry

```bash
docker login <runpod-registry-url>
# 输入 RunPod 提供的用户名和密码/API token
```

#### 3.3 标记并推送

```bash
# 标记镜像
docker tag acestep-runpod:latest <runpod-registry-url>/acestep-runpod:latest

# 推送
docker push <runpod-registry-url>/acestep-runpod:latest
```

### 选项 C: 其他注册表（GitHub Container Registry, AWS ECR 等）

根据你使用的注册表，按照相应的文档进行认证和推送。

---

## 步骤 4: 在 RunPod 控制台创建/更新 Endpoint

### 4.1 创建新的 Serverless Endpoint

1. 登录 [RunPod 控制台](https://www.runpod.io/)
2. 导航到 **Serverless** → **Endpoints** → **Create Endpoint**

### 4.2 配置 Endpoint

填写以下信息：

- **Endpoint Name**: `acestep-music-generator`（或你喜欢的名称）
- **Container Image**: 
  - Docker Hub: `<你的用户名>/acestep-runpod:latest`
  - RunPod Registry: `<runpod-registry-url>/acestep-runpod:latest`
- **Handler Path**: `runpod_handler.py`
- **Container Disk**: 建议至少 `20GB`（用于模型和临时文件）
- **GPU Type**: 根据你的需求选择（推荐 `RTX 4090` 或 `A100`）
- **Min Workers**: `0`（允许空闲时关闭，节省成本）
- **Max Workers**: 根据需求设置（例如 `5`）
- **Concurrency**: 每个 worker 的并发数（已在代码中通过 `RUNPOD_MAX_CONCURRENCY` 环境变量控制，默认 `2`）

### 4.3 配置环境变量

在 Endpoint 设置中找到 **Environment Variables** 部分，添加以下变量：

#### 必需变量（R2 配置）

```
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY=your-r2-access-key-id
R2_SECRET_KEY=your-r2-secret-access-key
R2_BUCKET_NAME=your-bucket-name
R2_PUBLIC_URL=https://your-public-domain.com
```

#### 可选变量（ACE-Step 配置）

```
ACESTEP_CONFIG_PATH=acestep-v15-turbo
ACESTEP_DEVICE=auto
ACESTEP_USE_FLASH_ATTENTION=true
ACESTEP_COMPILE_MODEL=false
ACESTEP_OFFLOAD_TO_CPU=false
ACESTEP_OFFLOAD_DIT_TO_CPU=false
ACESTEP_LM_MODEL_PATH=acestep-5Hz-lm-0.6B
ACESTEP_LM_BACKEND=vllm
ACESTEP_LM_OFFLOAD_TO_CPU=false
RUNPOD_MAX_CONCURRENCY=2
```

**注意**: 
- 敏感信息（如 R2 密钥）应该通过 RunPod 的环境变量设置，而不是打包在 Docker 镜像中
- 所有变量名称都是大小写敏感的

### 4.4 保存并部署

点击 **Save** 或 **Deploy** 按钮，RunPod 将开始部署你的 Endpoint。

**首次部署时间**: 可能需要 5-10 分钟来拉取镜像和初始化。

---

## 步骤 5: 测试部署

### 5.1 在 RunPod 控制台测试

1. 进入你的 Endpoint 页面
2. 点击 **Test** 或 **Send Request**
3. 使用以下测试输入：

```json
{
  "input": {
    "prompt": "generate a song for rain within 30 secs",
    "duration": 30
  }
}
```

### 5.2 检查日志

在 Endpoint 页面查看 **Logs**，确认：
- ✅ 镜像成功拉取
- ✅ 依赖正确安装
- ✅ 模型成功加载
- ✅ 请求成功处理

### 5.3 验证输出

如果一切正常，你应该收到类似以下的响应：

```json
{
  "output_url": "https://your-public-domain.com/songs/uuid.mp3",
  "status": "success",
  "mode": null
}
```

---

## 常见问题排查

### 问题 1: 镜像构建失败

**可能原因**:
- 网络连接问题
- Docker 资源不足
- Dockerfile 语法错误

**解决方案**:
```bash
# 检查 Docker 状态
docker info

# 清理 Docker 缓存
docker system prune -a

# 重新构建（使用 --no-cache 强制重新构建）
docker build --no-cache -t acestep-runpod:latest .
```

### 问题 2: 推送镜像失败

**可能原因**:
- 未登录容器注册表
- 镜像名称格式错误
- 网络问题

**解决方案**:
```bash
# 确认已登录
docker login

# 检查镜像标签
docker images | grep acestep-runpod

# 使用正确的格式重新标记
docker tag acestep-runpod:latest <registry>/acestep-runpod:latest
```

### 问题 3: Endpoint 启动失败

**可能原因**:
- 镜像路径错误
- 环境变量缺失
- 资源不足

**解决方案**:
1. 检查镜像路径是否正确
2. 确认所有必需的环境变量都已设置
3. 检查 RunPod 日志中的具体错误信息
4. 尝试增加 Container Disk 大小

### 问题 4: 请求超时或失败

**可能原因**:
- 模型加载时间过长
- GPU 内存不足
- 网络问题

**解决方案**:
1. 检查 GPU 类型是否足够（建议至少 24GB VRAM）
2. 考虑使用更小的模型（如 `acestep-5Hz-lm-0.6B`）
3. 增加 Endpoint 的 timeout 设置
4. 检查 R2 配置是否正确

---

## 更新部署

当你需要更新代码时：

1. **修改代码并提交**
   ```bash
   git add .
   git commit -m "fix: update handler logic"
   git push
   ```

2. **重新构建镜像**（使用新标签）
   ```bash
   docker build -t acestep-runpod:v1.5.1 .
   docker tag acestep-runpod:v1.5.1 <registry>/acestep-runpod:v1.5.1
   docker push <registry>/acestep-runpod:v1.5.1
   ```

3. **在 RunPod 控制台更新 Endpoint**
   - 进入 Endpoint 设置
   - 更新 **Container Image** 为新标签
   - 保存更改（RunPod 会自动重新部署）

---

## 成本优化建议

1. **使用 `min_worker=0`**: 允许空闲时关闭 worker，节省成本
2. **合理设置并发**: 通过 `RUNPOD_MAX_CONCURRENCY` 控制每个 worker 的并发数
3. **选择合适的 GPU**: 根据实际需求选择 GPU 类型，避免过度配置
4. **监控使用情况**: 定期查看 RunPod 的使用报告，优化配置

---

## 相关文档

- [RUNPOD_DEPLOYMENT.md](./RUNPOD_DEPLOYMENT.md) - 详细的部署和环境变量配置
- [Dockerfile](./Dockerfile) - Docker 镜像构建配置
- [runpod_handler.py](./runpod_handler.py) - RunPod Serverless 处理器

---

## 快速参考命令

```bash
# 1. 合并分支
git checkout main && git merge runpod && git push origin main

# 2. 构建镜像
docker build -t acestep-runpod:latest .

# 3. 标记镜像（Docker Hub）
docker tag acestep-runpod:latest <username>/acestep-runpod:latest

# 4. 推送镜像
docker push <username>/acestep-runpod:latest

# 5. 在 RunPod 控制台配置 Endpoint 和环境变量
```

---

**部署完成后，你的 ACE-Step 音乐生成服务就可以通过 RunPod Serverless 访问了！** 🎵
