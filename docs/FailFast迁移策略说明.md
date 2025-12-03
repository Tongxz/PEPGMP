# Fail Fast 迁移策略说明

## 🔍 问题背景

### 原始风险

在之前的实现中，数据库迁移失败时，脚本只是打印警告但继续启动应用：

```bash
if alembic upgrade head; then
    print_success "Database migrations completed successfully"
else
    print_warning "Database migrations failed (non-fatal, continuing anyway)"
    # 继续启动应用 ❌
fi
```

**风险**:
- ⚠️ 如果数据库迁移失败（例如表结构不匹配），代码却强行启动
- ⚠️ 应用在运行时会出现大量的 500 错误
- ⚠️ 可能导致数据损坏或脏数据写入
- ⚠️ 问题难以发现，因为应用"看起来"在运行
- ⚠️ 运维人员可能不知道数据库结构有问题

---

## ✅ Fail Fast 策略

### 核心原则

**Fail Fast（快速失败）**: 如果迁移失败，容器应该立即退出，而不是继续运行。

### 修复后的行为

```bash
if alembic upgrade head; then
    print_success "Database migrations completed successfully"
else
    print_error "Database migrations failed!"
    print_error "  Container will exit now to prevent running with an incompatible database."
    exit 1  # 立即退出 ✅
fi
```

**效果**:
- ✅ 迁移失败时容器立即退出（退出码 1）
- ✅ Docker Compose/Kubernetes 会标记容器为 Unhealthy
- ✅ 容器会不断重启（如果配置了 `restart: unless-stopped`）
- ✅ 运维人员能立刻发现问题（通过日志或容器状态）
- ✅ 避免应用在错误的数据库结构下运行
- ✅ 防止数据损坏和脏数据写入

---

## 📋 失败场景分析

### 场景 1: 数据库结构不匹配

**情况**: 数据库表结构与代码期望的不一致

**Fail Fast 行为**:
- 迁移失败，容器退出
- 日志显示详细的错误信息
- 运维人员立即发现问题并修复

**如果继续运行**:
- 应用启动，但查询失败
- 大量 500 错误
- 用户看到错误页面
- 问题难以定位

---

### 场景 2: 迁移冲突

**情况**: 多个迁移文件冲突或依赖问题

**Fail Fast 行为**:
- 迁移失败，容器退出
- 日志显示冲突详情
- 开发人员可以修复迁移文件

**如果继续运行**:
- 部分迁移可能已执行
- 数据库处于不一致状态
- 需要手动回滚和修复

---

### 场景 3: 数据库连接问题

**情况**: 数据库连接失败或权限不足

**Fail Fast 行为**:
- 迁移失败，容器退出
- 日志显示连接错误
- 运维人员检查网络和权限

**如果继续运行**:
- 应用可能启动，但无法访问数据库
- 所有数据库操作失败
- 用户无法使用系统

---

## 🔧 实现细节

### 当前实现

```bash
# 执行数据库迁移（如果使用 Alembic）
if [ -f "alembic.ini" ] && command -v alembic >/dev/null 2>&1; then
    print_info "Running database migrations..."

    if alembic upgrade head; then
        print_success "Database migrations completed successfully"
    else
        print_error "Database migrations failed!"
        print_error "  Container will exit now to prevent running with an incompatible database."
        exit 1  # Fail Fast
    fi
else
    print_info "No Alembic migration found, skipping..."
fi
```

### 错误信息

迁移失败时会输出详细的错误信息：

```
[ERROR] Database migrations failed!
[ERROR]   This is a critical error. The application cannot start with an incompatible database schema.
[ERROR]   Please check the migration logs above and fix the issue before restarting.
[ERROR]
[ERROR]   Common causes:
[ERROR]     - Database schema is out of sync with migration files
[ERROR]     - Migration conflicts or dependency issues
[ERROR]     - Database connection or permission problems
[ERROR]
[ERROR]   Container will exit now to prevent running with an incompatible database.
```

---

## 🚀 Docker Compose 行为

### 容器重启策略

在 `docker-compose.prod.yml` 中配置了 `restart: unless-stopped`：

```yaml
api:
  restart: unless-stopped
```

**行为**:
- 迁移失败 → 容器退出（退出码 1）
- Docker Compose 检测到退出 → 标记为 Unhealthy
- 如果配置了 `restart: unless-stopped` → 容器会不断重启
- 每次重启都会尝试迁移，直到成功

