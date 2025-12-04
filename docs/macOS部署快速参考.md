# macOS 部署快速参考

## 🚀 一键部署（推荐）

```bash
# 在项目根目录执行
cd /Users/zhou/Code/Pyt

# 使用默认部署目录和日期版本
bash scripts/deploy_prod_macos.sh

# 或指定部署目录和版本
bash scripts/deploy_prod_macos.sh ~/projects/PEPGMP20251202
```

脚本会自动完成：
- ✅ 检查 Docker 环境
- ✅ 检查端口占用
- ✅ 准备部署目录
- ✅ 生成配置文件
- ✅ 构建生产镜像
- ✅ 启动所有服务
- ✅ 验证部署状态

---

## 📋 手动部署步骤

### 1. 检查 Docker

```bash
docker --version
docker info
```

### 2. 准备部署目录

```bash
cd /Users/zhou/Code/Pyt
bash scripts/prepare_minimal_deploy.sh ~/projects/Pyt
```

### 3. 生成配置

```bash
cd ~/projects/Pyt
bash /Users/zhou/Code/Pyt/scripts/generate_production_config.sh -y
```

### 4. 构建镜像

```bash
cd /Users/zhou/Code/Pyt
VERSION_TAG=$(date +%Y%m%d)
bash scripts/build_prod_only.sh $VERSION_TAG
```

### 5. 更新配置

```bash
cd ~/projects/Pyt
sed -i '' "s/IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/" .env.production
```

### 6. 启动服务

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### 7. 验证

```bash
curl http://localhost/
curl http://localhost/api/v1/monitoring/health
```

---

## 🔧 常见问题

### 端口 80 被占用

**方案 A**: 修改 `docker-compose.prod.yml` 使用 8080
```yaml
nginx:
  ports:
    - "8080:80"
```

**方案 B**: 停止占用进程
```bash
sudo lsof -i :80
# 然后停止相关进程
```

### Docker Desktop 未运行

1. 打开 Docker Desktop
2. 等待完全启动（菜单栏图标显示运行中）
3. 重新运行部署脚本

### 内存不足

1. Docker Desktop Settings → Resources
2. 增加 Memory 限制（推荐 16GB）
3. 重启 Docker Desktop

---

## 📊 验证命令

```bash
# 检查容器状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f

# 诊断前端白屏
bash scripts/diagnose_frontend_whitescreen.sh ~/projects/Pyt
```

---

## 🌐 访问地址

- **前端**: http://localhost/ 或 http://localhost:8080/
- **API**: http://localhost/api/v1/monitoring/health
- **健康检查**: http://localhost/health

---

## 📚 详细文档

- [macOS 生产部署指南](./macOS生产部署指南.md) - 完整部署指南
- [前端白屏问题排查指南](./前端白屏问题排查指南.md) - 故障排查

---

**最后更新**: 2025-12-02
