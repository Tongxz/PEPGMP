# 项目清理计划

## 日期
2025-11-03

## 概述

在完成重构和生产环境部署改进后，项目中积累了一些冗余文件和旧版本文件。本文档提供清理建议。

## 🔍 分析结果

### 1. 部署相关冗余文件

#### Docker文件重复

| 文件 | 状态 | 建议 |
|------|------|------|
| `Dockerfile.prod` | 旧版本 | ❌ 删除（已被`Dockerfile.prod.new`替代）|
| `Dockerfile.prod.new` | 新版本 | ✅ 保留并重命名为`Dockerfile.prod` |
| `Dockerfile.dev` | 开发环境 | ✅ 保留 |
| `Dockerfile.frontend` | 前端 | ✅ 保留 |

#### Docker Compose文件

| 文件 | 用途 | 建议 |
|------|------|------|
| `docker-compose.yml` | 开发环境（当前使用） | ✅ 保留 |
| `docker-compose.prod.yml` | 生产环境（新版本） | ✅ 保留 |
| `docker-compose.dev-db.yml` | 开发数据库 | ⚠️ 检查是否重复 |
| `docker-compose.prod.mlops.yml` | MLOps功能 | ⚠️ 评估是否需要 |

#### 备份目录

| 目录 | 内容 | 建议 |
|------|------|------|
| `docker_backup/` | 旧Docker配置备份 | ❌ 删除（已有Git历史）|
| `docker_exports/` | 旧镜像导出文件 | ❌ 删除（占用空间）|
| `deployment/` | 旧部署脚本 | ❌ 移动到archive/ |

### 2. 重复的部署脚本

| 位置 | 内容 | 建议 |
|------|------|------|
| `deployment/` | 旧的部署脚本和README | ❌ 移动到archive/ |
| `scripts/deployment/` | 旧的部署脚本 | ❌ 移动到archive/ |
| `src/deployment/` | 旧的部署代码 | ❌ 移动到archive/ |
| `scripts/deploy_prod.sh` | 新的部署脚本 | ✅ 保留 |
| `scripts/start_prod.sh` | 新的启动脚本 | ✅ 保留 |

### 3. 重复的Requirements文件

| 文件 | 用途 | 建议 |
|------|------|------|
| `requirements.txt` | 主依赖文件 | ✅ 保留 |
| `requirements.dev.txt` | 开发依赖 | ✅ 保留 |
| `requirements.prod.txt` | 生产依赖（重复） | ⚠️ 合并到requirements.txt |
| `requirements-prod.txt` | 生产依赖（重复） | ❌ 删除 |
| `requirements.supervisor.txt` | Supervisor依赖 | ⚠️ 评估是否需要 |

### 4. 根目录杂项文件

| 文件 | 说明 | 建议 |
|------|------|------|
| `GPU性能优化README.md` | GPU优化文档 | ❌ 移动到docs/ |
| `how --name-only 461baf8` | 误创建的文件 | ❌ 删除 |
| `test_api_connectivity.sh` | 测试脚本 | ❌ 移动到tools/ |
| `test_frontend_functionality.js` | 测试脚本 | ❌ 移动到tools/ |
| `test_intelligent_features.py` | 测试脚本 | ❌ 移动到tools/ |
| `test_mlops_integration.py` | 测试脚本 | ❌ 移动到tools/ |
| `verify_frontend_features.py` | 测试脚本 | ❌ 移动到tools/ |

### 5. Config目录

| 文件 | 说明 | 建议 |
|------|------|------|
| `config/production.env.example` | 旧的生产配置模板 | ❌ 删除（已有`.env.production.example`）|

### 6. Archive目录

| 目录 | 内容 | 状态 |
|------|------|------|
| `archive/phase1/` | Phase 1清理的文件 | ✅ 保留 |
| `archive/phase2/` | Phase 2清理的文件 | ✅ 保留 |
| `archive/phase3/` | Phase 3清理的文件 | ✅ 保留 |

## 📋 清理清单

### 阶段1：安全删除（无风险）✅

**可直接删除的文件/目录：**

```bash
# 备份目录
docker_backup/              # 旧Docker配置备份
docker_exports/             # 旧镜像导出（大文件）

# 误创建的文件
how --name-only 461baf8     # Git命令输出误创建

# 重复的requirements
requirements-prod.txt       # 与requirements.prod.txt重复

# 旧的配置模板
config/production.env.example  # 已被.env.production.example替代
```

**预计释放空间：**
- docker_exports/: ~几百MB到几GB
- docker_backup/: ~几MB
- 其他文件: ~几KB

### 阶段2：移动到Archive（低风险）⚠️

**需要归档的目录：**

```bash
# 旧的部署相关文件
deployment/                 # 旧部署脚本和配置
scripts/deployment/         # 旧部署脚本
src/deployment/             # 旧部署代码
```

**归档到：**
```bash
archive/deployment_legacy/
├── deployment/
├── scripts_deployment/
└── src_deployment/
```

### 阶段3：整理和重命名（中风险）⚠️

**需要重命名的文件：**

```bash
# Docker文件
Dockerfile.prod.new  →  Dockerfile.prod  # 替换旧版本
```

