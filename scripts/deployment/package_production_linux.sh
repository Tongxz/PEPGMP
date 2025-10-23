#!/bin/bash
# 生产环境打包脚本（Linux兼容版本）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}生产环境打包脚本（Linux兼容版本）${NC}"
echo -e "${GREEN}========================================${NC}"

# 配置
PACKAGE_NAME="pyt_production_$(date +%Y%m%d_%H%M%S)"
PACKAGE_DIR="/tmp/${PACKAGE_NAME}"
USB_DIR="/Volumes/Untitled/imag"

echo -e "${GREEN}打包名称: ${PACKAGE_NAME}${NC}"
echo -e "${GREEN}打包目录: ${PACKAGE_DIR}${NC}"

# 创建打包目录结构
echo -e "\n${GREEN}[1/8] 创建目录结构${NC}"
mkdir -p ${PACKAGE_DIR}/{images,config,scripts,logs,output,data,models}

# 复制Docker镜像
echo -e "\n${GREEN}[2/8] 复制Docker镜像${NC}"
if [ -d "${USB_DIR}" ]; then
    cp ${USB_DIR}/pyt-api-prod.tar ${PACKAGE_DIR}/images/
    cp ${USB_DIR}/pyt-frontend-prod.tar ${PACKAGE_DIR}/images/
    echo -e "${GREEN}✅ 镜像文件已复制${NC}"
else
    echo -e "${YELLOW}⚠️  U盘目录不存在，跳过镜像复制${NC}"
fi

# 复制Docker Compose配置
echo -e "\n${GREEN}[3/8] 复制Docker Compose配置${NC}"
cp docker-compose.prod.yml ${PACKAGE_DIR}/
echo -e "${GREEN}✅ Docker Compose配置已复制${NC}"

# 复制配置文件（排除Mac特定文件）
echo -e "\n${GREEN}[4/8] 复制配置文件${NC}"
rsync -av --exclude='.DS_Store' --exclude='__pycache__' --exclude='*.pyc' config/ ${PACKAGE_DIR}/config/
echo -e "${GREEN}✅ 配置文件已复制${NC}"

# 复制脚本文件（排除Mac特定文件）
echo -e "\n${GREEN}[5/8] 复制脚本文件${NC}"
rsync -av --exclude='.DS_Store' --exclude='__pycache__' --exclude='*.pyc' scripts/ ${PACKAGE_DIR}/scripts/
echo -e "${GREEN}✅ 脚本文件已复制${NC}"

# 创建必要的空目录
echo -e "\n${GREEN}[6/8] 创建必要的空目录${NC}"
mkdir -p ${PACKAGE_DIR}/{logs,output,data,models}
echo -e "${GREEN}✅ 目录结构已创建${NC}"

# 创建部署说明文档
echo -e "\n${GREEN}[7/8] 创建部署说明文档${NC}"
cat > ${PACKAGE_DIR}/DEPLOYMENT.md << 'EOF'
# 生产环境部署说明

## 📦 包内容

```
pyt_production/
├── images/                    # Docker镜像文件
│   ├── pyt-api-prod.tar      # API镜像 (1.7GB)
│   └── pyt-frontend-prod.tar # 前端镜像 (21MB)
├── docker-compose.prod.yml   # Docker Compose配置
├── config/                    # 配置文件
├── scripts/                   # 脚本文件
├── logs/                      # 日志目录（运行时）
├── output/                    # 输出目录（运行时）
├── data/                      # 数据目录（运行时）
└── models/                    # 模型目录（运行时）
```

## 🚀 快速部署

### 步骤1: 解压包文件

```bash
# 使用解压脚本（推荐）
chmod +x extract_production.sh
./extract_production.sh pyt_production_*.tar.gz /opt/pyt_production

# 或手动解压
mkdir -p /opt/pyt_production
cd /opt/pyt_production
tar --warning=no-unknown-keyword -xzf pyt_production_*.tar.gz
cd pyt_production_*/
```

### 步骤2: 导入Docker镜像

```bash
# 导入API镜像
docker load -i images/pyt-api-prod.tar

# 导入前端镜像
docker load -i images/pyt-frontend-prod.tar

# 验证镜像
docker images | grep pyt
```

