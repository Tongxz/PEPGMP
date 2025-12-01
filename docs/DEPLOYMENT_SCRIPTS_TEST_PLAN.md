# 部署脚本统一方案 - 测试计划

## 📋 测试概述

本文档提供了统一脚本的完整测试计划，包括单元测试、集成测试和功能测试。

---

## 🧪 测试环境要求

### 基础环境

- ✅ Linux/WSL2 Ubuntu 环境
- ✅ Bash 4.0+
- ✅ 可选：Docker Desktop（用于容器化测试）
- ✅ 可选：Python 3.8+（用于宿主机模式测试）

### 测试数据

- ✅ 项目代码已克隆
- ✅ `.env` 或 `.env.production` 配置文件存在（可选）

---

## 📝 测试用例

### 1. 文件存在性测试

**目标**: 验证所有必需文件都已创建

| 测试项 | 预期结果 | 状态 |
|--------|---------|------|
| `scripts/start.sh` 存在 | ✅ 存在 | ⬜ |
| `scripts/lib/common.sh` 存在 | ✅ 存在 | ⬜ |
| `scripts/lib/env_detection.sh` 存在 | ✅ 存在 | ⬜ |
| `scripts/lib/config_validation.sh` 存在 | ✅ 存在 | ⬜ |
| `scripts/lib/docker_utils.sh` 存在 | ✅ 存在 | ⬜ |
| `scripts/lib/service_manager.sh` 存在 | ✅ 存在 | ⬜ |
| `scripts/start_dev.sh` 存在 | ✅ 存在 | ⬜ |
| `scripts/start_prod.sh` 存在 | ✅ 存在 | ⬜ |
| `scripts/start_prod_wsl.sh` 存在 | ✅ 存在 | ⬜ |

**执行命令**:
```bash
bash scripts/test_unified_script.sh
```

---

### 2. 脚本语法测试

**目标**: 验证所有脚本语法正确

| 测试项 | 预期结果 | 状态 |
|--------|---------|------|
| `start.sh` 语法检查 | ✅ 无语法错误 | ⬜ |
| `lib/*.sh` 语法检查 | ✅ 无语法错误 | ⬜ |
| `start_*.sh` 语法检查 | ✅ 无语法错误 | ⬜ |

**执行命令**:
```bash
bash -n scripts/start.sh
bash -n scripts/lib/*.sh
bash -n scripts/start_*.sh
```

---

### 3. 帮助信息测试

**目标**: 验证帮助信息正常显示

| 测试项 | 预期结果 | 状态 |
|--------|---------|------|
| `--help` 显示帮助 | ✅ 显示完整帮助信息 | ⬜ |
| 帮助信息包含所有选项 | ✅ 包含所有参数说明 | ⬜ |

**执行命令**:
```bash
./scripts/start.sh --help
```

**预期输出**:
```
统一启动脚本 - 支持开发和生产环境部署

用法: ./scripts/start.sh [选项]

选项:
  --env <dev|prod>              环境类型（必需）
  ...
```

---

### 4. 参数解析测试

**目标**: 验证参数解析正确

| 测试项 | 命令 | 预期结果 | 状态 |
|--------|------|---------|------|
| 缺少必需参数 | `./scripts/start.sh` | ❌ 显示错误信息 | ⬜ |
| 无效环境类型 | `./scripts/start.sh --env invalid` | ❌ 显示错误信息 | ⬜ |
| 有效环境类型 | `./scripts/start.sh --env dev --help` | ✅ 显示帮助 | ⬜ |
| 自定义端口 | `./scripts/start.sh --env dev --port 9000 --help` | ✅ 接受参数 | ⬜ |
| 自定义workers | `./scripts/start.sh --env prod --workers 8 --help` | ✅ 接受参数 | ⬜ |

**执行命令**:
```bash
# 测试缺少参数
./scripts/start.sh 2>&1 | grep "必须指定环境类型"

# 测试无效参数
./scripts/start.sh --env invalid 2>&1 | grep "环境类型必须是 dev 或 prod"
```

---

### 5. 环境检测测试

**目标**: 验证环境检测功能正常

| 测试项 | 预期结果 | 状态 |
|--------|---------|------|
| WSL环境检测 | ✅ 正确检测WSL（如果在WSL中） | ⬜ |
| Docker检测 | ✅ 正确检测Docker可用性 | ⬜ |
| Python检测 | ✅ 正确检测Python可用性 | ⬜ |
| 虚拟环境检测 | ✅ 正确检测虚拟环境 | ⬜ |

**执行命令**:
```bash
# 测试环境检测（不实际启动服务）
./scripts/start.sh --env dev --no-check --no-init-db --no-validate 2>&1 | head -20
```

---

### 6. 配置文件测试

**目标**: 验证配置文件处理正确

| 测试项 | 预期结果 | 状态 |
|--------|---------|------|
| 开发环境加载 `.env` | ✅ 正确加载 | ⬜ |
| 生产环境加载 `.env.production` | ✅ 正确加载 | ⬜ |
| 配置文件不存在时提示 | ✅ 显示创建提示 | ⬜ |
| 配置文件权限检查 | ✅ 检查权限（生产环境） | ⬜ |

