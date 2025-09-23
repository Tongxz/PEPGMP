#!/bin/bash
#
# 终极Ubuntu生产环境模拟自动化安装脚本 (V3 - 带自动驱动安装)
#
# 警告: 本脚本会尝试自动安装NVIDIA驱动，这属于高风险操作。
#       在生产服务器上使用前，请务必了解其风险。
#
set -e

# --- 配置变量 ---
ALIYUN_MIRROR="https://5gmxobzm.mirror.aliyuncs.com"
PUBLIC_MIRRORS='"https://docker.mirrors.ustc.edu.cn", "https://hub-mirror.c.163.com"'

# --- 日志函数 ---
log_info() { echo -e "\033[0;34m[INFO] $1\033[0m"; }
log_success() { echo -e "\033[0;32m[SUCCESS] $1\033[0m"; }
log_error() { echo -e "\033[0;31m[ERROR] $1\033[0m"; }
log_warning() { echo -e "\033[1;33m[WARNING] $1\033[0m"; }

# --- 主流程开始 ---
log_info "=== 开始配置Ubuntu生产模拟环境 (V3) ==="

# --- 步骤 0: 基础环境和驱动检查/安装 ---
log_info "步骤 0/5: 检查基础环境和NVIDIA驱动..."

# 检查并安装基础工具
sudo apt-get update
sudo apt-get install -y curl gpg sudo ubuntu-drivers-common

# 检查NVIDIA驱动
if ! command -v nvidia-smi &> /dev/null; then
    log_warning "NVIDIA驱动未安装。本脚本将尝试自动安装。"
    log_warning "这是一个高风险操作，可能会与现有内核或图形界面冲突。"
    read -p "是否继续自动安装驱动? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "用户取消操作。请手动安装驱动后重试。"
        exit 1
    fi

    log_info "正在添加PPA源并自动安装推荐驱动..."
    sudo add-apt-repository ppa:graphics-drivers/ppa -y
    sudo apt-get update
    sudo ubuntu-drivers autoinstall

    log_error "------------------------------------------------------------------"
    log_error "驱动安装程序已运行完毕。您现在必须重启计算机！"
    log_error "请运行 'sudo reboot' 命令，重启后再次运行本脚本以完成后续步骤。"
    log_error "------------------------------------------------------------------"
    exit 1
else
    log_success "NVIDIA驱动已安装。"
fi

# --- 步骤 1: 安装Docker ---
if command -v docker &> /dev/null; then
    log_success "步骤 1/5: Docker 已安装，版本: $(docker --version)"
else
    log_info "步骤 1/5: 未检测到 Docker，开始安装..."
    sudo apt-get remove -y docker docker-engine docker.io containerd runc > /dev/null 2>&1 || true
    sudo apt-get install -y ca-certificates

    DOCKER_SOURCE_URL="https://mirrors.aliyun.com/docker-ce"
    log_info "尝试使用阿里云源..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL ${DOCKER_SOURCE_URL}/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] ${DOCKER_SOURCE_URL}/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update
    if ! sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin; then
        log_error "使用国内源安装Docker失败，回退到官方源..."
        DOCKER_SOURCE_URL="https://download.docker.com"
        curl -fsSL ${DOCKER_SOURCE_URL}/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] ${DOCKER_SOURCE_URL}/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
    fi
    sudo usermod -aG docker $USER
    log_success "Docker Engine 安装完成。请关闭并重新打开终端，然后再次运行此脚本，以使用户组生效。"
    exit 0
fi

# --- 步骤 2: 安装Docker Compose ---
if ! command -v docker-compose &> /dev/null; then
    log_info "步骤 2/5: 安装独立的 Docker Compose (用于兼容)..."
    COMPOSE_VERSION="1.29.2"
    COMPOSE_URL="https://mirrors.aliyun.com/docker-toolbox/linux/compose/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)"
    if ! sudo curl -L "$COMPOSE_URL" -o /usr/local/bin/docker-compose; then
        log_error "从阿里云下载Docker Compose失败，尝试从GitHub官方源下载..."
        COMPOSE_URL="https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)"
        sudo curl -L "$COMPOSE_URL" -o /usr/local/bin/docker-compose
    fi
    sudo chmod +x /usr/local/bin/docker-compose
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    log_success "独立的 Docker Compose 安装完成。"
else
    log_success "步骤 2/5: Docker Compose 已存在。"
fi

# --- 步骤 3: 安装NVIDIA Container Toolkit ---
if dpkg -l | grep -q nvidia-container-toolkit; then
    log_success "步骤 3/5: NVIDIA Container Toolkit 已安装。"
else
    log_info "步骤 3/5: 安装 NVIDIA Container Toolkit..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    log_success "NVIDIA Container Toolkit 安装完成。"
fi

# --- 步骤 4: 配置并重启Docker ---
log_info "步骤 4/5: 配置Docker守护进程并重启..."
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    },
    "registry-mirrors": [
        "$ALIYUN_MIRROR",
        $PUBLIC_MIRRORS
    ]
}
EOF
log_success "Docker配置文件 (/etc/docker/daemon.json) 创建/更新成功。"

sudo systemctl restart docker
log_success "Docker服务已重启。"

# --- 步骤 5: 最终验证 ---
log_info "步骤 5/5: 运行最终GPU验证容器..."
docker run --rm --gpus all nvidia/cuda:12.1.0-devel-ubuntu22.04 nvidia-smi

log_success "======================================================"
log_success "🎉 终极环境搭建脚本执行完毕！🎉"
log_success "======================================================"
log_info "您的环境已准备就绪，可以部署项目了。"