### 步骤3: 启动服务

```bash
# 赋予执行权限
chmod +x scripts/deployment/start_production.sh

# 启动服务
./scripts/deployment/start_production.sh
```

## 🔧 管理命令

### 查看服务状态
```bash
docker-compose -f docker-compose.prod.yml ps
```

### 查看日志
```bash
docker-compose -f docker-compose.prod.yml logs -f api
```

### 重启服务
```bash
docker-compose -f docker-compose.prod.yml restart
```

### 停止服务
```bash
docker-compose -f docker-compose.prod.yml down
```

EOF
echo -e "${GREEN}✅ 部署说明文档已创建${NC}"

# 创建README
echo -e "\n${GREEN}[8/8] 创建README${NC}"
cat > ${PACKAGE_DIR}/README.md << 'EOF'
# 生产环境部署包

## 📦 快速开始

```bash
# 1. 解压包文件（推荐使用解压脚本）
chmod +x extract_production.sh
./extract_production.sh pyt_production_*.tar.gz /opt/pyt_production

# 2. 进入目录
cd /opt/pyt_production/pyt_production_*/

# 3. 导入镜像
docker load -i images/pyt-api-prod.tar
docker load -i images/pyt-frontend-prod.tar

# 4. 启动服务
chmod +x scripts/deployment/start_production.sh
./scripts/deployment/start_production.sh
```

## 📋 目录结构

```
pyt_production/
├── images/                    # Docker镜像
├── docker-compose.prod.yml   # Docker配置
├── config/                    # 配置文件
├── scripts/                   # 脚本文件
├── logs/                      # 日志目录
├── output/                    # 输出目录
├── data/                      # 数据目录
└── models/                    # 模型目录
```

## 🚀 访问地址

- API: http://localhost:8000
- 前端: http://localhost:8080
- 健康检查: http://localhost:8000/health

## 📖 详细文档

请查看 `DEPLOYMENT.md` 文件获取完整的部署说明。
EOF
echo -e "${GREEN}✅ README已创建${NC}"

# 复制解压脚本
echo -e "\n${GREEN}复制解压脚本${NC}"
cp scripts/deployment/extract_production.sh ${PACKAGE_DIR}/
chmod +x ${PACKAGE_DIR}/extract_production.sh
echo -e "${GREEN}✅ 解压脚本已复制${NC}"

# 打包（使用--no-xattrs排除扩展属性）
echo -e "\n${GREEN}开始打包（Linux兼容模式）...${NC}"
cd /tmp
tar --no-xattrs -czf ${PACKAGE_NAME}.tar.gz ${PACKAGE_NAME}/

# 复制到U盘
echo -e "\n${GREEN}复制到U盘...${NC}"
if [ -d "${USB_DIR}" ]; then
    cp ${PACKAGE_NAME}.tar.gz ${USB_DIR}/
    echo -e "${GREEN}✅ 已复制到U盘: ${USB_DIR}/${PACKAGE_NAME}.tar.gz${NC}"
else
    echo -e "${YELLOW}⚠️  U盘目录不存在，跳过复制${NC}"
fi

# 完成
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 打包完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}打包文件: /tmp/${PACKAGE_NAME}.tar.gz${NC}"
echo -e "${GREEN}包大小: $(du -sh /tmp/${PACKAGE_NAME}.tar.gz | awk '{print $1}')${NC}"
echo -e "${GREEN}========================================${NC}"

# 清理临时目录
echo -e "\n${GREEN}清理临时目录...${NC}"
rm -rf ${PACKAGE_DIR}
echo -e "${GREEN}✅ 清理完成${NC}"

echo -e "\n${YELLOW}下一步:${NC}"
echo -e "${YELLOW}1. 将U盘带到生产服务器${NC}"
echo -e "${YELLOW}2. 使用解压脚本解压: ./extract_production.sh pyt_production_*.tar.gz /opt/pyt_production${NC}"
echo -e "${YELLOW}3. 按照DEPLOYMENT.md中的说明部署${NC}"