**注意**: 如果迁移一直失败，容器会不断重启。运维人员需要：
1. 查看日志：`docker logs pepgmp-api-prod`
2. 修复迁移问题
3. 重启容器：`docker-compose restart api`

---

## 📊 对比分析

| 策略 | 迁移失败时行为 | 优点 | 缺点 |
|------|---------------|------|------|
| **继续运行**（旧） | 打印警告，继续启动 | 应用"看起来"在运行 | ❌ 运行时错误<br>❌ 数据损坏风险<br>❌ 问题难以发现 |
| **Fail Fast**（新） | 立即退出（exit 1） | ✅ 立即发现问题<br>✅ 防止数据损坏<br>✅ 清晰的错误信息 | 需要修复后才能启动 |

---

## 🔍 故障排查

### 问题 1: 容器不断重启

**症状**: 容器启动后立即退出，然后不断重启

**原因**: 数据库迁移失败

**解决步骤**:
```bash
# 1. 查看容器日志
docker logs pepgmp-api-prod

# 2. 查看最后几行（迁移错误）
docker logs pepgmp-api-prod --tail 50

# 3. 检查数据库连接
docker exec pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production -c "\dt"

# 4. 手动测试迁移
docker exec pepgmp-api-prod alembic upgrade head

# 5. 修复问题后重启
docker-compose restart api
```

### 问题 2: 迁移文件冲突

**症状**: 日志显示 "Target database is not up to date" 或类似错误

**解决**:
```bash
# 1. 查看当前迁移版本
docker exec pepgmp-api-prod alembic current

# 2. 查看迁移历史
docker exec pepgmp-api-prod alembic history

# 3. 检查迁移文件
ls -la alembic/versions/

# 4. 修复冲突后重新迁移
docker exec pepgmp-api-prod alembic upgrade head
```

### 问题 3: 数据库权限问题

**症状**: 日志显示 "permission denied" 或 "access denied"

**解决**:
```bash
# 1. 检查数据库用户权限
docker exec pepgmp-postgres-prod psql -U postgres -c "\du pepgmp_prod"

# 2. 检查数据库连接配置
docker exec pepgmp-api-prod env | grep DATABASE

# 3. 测试数据库连接
docker exec pepgmp-api-prod pg_isready -h database -U pepgmp_prod -d pepgmp_production
```

---

## ⚙️ 配置选项

### 禁用迁移（不推荐）

如果确实需要禁用迁移检查（例如使用 SQL 脚本迁移），可以：

**方法 1**: 删除或重命名 `alembic.ini`
```bash
# 在 Dockerfile 中
RUN mv alembic.ini alembic.ini.disabled || true
```

**方法 2**: 使用环境变量控制
```bash
# 在 docker-entrypoint.sh 中
if [ "${SKIP_MIGRATIONS:-false}" = "true" ]; then
    print_warning "Skipping database migrations (SKIP_MIGRATIONS=true)"
else
    # 执行迁移...
fi
```

**注意**: 不推荐在生产环境禁用迁移检查，除非有明确的理由。

---

## 📝 最佳实践

### 1. 迁移前备份

在生产环境执行迁移前，应该备份数据库：

```bash
# 备份数据库
docker exec pepgmp-postgres-prod pg_dump -U pepgmp_prod pepgmp_production > backup_$(date +%Y%m%d_%H%M%S).sql

# 然后执行迁移
docker-compose restart api
```

### 2. 测试迁移

在测试环境先测试迁移：

```bash
# 在测试环境
docker-compose -f docker-compose.test.yml up -d
docker logs pepgmp-api-test | grep -i migration
```

### 3. 监控迁移状态

设置监控告警，当容器不断重启时发送通知：

```yaml
# Prometheus 或监控系统
- alert: APIContainerRestarting
  expr: rate(container_restart_count[5m]) > 0
  annotations:
    summary: "API container is restarting frequently"
```

---

## 🎯 总结

**Fail Fast 策略的优势**:
- ✅ 立即发现问题，而不是让应用在错误状态下运行
- ✅ 防止数据损坏和脏数据写入
- ✅ 清晰的错误信息，便于排查
- ✅ 与 Docker Compose/Kubernetes 的健康检查机制配合良好

**关键原则**:
- 🎯 **迁移失败 = 致命错误**，必须修复后才能启动
- 🎯 **快速失败 > 延迟失败**，越早发现问题越好
- 🎯 **明确的错误信息**，帮助运维人员快速定位问题

---

**文档版本**: 1.0
**创建日期**: 2025-01-18
**维护者**: 开发团队
