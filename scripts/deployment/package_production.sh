#!/bin/bash
# 生产环境打包脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}生产环境打包脚本${NC}"
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

# 复制配置文件
echo -e "\n${GREEN}[4/8] 复制配置文件${NC}"
cp -r config/ ${PACKAGE_DIR}/
echo -e "${GREEN}✅ 配置文件已复制${NC}"

# 复制脚本文件
echo -e "\n${GREEN}[5/8] 复制脚本文件${NC}"
cp -r scripts/ ${PACKAGE_DIR}/
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
│   ├── unified_params.yaml
│   ├── regions.json
│   ├── cameras.yaml
│   └── user_profiles/
├── scripts/                   # 脚本文件
│   ├── deployment/
│   │   └── start_production.sh
│   └── init_db.sql
├── logs/                      # 日志目录（运行时）
├── output/                    # 输出目录（运行时）
├── data/                      # 数据目录（运行时）
└── models/                    # 模型目录（运行时）
```

## 🚀 快速部署

### 步骤1: 解压包文件

```bash
# 解压到目标目录
tar -xzf pyt_production_*.tar.gz -C /path/to/

# 进入目录
cd /path/to/pyt_production_*/
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

## 📋 目录说明

### 挂载目录

| 目录 | 用途 | 说明 |
|------|------|------|
| `config/` | 配置文件 | 只读挂载 |
| `logs/` | 日志文件 | 读写挂载 |
| `output/` | 输出文件 | 读写挂载 |
| `data/` | 数据文件 | 读写挂载 |
| `models/` | 模型文件 | 读写挂载（TensorRT引擎） |

### 运行时文件

- **日志文件**: `logs/app.log`
- **输出文件**: `output/videos/`, `output/images/`
- **数据文件**: `data/detection_results.db`, `data/annotations/`
- **模型文件**: `models/yolo/*.engine`, `models/hairnet_detection/*.engine`

## 🔧 管理命令

### 查看服务状态

```bash
docker-compose -f docker-compose.prod.yml ps
```

### 查看日志

```bash
# 查看所有日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看API日志
docker-compose -f docker-compose.prod.yml logs -f api

# 查看TensorRT转换日志
docker-compose -f docker-compose.prod.yml logs -f api | grep TensorRT
```

### 重启服务

```bash
docker-compose -f docker-compose.prod.yml restart
```

### 停止服务

```bash
docker-compose -f docker-compose.prod.yml down
```

### 更新服务

```bash
# 停止服务
docker-compose -f docker-compose.prod.yml down

# 导入新镜像
docker load -i images/pyt-api-prod.tar

# 启动服务
docker-compose -f docker-compose.prod.yml up -d
```

## ⚠️ 注意事项

1. **GPU支持**: 确保GPU驱动和NVIDIA Docker Runtime已安装
2. **磁盘空间**: 确保有足够的磁盘空间（至少10GB）
3. **网络**: 确保可以访问私有镜像仓库（如果需要）
4. **权限**: 确保脚本有执行权限
5. **防火墙**: 确保端口8000和8080已开放

## 📊 性能优化

### TensorRT自动转换

首次启动时会自动转换TensorRT引擎，需要2-5分钟。

转换后的.engine文件会保存在 `models/` 目录中。

### 预期性能提升

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 推理速度 | 28.6 FPS | 166.7 FPS | 5.8倍 |
| 延迟 | 35ms | 6ms | 83%降低 |
| GPU利用率 | 30-40% | 80-90% | 2倍 |

## 🔍 故障排除

### 问题1: GPU不可用

```bash
# 检查GPU
nvidia-smi

# 检查Docker GPU支持
docker run --rm --gpus all nvidia/cuda:12.4.0-runtime-ubuntu22.04 nvidia-smi
```

### 问题2: 镜像导入失败

```bash
# 检查镜像文件
ls -lh images/

# 检查磁盘空间
df -h

# 重新导入
docker load -i images/pyt-api-prod.tar
```

### 问题3: 服务启动失败

```bash
# 查看详细日志
docker-compose -f docker-compose.prod.yml logs api

# 检查配置文件
cat config/unified_params.yaml

# 检查端口占用
netstat -tlnp | grep 8000
```

## 📞 技术支持

如有问题，请联系技术支持团队。

EOF
echo -e "${GREEN}✅ 部署说明文档已创建${NC}"

# 创建README
echo -e "\n${GREEN}[8/8] 创建README${NC}"
cat > ${PACKAGE_DIR}/README.md << 'EOF'
# 生产环境部署包

## 📦 快速开始

```bash
# 1. 解压包文件
tar -xzf pyt_production_*.tar.gz -C /path/to/

# 2. 进入目录
cd /path/to/pyt_production_*/

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

# 打包
echo -e "\n${GREEN}开始打包...${NC}"
cd /tmp
tar -czf ${PACKAGE_NAME}.tar.gz ${PACKAGE_NAME}/

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

# 显示包内容
echo -e "\n${GREEN}包内容:${NC}"
tar -tzf /tmp/${PACKAGE_NAME}.tar.gz | head -20
echo -e "${YELLOW}... (更多文件)${NC}"

# 清理临时目录
echo -e "\n${GREEN}清理临时目录...${NC}"
rm -rf ${PACKAGE_DIR}
echo -e "${GREEN}✅ 清理完成${NC}"

echo -e "\n${YELLOW}下一步:${NC}"
echo -e "${YELLOW}1. 将U盘带到生产服务器${NC}"
echo -e "${YELLOW}2. 解压包文件: tar -xzf pyt_production_*.tar.gz -C /path/to/${NC}"
echo -e "${YELLOW}3. 按照DEPLOYMENT.md中的说明部署${NC}"