**需要移动的文件：**

```bash
# 移动到docs/
GPU性能优化README.md  →  docs/GPU性能优化指南.md

# 移动到tools/
test_api_connectivity.sh          →  tools/test_api_connectivity.sh
test_frontend_functionality.js    →  tools/test_frontend_functionality.js
test_intelligent_features.py      →  tools/test_intelligent_features.py
test_mlops_integration.py         →  tools/test_mlops_integration.py
verify_frontend_features.py       →  tools/verify_frontend_features.py
```

### 阶段4：评估后决定（高风险）🔴

**需要评估的文件：**

```bash
# Docker Compose
docker-compose.dev-db.yml       # 检查是否被使用
docker-compose.prod.mlops.yml   # 检查MLOps功能是否需要

# Requirements
requirements.prod.txt           # 与requirements.txt比对
requirements.supervisor.txt     # 检查Supervisor是否使用
```

## 🚀 执行步骤

### 步骤1：备份

```bash
# 创建完整备份
tar -czf project_backup_$(date +%Y%m%d).tar.gz \
    docker_backup/ \
    docker_exports/ \
    deployment/ \
    scripts/deployment/ \
    src/deployment/

# 上传到安全位置（可选）
# aws s3 cp project_backup_*.tar.gz s3://my-backups/
```

### 步骤2：执行阶段1清理

```bash
# 删除备份目录
rm -rf docker_backup/
rm -rf docker_exports/

# 删除误创建文件
rm -f "how --name-only 461baf8"

# 删除重复文件
rm -f requirements-prod.txt
rm -f config/production.env.example
```

### 步骤3：执行阶段2归档

```bash
# 创建归档目录
mkdir -p archive/deployment_legacy

# 移动旧部署文件
mv deployment/ archive/deployment_legacy/
mv scripts/deployment/ archive/deployment_legacy/scripts_deployment/
mv src/deployment/ archive/deployment_legacy/src_deployment/
```

### 步骤4：执行阶段3整理

```bash
# 重命名Docker文件
mv Dockerfile.prod Dockerfile.prod.old.backup
mv Dockerfile.prod.new Dockerfile.prod

# 移动文档
mv GPU性能优化README.md docs/GPU性能优化指南.md

# 移动测试脚本
mv test_*.sh tools/
mv test_*.py tools/
mv test_*.js tools/
mv verify_*.py tools/
```

### 步骤5：验证

```bash
# 验证Docker构建
docker build -f Dockerfile.prod -t test-build .

# 验证启动脚本
./scripts/start_dev.sh --help

# 运行测试
pytest tests/
```

### 步骤6：提交更改

```bash
# 查看更改
git status

# 提交清理
git add .
git commit -m "chore: 清理冗余部署文件和旧版本配置

- 删除docker_backup/和docker_exports/目录
- 归档旧的deployment/目录到archive/
- 重命名Dockerfile.prod.new为Dockerfile.prod
- 整理根目录测试脚本到tools/
- 移除重复的requirements文件
- 更新文档位置
"
```

## 📊 预期收益

### 空间节省

| 项目 | 预计节省 |
|------|----------|
| docker_exports/ | 500MB - 2GB |
| docker_backup/ | 10-50MB |
| 其他文件 | 1-5MB |
| **总计** | **~500MB - 2GB** |

### 代码质量

- ✅ 减少冗余文件
- ✅ 清晰的项目结构
- ✅ 更容易导航
- ✅ 减少混淆

### 维护性

- ✅ 明确哪些文件在使用
- ✅ 减少过时文档
- ✅ 更好的Git历史
- ✅ 更快的搜索

## ⚠️ 风险评估

### 低风险（可直接执行）✅

- 删除docker_backup/（已有Git历史）
- 删除docker_exports/（可重新导出）
- 删除误创建文件
- 删除明确重复的文件

### 中风险（需要测试）⚠️

- 重命名Dockerfile.prod
- 移动测试脚本
- 归档旧部署脚本

### 高风险（需要评估）🔴

- 删除requirements文件（需要确认依赖）
- 删除docker-compose文件（需要确认用途）

## 📝 回滚计划

如果清理后出现问题：

```bash
# 方式1：从备份恢复
tar -xzf project_backup_YYYYMMDD.tar.gz

# 方式2：从Git恢复
git reset --hard HEAD~1

# 方式3：从archive恢复
cp -r archive/deployment_legacy/deployment/ ./
```

## ✅ 检查清单

清理前：
- [ ] 创建完整备份
- [ ] 确认当前分支为开发分支
- [ ] 所有更改已提交
- [ ] 测试通过

清理中：
- [ ] 按阶段执行
- [ ] 每步后验证
- [ ] 记录删除的文件

清理后：
- [ ] Docker构建成功
- [ ] 测试全部通过
- [ ] 应用正常启动
- [ ] 文档更新完成
- [ ] Git提交清理记录

## 📚 参考

- [Git历史](https://github.com/your-repo/commits)
- [备份位置](./backups/)
- [Archive目录](./archive/)

---

**状态**: 📋 待执行
**优先级**: 中
**预计时间**: 30-60分钟
**风险等级**: 低-中
