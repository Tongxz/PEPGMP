#!/bin/bash
#
# 终极 Ubuntu 生产环境部署脚本
# V6.3 - Docker Compose V2 + 健壮配置写入 + NVIDIA Toolkit 镜像源 fallback
#
set -e

# --- 日志函数 ---
log_info()    { echo -e "\033[0;34m[INFO] $1\033[0m"; }
log_success() { echo -e "\033[0;32m[SUCCESS] $1\033[0m"; }
log_error()   { echo -e "\033[0;31m[ERROR] $1\033[0m"; }
log_warning() { echo -e "\033[1;33m[WARNING] $1\033[0m"; }

log_info "=== 开始配置 Ubuntu 生产模拟环境 (V6.3) ==="

# --- 步骤 0: 基础环境和驱动检查 ---
log_info "步骤 0/5: 检查基础环境和 NVIDIA 驱动..."
sudo apt-get update
sudo apt-get install -y curl gpg sudo ubuntu-drivers-common

if ! command -v nvidia-smi &> /dev/null; then
    log_warning "NVIDIA 驱动未安装。将尝试自动安装。"
    read -p "是否继续自动安装驱动? (y/N): " -n 1 -r; echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "用户取消操作。请手动安装驱动后重试。"; exit 1;
    fi
    sudo add-apt-repository ppa:graphics-drivers/ppa -y
    sudo apt-get update
    sudo ubuntu-drivers autoinstall
    log_error "驱动已安装，请执行 'sudo reboot' 后再次运行脚本。"; exit 1;
else
    log_success "NVIDIA 驱动已安装。"
fi

# --- 步骤 1: 健壮安装 Docker ---
if ! systemctl list-units --type=service | grep -q 'docker.service'; then
    log_info "步骤 1/5: 未检测到 Docker，开始安装..."
    sudo apt-get remove -y docker docker-engine docker.io containerd runc > /dev/null 2>&1 || true
    sudo apt-get install -y ca-certificates

    DOCKER_SOURCE_URL="https://mirrors.aliyun.com/docker-ce"
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL ${DOCKER_SOURCE_URL}/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] ${DOCKER_SOURCE_URL}/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
    sudo usermod -aG docker $USER
    log_success "Docker 安装完成。"
else
    log_success "步骤 1/5: 检测到 Docker 已存在。"
fi

# --- 步骤 2: Docker Compose V2 ---
if ! docker compose version &> /dev/null; then
    log_info "步骤 2/5: 安装 Docker Compose V2..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
    if docker compose version &> /dev/null; then
        log_success "Docker Compose V2 安装完成 (使用 'docker compose' 命令)。"
    else
        log_error "Docker Compose V2 安装失败，请手动检查。"
        exit 1
    fi
else
    log_success "步骤 2/5: Docker Compose V2 已存在。"
fi

# --- 步骤 3: NVIDIA Container Toolkit ---
if ! dpkg -l | grep -q nvidia-container-toolkit; then
    log_info "步骤 3/5: 安装 NVIDIA Container Toolkit..."

    # 添加 GPG 密钥
    curl -4 -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
        sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg || true

    # 尝试官方源，失败则用清华源
    if ! curl -4 -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null; then
        log_warning "官方源不可达，改用清华镜像..."
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null <<EOF
deb [arch=amd64 signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://mirrors.tuna.tsinghua.edu.cn/nvidia-container-toolkit/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable
EOF
    fi

    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    log_success "NVIDIA Container Toolkit 安装完成。"
else
    log_success "步骤 3/5: NVIDIA Container Toolkit 已存在。"
fi

# --- 步骤 4: 配置多镜像源 (健壮写入) ---
log_info "步骤 4/5: 配置 Docker 多镜像源..."
sudo mkdir -p /etc/docker

TMP_DOCKER_JSON=$(mktemp)
cat <<EOF > "$TMP_DOCKER_JSON"
{
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  },
  "registry-mirrors": [
    "https://docker.xuanyuan.me",
    "https://mirrors.aliyun.com",
    "https://mirrors.cloud.tencent.com",
    "https://mirrors.huaweicloud.com",
    "https://mirrors.ustc.edu.cn",
    "https://mirrors.tuna.tsinghua.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
EOF

if sudo cp "$TMP_DOCKER_JSON" /etc/docker/daemon.json; then
    if [[ ! -s /etc/docker/daemon.json ]]; then
        log_warning "检测到 /etc/docker/daemon.json 写入失败或为空，回退到默认配置..."
        sudo cp "$TMP_DOCKER_JSON" /etc/docker/daemon.json
    fi
else
    log_error "写入 /etc/docker/daemon.json 失败，请检查权限。"
    exit 1
fi
rm -f "$TMP_DOCKER_JSON"

sudo systemctl daemon-reexec || true
sudo systemctl restart docker
log_success "Docker 多镜像配置完成。"

# --- 步骤 5: 最终验证 ---
log_info "步骤 5/5: 拉取并运行 GPU 验证容器..."
if ! docker run --rm --gpus all nvidia/cuda:12.1.0-devel-ubuntu22.04 nvidia-smi; then
    log_error "容器拉取或运行失败，请检查镜像源或网络。"
    exit 1
fi

log_success "======================================================"
log_success "🎉 环境部署完成！(Docker Compose V2 + 健壮配置写入 + Toolkit 镜像源 fallback) 🎉"
log_success "======================================================"
log_info "请重新登录以应用 Docker 用户组更改，或运行 'newgrp docker'。"