**执行命令**:
```bash
# 测试开发环境配置
./scripts/start.sh --env dev --help 2>&1 | head -5

# 测试生产环境配置（如果文件不存在）
./scripts/start.sh --env prod --help 2>&1 | head -5
```

---

### 7. 快捷方式测试

**目标**: 验证快捷方式正确调用统一脚本

| 测试项 | 命令 | 预期结果 | 状态 |
|--------|------|---------|------|
| `start_dev.sh` 调用统一脚本 | `./scripts/start_dev.sh --help` | ✅ 显示统一脚本帮助 | ⬜ |
| `start_prod.sh` 调用统一脚本 | `./scripts/start_prod.sh --help` | ✅ 显示统一脚本帮助 | ⬜ |
| `start_prod_wsl.sh` 调用统一脚本 | `./scripts/start_prod_wsl.sh --help` | ✅ 显示统一脚本帮助 | ⬜ |
| 参数传递 | `./scripts/start_dev.sh --port 9000 --help` | ✅ 参数正确传递 | ⬜ |

**执行命令**:
```bash
./scripts/start_dev.sh --help
./scripts/start_prod.sh --help
./scripts/start_prod_wsl.sh --help
```

---

### 8. 部署模式测试

**目标**: 验证不同部署模式选择正确

| 测试项 | 环境 | 预期模式 | 状态 |
|--------|------|---------|------|
| 开发环境 + Docker + Python | 有Docker和Python | `hybrid` | ⬜ |
| 开发环境 + Docker | 只有Docker | `containerized` | ⬜ |
| 生产环境 + Docker | 有Docker | `containerized` | ⬜ |
| 生产环境 + Python | 只有Python | `host` | ⬜ |
| 手动指定模式 | 任意 | 使用指定模式 | ⬜ |

**执行命令**:
```bash
# 测试自动模式选择（需要实际环境）
./scripts/start.sh --env dev --no-check --no-init-db --no-validate 2>&1 | grep "部署模式"
```

---

### 9. 集成测试（可选）

**目标**: 验证完整部署流程（需要实际环境）

| 测试项 | 命令 | 预期结果 | 状态 |
|--------|------|---------|------|
| 开发环境启动 | `./scripts/start_dev.sh` | ✅ 服务正常启动 | ⬜ |
| 生产环境启动（容器化） | `./scripts/start_prod_wsl.sh` | ✅ 容器正常启动 | ⬜ |
| 生产环境启动（宿主机） | `./scripts/start_prod.sh` | ✅ 服务正常启动 | ⬜ |

**注意**: 这些测试需要实际环境，建议在测试环境中执行。

---

## 🚀 快速测试

### 自动化测试脚本

运行完整的自动化测试：

```bash
# 在WSL或Linux环境中执行
bash scripts/test_unified_script.sh
```

### 手动测试步骤

1. **基础测试**:
   ```bash
   # 检查文件
   ls -la scripts/start.sh scripts/lib/*.sh scripts/start_*.sh
   
   # 语法检查
   bash -n scripts/start.sh
   bash -n scripts/lib/*.sh
   ```

2. **帮助信息测试**:
   ```bash
   ./scripts/start.sh --help
   ./scripts/start_dev.sh --help
   ```

3. **参数测试**:
   ```bash
   # 测试错误处理
   ./scripts/start.sh
   ./scripts/start.sh --env invalid
   
   # 测试有效参数
   ./scripts/start.sh --env dev --help
   ```

---

## 📊 测试结果记录

### 测试环境信息

- **操作系统**: ________________
- **Bash版本**: `bash --version`
- **Docker版本**: `docker --version` (如果可用)
- **Python版本**: `python --version` (如果可用)
- **测试日期**: ________________

### 测试结果

| 测试类别 | 通过 | 失败 | 总计 | 通过率 |
|---------|------|------|------|--------|
| 文件存在性 | ___ | ___ | ___ | ___% |
| 脚本语法 | ___ | ___ | ___ | ___% |
| 帮助信息 | ___ | ___ | ___ | ___% |
| 参数解析 | ___ | ___ | ___ | ___% |
| 环境检测 | ___ | ___ | ___ | ___% |
| 配置文件 | ___ | ___ | ___ | ___% |
| 快捷方式 | ___ | ___ | ___ | ___% |
| 部署模式 | ___ | ___ | ___ | ___% |
| **总计** | ___ | ___ | ___ | ___% |

---

## ⚠️ 已知问题

（记录测试过程中发现的问题）

---

## ✅ 测试通过标准

- ✅ 所有文件存在性测试通过
- ✅ 所有脚本语法检查通过
- ✅ 帮助信息正常显示
- ✅ 参数解析正确
- ✅ 快捷方式正确调用统一脚本
- ✅ 环境检测功能正常（如果环境支持）

---

**最后更新**: 2025-11-18


