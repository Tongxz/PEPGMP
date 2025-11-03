# 生产环境密钥管理指南

## 概述

本文档提供生产环境密钥的管理、轮换和安全最佳实践。

## 已生成的密钥

### 1. 数据库密钥

```bash
DATABASE_PASSWORD      # PostgreSQL数据库密码（32字符）
DATABASE_URL          # 完整的数据库连接字符串
```

### 2. 缓存密钥

```bash
REDIS_PASSWORD        # Redis密码（32字符）
REDIS_URL            # 完整的Redis连接字符串
```

### 3. 应用密钥

```bash
ADMIN_USERNAME        # 管理员用户名（随机生成）
ADMIN_PASSWORD        # 管理员密码（24字符）
SECRET_KEY           # 应用密钥（64字符）
JWT_SECRET_KEY       # JWT令牌密钥（64字符）
```

## 密钥文件位置

| 文件 | 用途 | 权限 | Git |
|------|------|------|-----|
| `.env.production` | 生产环境配置 | 600 | ❌ 不提交 |
| `secrets/production_secrets_backup.txt` | 密钥备份 | 600 | ❌ 不提交 |
| `.env.production.example` | 配置模板 | 644 | ✅ 提交 |

## 查看密钥

### 查看所有配置

```bash
# 查看完整配置（小心，包含敏感信息）
cat .env.production
```

### 查看特定配置

```bash
# 查看管理员配置
grep "ADMIN_" .env.production

# 查看数据库配置
grep "DATABASE_" .env.production

# 查看Redis配置
grep "REDIS_" .env.production
```

### 查看密钥备份

```bash
cat secrets/production_secrets_backup.txt
```

## 验证配置

### 自动验证

```bash
# 使用验证脚本
python scripts/validate_config.py
```

### 手动验证

```bash
# 检查文件是否存在
ls -la .env.production

# 检查文件权限（应该是 600）
stat -f %A .env.production  # macOS
stat -c %a .env.production  # Linux

# 检查必需的配置项
grep -E "DATABASE_PASSWORD|REDIS_PASSWORD|SECRET_KEY" .env.production
```

## 更新密钥

### 重新生成所有密钥

```bash
# ⚠️ 警告：这会覆盖现有配置
python scripts/generate_production_secrets.py
```

### 手动更新单个密钥

```bash
# 1. 编辑配置文件
nano .env.production

# 2. 找到要更新的配置项并修改
# 例如：ADMIN_PASSWORD=new_strong_password

# 3. 保存并验证
python scripts/validate_config.py
```

### 生成新密钥的Python命令

```python
# 在Python中生成强密码
import secrets
import string

# 生成32字符密码
alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
password = ''.join(secrets.choice(alphabet) for _ in range(32))
print(password)

# 生成64字符URL安全密钥
secret_key = secrets.token_urlsafe(64)
print(secret_key)
```

### 生成新密钥的命令行

```bash
# 使用OpenSSL生成随机密码
openssl rand -base64 32

# 使用Python生成URL安全密钥
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## 密钥轮换策略

### 推荐的轮换周期

| 密钥类型 | 轮换周期 | 优先级 |
|---------|---------|--------|
| DATABASE_PASSWORD | 每季度 | 高 |
| REDIS_PASSWORD | 每季度 | 高 |
| ADMIN_PASSWORD | 每月 | 高 |
| SECRET_KEY | 每年 | 中 |
| JWT_SECRET_KEY | 每年 | 中 |

### 轮换步骤

#### 1. 数据库密码轮换

```bash
# 步骤1：在数据库中创建新密码
psql -U postgres -c "ALTER USER pyt_prod PASSWORD 'new_password';"

# 步骤2：更新配置文件
nano .env.production
# 修改 DATABASE_PASSWORD=new_password

# 步骤3：重启应用
docker-compose -f docker-compose.prod.yml restart api

# 步骤4：验证连接
curl http://localhost:8000/api/v1/monitoring/health
```

#### 2. Redis密码轮换

```bash
# 步骤1：更新Redis配置并重启
docker-compose -f docker-compose.prod.yml down redis
# 修改 docker-compose.prod.yml 中的 REDIS_PASSWORD
docker-compose -f docker-compose.prod.yml up -d redis

# 步骤2：更新应用配置
nano .env.production
# 修改 REDIS_PASSWORD=new_password

# 步骤3：重启应用
docker-compose -f docker-compose.prod.yml restart api
```

#### 3. 应用密钥轮换

```bash
# 步骤1：生成新密钥
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 步骤2：更新配置
nano .env.production
# 修改 SECRET_KEY=new_key
# 修改 JWT_SECRET_KEY=new_key

# 步骤3：重启应用（会使所有会话失效）
docker-compose -f docker-compose.prod.yml restart api

# 步骤4：通知用户重新登录
```

## 密钥备份

### 创建备份

```bash
# 创建加密备份
tar -czf production_secrets_$(date +%Y%m%d).tar.gz \
    .env.production \
    secrets/

# 使用GPG加密
gpg -c production_secrets_$(date +%Y%m%d).tar.gz

