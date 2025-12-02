# 验证配置文件

## 步骤 1: 检查生成的配置文件

```bash
cd /mnt/f/code/PythonCode/Pyt

# 检查镜像标签
grep IMAGE_TAG .env.production

# 检查密码（应该看到实际的强随机密码，不是 CHANGE_ME）
grep -E 'DATABASE_PASSWORD|REDIS_PASSWORD' .env.production | head -2

# 检查管理员账户
grep -E 'ADMIN_USERNAME|ADMIN_PASSWORD' .env.production
```

## 步骤 2: 验证 Docker Compose 配置

```bash
cd /mnt/f/code/PythonCode/Pyt

# 使用 --env-file 明确指定环境变量文件
docker-compose -f docker-compose.prod.yml --env-file .env.production config | grep -E 'image:|IMAGE_TAG|DATABASE_PASSWORD|REDIS_PASSWORD|ADMIN_USERNAME|ADMIN_PASSWORD'
```

**预期结果**：
- `image: pepgmp-backend:20251201`（不再是 latest）
- `DATABASE_PASSWORD: MB_MQI1WFyRHcEW5lUtGnhOi9cDN-exqHXnXARIv3v8`（实际密码）
- `REDIS_PASSWORD: 2WlaMYmqDnM30eoi80Q-_wgUwMdqLfgp0HQYGXpfJ_s`（实际密码）
- `ADMIN_USERNAME: pepadmin`
- `ADMIN_PASSWORD: x6TimzMLrBM-Zcpy5hn5Wb4oGnpFYmTGW-kAlhIJtlg`

## 步骤 3: 复制到部署目录（如果需要）

如果需要在 WSL Ubuntu 的部署目录中使用：

```bash
# 从 Windows 项目目录复制到 WSL 部署目录
cp /mnt/f/code/PythonCode/Pyt/.env.production ~/projects/Pyt/.env.production

# 设置正确的权限
chmod 600 ~/projects/Pyt/.env.production

# 验证
cd ~/projects/Pyt
docker-compose -f docker-compose.prod.yml --env-file .env.production config | grep -E 'image:|DATABASE_PASSWORD|REDIS_PASSWORD'
```

## 步骤 4: 在 1Panel 中部署

1. 确保工作目录：`/home/pep/projects/Pyt`
2. 确保 `.env.production` 文件存在且包含正确的密码
3. 在 1Panel 中创建/更新 Compose 项目
4. 使用 `docker-compose.prod.yml` 文件（1Panel 会自动加载 `.env.production`）

