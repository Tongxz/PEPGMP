# WSL2 + 1Panel 快速部署指南

## 🚀 完整部署步骤（5步）

### ✅ 步骤1: 验证镜像已导入

```bash
# 在 WSL2 Ubuntu 中
docker images | grep pepgmp

# 如果看不到镜像，需要导入：
docker load -i /mnt/c/Users/YourName/Code/PythonCode/Pyt/pepgmp-backend-20251201.tar
```

---

### ✅ 步骤2: 准备部署包（重新运行）

```bash
# 在 WSL2 Ubuntu 中运行准备脚本
bash /mnt/c/Users/YourName/Code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh

# 脚本会：
# ✓ 创建 ~/projects/Pyt 目录
# ✓ 复制 docker-compose.prod.1panel.yml
# ✓ 复制 config/ 和 models/ 目录
# ✓ 复制 generate_production_config.sh 脚本
```

**如果之前运行过**，脚本会询问是否覆盖，选择 `yes` 即可。

---

### ✅ 步骤3: 生成配置文件

```bash
cd ~/projects/Pyt

# 运行配置生成脚本
bash scripts/generate_production_config.sh

# 按提示输入：
# - API端口 [8000]: 直接回车
# - 管理员用户名 [admin]: 直接回车
# - CORS来源 [*]: 直接回车
# - 镜像标签 [latest]: 20251201  ← 重要！输入你的镜像标签
```

**脚本会自动生成**：
- `.env.production` - 完整配置文件（包含强随机密码）
- `.env.production.credentials` - 凭证文件（请保存后删除）

---

### ✅ 步骤4: 在 1Panel 中部署

1. **登录 1Panel**
   - 打开浏览器访问 1Panel
   - 使用用户名和密码登录

2. **创建 Compose 项目**
   - 进入 **"容器"** > **"Compose"**
   - 点击 **"创建"** 或 **"新建"**
   - 项目名称：`pepgmp-production`
   - 工作目录：`/home/你的用户名/projects/Pyt`
   - 选择 **"从文件创建"**，指向 `docker-compose.prod.yml`

3. **启动服务**
   - 点击 **"启动"** 或 **"部署"**
   - 等待60-70秒让服务启动

---

### ✅ 步骤5: 验证部署

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 健康检查
curl http://localhost:8000/api/v1/monitoring/health

# 查看日志
docker compose -f docker-compose.prod.yml logs -f api
```

---

## 📋 一键执行脚本

创建 `~/deploy.sh` 文件：

```bash
#!/bin/bash
# 一键部署脚本

set -e

echo "========================================================================="
echo "              开始部署流程"
echo "========================================================================="
echo ""

# 步骤1: 验证镜像
echo "步骤1: 验证镜像..."
if ! docker images | grep -q pepgmp; then
    echo "❌ 错误: 未找到 pepgmp 镜像"
    echo "请先导入镜像: docker load -i /path/to/pepgmp-backend-20251201.tar"
    exit 1
fi
echo "✓ 镜像已存在"
echo ""

# 步骤2: 准备部署包
echo "步骤2: 准备部署包..."
bash /mnt/c/Users/YourName/Code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh
echo ""

# 步骤3: 生成配置文件
echo "步骤3: 生成配置文件..."
cd ~/projects/Pyt
if [ ! -f ".env.production" ]; then
    echo "运行配置生成脚本..."
    bash scripts/generate_production_config.sh
else
    echo "✓ 配置文件已存在，跳过生成"
fi
echo ""

# 步骤4: 验证配置
echo "步骤4: 验证配置..."
docker compose -f docker-compose.prod.yml config > /dev/null
echo "✓ 配置验证通过"
echo ""

echo "========================================================================="
echo "              部署准备完成"
echo "========================================================================="
echo ""
echo "下一步："
echo "  1. 登录 1Panel"
echo "  2. 创建 Compose 项目"
echo "  3. 工作目录: ~/projects/Pyt"
echo "  4. Compose 文件: docker-compose.prod.yml"
echo ""
```

使用：

```bash
chmod +x ~/deploy.sh
~/deploy.sh
```

---

## 🔍 常见问题

### Q1: 是否需要重新运行准备脚本？

**A**: 如果之前运行过，建议重新运行以使用更新后的脚本。脚本会询问是否覆盖，选择 `yes`。

### Q2: 配置文件内容不对怎么办？

**A**: 删除现有配置文件，重新运行生成脚本：

```bash
cd ~/projects/Pyt
rm .env.production
bash scripts/generate_production_config.sh
```

### Q3: 镜像标签不匹配怎么办？

**A**: 修改配置文件中的 `IMAGE_TAG`：

```bash
cd ~/projects/Pyt
nano .env.production
# 修改 IMAGE_TAG=你的镜像标签
```

### Q4: 1Panel 中找不到项目目录？

**A**: 确保使用绝对路径：

```bash
# 查看实际路径
cd ~/projects/Pyt && pwd
# 输出类似: /home/username/projects/Pyt
```

在 1Panel 中使用这个绝对路径。

---

## 📚 详细文档

- [完整部署流程](WSL2_1PANEL_DEPLOYMENT_STEPS.md) - 详细的步骤说明
- [1Panel 部署指南](1PANEL_DEPLOYMENT_GUIDE.md) - 1Panel 操作说明
- [最小化部署指南](WSL2_MINIMAL_DEPLOYMENT.md) - 文件说明

---

**最后更新**: 2025-12-01

