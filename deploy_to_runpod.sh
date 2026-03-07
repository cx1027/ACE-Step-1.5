#!/bin/bash
# =============================================================================
# RunPod 部署脚本
# =============================================================================
# 
# 自动化部署流程：
#   1. 合并 runpod 分支到 main
#   2. 构建 Docker 镜像
#   3. 推送镜像到容器注册表
#
# 使用方法:
#   ./deploy_to_runpod.sh [选项]
#
# 选项:
#   --registry <registry>    容器注册表 (dockerhub|runpod) [默认: dockerhub]
#   --username <username>   Docker Hub 用户名 (必需，如果使用 dockerhub)
#   --tag <tag>             镜像标签 [默认: latest]
#   --skip-merge            跳过合并分支步骤
#   --skip-build            跳过构建步骤
#   --skip-push             跳过推送步骤
#   --help                  显示帮助信息
#
# 示例:
#   ./deploy_to_runpod.sh --username myuser --tag v1.5.0
#   ./deploy_to_runpod.sh --registry runpod --tag latest
#
# =============================================================================

set -e  # 遇到错误立即退出

# 默认配置
REGISTRY="dockerhub"
USERNAME=""
TAG="latest"
SKIP_MERGE=false
SKIP_BUILD=false
SKIP_PUSH=false
IMAGE_NAME="acestep-runpod"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
RunPod 部署脚本

使用方法:
    ./deploy_to_runpod.sh [选项]

选项:
    --registry <registry>    容器注册表 (dockerhub|runpod) [默认: dockerhub]
    --username <username>   Docker Hub 用户名 (必需，如果使用 dockerhub)
    --tag <tag>             镜像标签 [默认: latest]
    --skip-merge            跳过合并分支步骤
    --skip-build            跳过构建步骤
    --skip-push             跳过推送步骤
    --help                  显示帮助信息

示例:
    ./deploy_to_runpod.sh --username myuser --tag v1.5.0
    ./deploy_to_runpod.sh --registry runpod --tag latest
EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --username)
            USERNAME="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --skip-merge)
            SKIP_MERGE=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-push)
            SKIP_PUSH=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 验证参数
if [[ "$REGISTRY" == "dockerhub" && -z "$USERNAME" ]]; then
    print_error "使用 Docker Hub 时必须提供 --username 参数"
    exit 1
fi

# 检查是否在正确的目录
if [[ ! -f "Dockerfile" ]]; then
    print_error "未找到 Dockerfile，请确保在项目根目录运行此脚本"
    exit 1
fi

# 步骤 1: 合并分支
if [[ "$SKIP_MERGE" == false ]]; then
    print_info "步骤 1/3: 合并 runpod 分支到 main..."
    
    # 检查当前分支
    CURRENT_BRANCH=$(git branch --show-current)
    print_info "当前分支: $CURRENT_BRANCH"
    
    # 检查是否有未提交的更改
    if [[ -n $(git status -s) ]]; then
        print_warn "检测到未提交的更改"
        read -p "是否继续？(y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "已取消"
            exit 0
        fi
    fi
    
    # 切换到 main 分支
    print_info "切换到 main 分支..."
    git checkout main || {
        print_error "无法切换到 main 分支"
        exit 1
    }
    
    # 拉取最新代码
    print_info "拉取最新的 main 分支..."
    git pull origin main || print_warn "拉取失败，继续..."
    
    # 合并 runpod 分支
    print_info "合并 runpod 分支..."
    if git merge runpod --no-edit; then
        print_info "合并成功"
    else
        print_error "合并失败，请手动解决冲突后重试"
        exit 1
    fi
    
    # 推送到远程
    read -p "是否推送到远程仓库？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin main || {
            print_error "推送失败"
            exit 1
        }
        print_info "已推送到远程仓库"
    else
        print_warn "跳过推送，请稍后手动推送"
    fi
else
    print_info "跳过合并分支步骤"
fi

# 步骤 2: 构建 Docker 镜像
if [[ "$SKIP_BUILD" == false ]]; then
    print_info "步骤 2/3: 构建 Docker 镜像..."
    
    FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"
    print_info "镜像名称: $FULL_IMAGE_NAME"
    
    # 检查 Docker 是否运行
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker 未运行，请启动 Docker 后重试"
        exit 1
    fi
    
    # 构建镜像
    print_info "开始构建（这可能需要 15-30 分钟）..."
    if docker build -t "$FULL_IMAGE_NAME" .; then
        print_info "构建成功！"
    else
        print_error "构建失败"
        exit 1
    fi
else
    print_info "跳过构建步骤"
    FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"
fi

# 步骤 3: 推送镜像
if [[ "$SKIP_PUSH" == false ]]; then
    print_info "步骤 3/3: 推送镜像到容器注册表..."
    
    # 确定推送目标
    if [[ "$REGISTRY" == "dockerhub" ]]; then
        PUSH_TARGET="${USERNAME}/${IMAGE_NAME}:${TAG}"
        print_info "目标: Docker Hub - $PUSH_TARGET"
        
        # 检查是否已登录
        if ! docker info | grep -q "Username"; then
            print_warn "未检测到 Docker Hub 登录状态"
            print_info "请先运行: docker login"
            read -p "是否现在登录？(y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker login || {
                    print_error "登录失败"
                    exit 1
                }
            else
                print_error "需要登录才能推送"
                exit 1
            fi
        fi
        
        # 标记镜像
        print_info "标记镜像..."
        docker tag "$FULL_IMAGE_NAME" "$PUSH_TARGET" || {
            print_error "标记失败"
            exit 1
        }
        
        # 推送镜像
        print_info "推送镜像（这可能需要 10-30 分钟）..."
        if docker push "$PUSH_TARGET"; then
            print_info "推送成功！"
            print_info "镜像地址: docker.io/$PUSH_TARGET"
        else
            print_error "推送失败"
            exit 1
        fi
        
    elif [[ "$REGISTRY" == "runpod" ]]; then
        print_warn "RunPod Registry 需要手动配置"
        print_info "请参考 DEPLOY_TO_RUNPOD.md 中的说明"
        print_info "本地镜像: $FULL_IMAGE_NAME"
        exit 0
    else
        print_error "不支持的注册表: $REGISTRY"
        exit 1
    fi
else
    print_info "跳过推送步骤"
    if [[ "$REGISTRY" == "dockerhub" ]]; then
        PUSH_TARGET="${USERNAME}/${IMAGE_NAME}:${TAG}"
    else
        PUSH_TARGET="$FULL_IMAGE_NAME"
    fi
fi

# 完成
echo
print_info "=========================================="
print_info "部署完成！"
print_info "=========================================="
print_info "镜像: $PUSH_TARGET"
print_info ""
print_info "下一步:"
print_info "1. 登录 RunPod 控制台"
print_info "2. 创建或更新 Serverless Endpoint"
print_info "3. 设置 Container Image: $PUSH_TARGET"
print_info "4. 设置 Handler Path: runpod_handler.py"
print_info "5. 配置环境变量（参考 RUNPOD_DEPLOYMENT.md）"
print_info ""
print_info "详细说明请查看: DEPLOY_TO_RUNPOD.md"
echo