# 删除未加密的备份
rm production_secrets_$(date +%Y%m%d).tar.gz
```

### 恢复备份

```bash
# 解密备份
gpg production_secrets_YYYYMMDD.tar.gz.gpg

# 解压
tar -xzf production_secrets_YYYYMMDD.tar.gz

# 恢复文件
cp backup/.env.production .env.production
chmod 600 .env.production
```

### 备份到安全位置

```bash
# 上传到S3（加密）
aws s3 cp production_secrets_$(date +%Y%m%d).tar.gz.gpg \
    s3://my-secure-bucket/backups/ \
    --sse AES256

# 上传到加密的云存储
# 使用 rclone 或其他工具
```

## 使用密钥管理服务

### AWS Secrets Manager

```bash
# 存储密钥
aws secretsmanager create-secret \
    --name prod/database/password \
    --secret-string "your_password"

# 读取密钥
aws secretsmanager get-secret-value \
    --secret-id prod/database/password \
    --query SecretString \
    --output text
```

### HashiCorp Vault

```bash
# 存储密钥
vault kv put secret/prod/database password="your_password"

# 读取密钥
vault kv get -field=password secret/prod/database
```

### 在应用中使用

```python
# 从AWS Secrets Manager读取
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# 在应用启动时读取
secrets = get_secret('prod/application/secrets')
DATABASE_PASSWORD = secrets['database_password']
```

## 安全最佳实践

### 1. 文件权限

```bash
# 确保配置文件只有所有者可读
chmod 600 .env.production
chmod 600 secrets/production_secrets_backup.txt

# 确保目录权限正确
chmod 700 secrets/
```

### 2. 密码强度要求

- ✅ 最少16字符（推荐24-32字符）
- ✅ 包含大小写字母
- ✅ 包含数字
- ✅ 包含特殊字符
- ✅ 不使用常见密码
- ✅ 不使用个人信息

### 3. 存储安全

- ✅ 不要在代码中硬编码密钥
- ✅ 不要提交到版本控制系统
- ✅ 使用环境变量或配置文件
- ✅ 加密存储备份
- ✅ 使用密钥管理服务

### 4. 访问控制

- ✅ 限制知道密钥的人员数量
- ✅ 使用基于角色的访问控制
- ✅ 记录密钥访问日志
- ✅ 定期审计访问权限

### 5. 传输安全

- ✅ 使用HTTPS/TLS传输
- ✅ 使用SSH密钥认证
- ✅ 避免通过邮件发送密钥
- ✅ 使用安全的通信渠道

## 故障排查

### 密钥相关错误

#### 错误：Authentication failed

```bash
# 检查密码是否正确
grep DATABASE_PASSWORD .env.production

# 测试数据库连接
psql "postgresql://user:password@host:port/dbname"
```

#### 错误：Permission denied

```bash
# 检查文件权限
ls -la .env.production

# 修复权限
chmod 600 .env.production
```

#### 错误：Invalid token

```bash
# JWT密钥可能已更改，需要重新登录
# 或检查 JWT_SECRET_KEY 是否正确
grep JWT_SECRET_KEY .env.production
```

### 验证密钥有效性

```bash
# 验证数据库密码
psql "postgresql://pyt_prod:${DATABASE_PASSWORD}@localhost:5432/pyt_production" -c "SELECT 1;"

# 验证Redis密码
redis-cli -a "${REDIS_PASSWORD}" PING

# 验证应用启动
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs api | grep -i error
```

## 应急响应

### 密钥泄露处理

如果密钥泄露，立即执行以下步骤：

```bash
# 1. 立即更改所有密钥
python scripts/generate_production_secrets.py

# 2. 重启所有服务
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 3. 撤销所有会话
# 通过更改 SECRET_KEY 和 JWT_SECRET_KEY

# 4. 通知所有用户重新登录

# 5. 审查访问日志
grep -i "failed\|unauthorized" logs/app.log

# 6. 评估影响范围
# 检查是否有未授权访问

# 7. 生成事件报告
echo "$(date): 密钥泄露事件" >> security_incidents.log
```

## 检查清单

### 日常检查 ✓

- [ ] 配置文件存在且权限正确（600）
- [ ] 密钥已添加到 .gitignore
- [ ] 备份已创建且加密
- [ ] 密钥强度符合要求

### 部署检查 ✓

- [ ] 所有占位符已替换
- [ ] 配置验证通过
- [ ] 数据库连接正常
- [ ] Redis连接正常
- [ ] 应用启动成功

### 安全审计 ✓

- [ ] 密钥轮换在周期内
- [ ] 访问权限合理
- [ ] 日志中无异常
- [ ] 备份完整有效

## 参考资源

### 密钥生成工具

- Python `secrets` 模块
- OpenSSL
- 在线密码生成器（仅用于开发）

### 密钥管理服务

- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- Google Secret Manager

### 安全标准

- OWASP Password Guidelines
- NIST SP 800-63B
- CIS Security Benchmarks

---

**最后更新**: 2025-11-03
**维护者**: 系统管理员
**优先级**: 🔴 高（安全关键）
