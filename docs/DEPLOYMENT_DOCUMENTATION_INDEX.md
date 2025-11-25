# 部署文档索引

## 📋 概述

本文档提供了所有部署相关文档的索引和快速导航，帮助您快速找到所需的部署信息。

**更新日期**: 2025-11-24  
**文档版本**: 1.1  
**目标环境**: Ubuntu 22.04 LTS 内网环境  
**部署方式**: Docker 容器化部署

⚠️ **重要**: 所有部署文档已更新为内网环境下的 Ubuntu 22.04 Docker 容器化部署。

---

## 📚 文档列表

### 1. 部署准备文档

#### 1.1 [部署前准备工作清单](./DEPLOYMENT_PREPARATION_CHECKLIST.md) ⭐ **必读**

**用途**: 部署前必须完成的所有工作的详细清单

**内容**:
- 部署前必须完成的工作（P0 - 阻塞部署）
- 部署前需要测试的内容（P1 - 重要）
- 需要优化调整的地方（P2 - 建议）
- 部署流程
- 故障排查

**适用场景**:
- ✅ 首次部署前
- ✅ 部署前检查
- ✅ 部署准备

**预计阅读时间**: 15分钟

---

#### 1.2 [部署测试计划](./DEPLOYMENT_TEST_PLAN.md) ⭐ **必读**

**用途**: 详细的测试计划和测试清单

**内容**:
- 部署前测试（Pre-Deployment Testing）
- 部署中测试（Deployment Testing）
- 部署后测试（Post-Deployment Testing）
- 测试自动化建议
- 测试结果评估

**适用场景**:
- ✅ 执行测试前
- ✅ 验证部署质量
- ✅ 测试计划制定

**预计阅读时间**: 20分钟

---

#### 1.3 [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md) ⭐ **必读**

**用途**: 完整的部署流程和执行步骤

**内容**:
- 部署流程总览
- 部署前准备
- 部署执行（一键部署/分步部署）
- 部署后验证
- 需要优化调整的内容
- 更新和回滚
- 故障排查

**适用场景**:
- ✅ 执行部署时
- ✅ 部署流程参考
- ✅ 故障排查

**预计阅读时间**: 25分钟

---

### 2. 部署执行文档

#### 2.1 [生产环境部署指南](./production_deployment_guide.md) ⭐ **必读**

**用途**: 生产环境部署的详细指南

**内容**:
- 快速开始（一键部署）
- 详细部署步骤
- 部署脚本说明
- 更新和回滚
- 故障排查
- 监控和维护
- 安全最佳实践
- 性能优化

**适用场景**:
- ✅ 生产环境部署
- ✅ 部署操作参考
- ✅ 运维参考

**预计阅读时间**: 30分钟

---

#### 2.2 [生产环境部署实施报告](./production_deployment_implementation.md)

**用途**: 生产环境部署系统的实施总结

**内容**:
- 实施摘要
- 创建的文件清单
- 部署架构
- 使用指南
- 安全改进
- 性能优化
- 监控和日志

**适用场景**:
- ✅ 了解部署系统架构
- ✅ 部署系统设计参考

**预计阅读时间**: 20分钟

---

### 3. 内网环境部署文档 ⭐ **重要**

#### 3.1 [内网环境部署说明](./INTRANET_DEPLOYMENT_NOTES.md) ⭐ **必读**

**用途**: 内网环境下 Ubuntu 22.04 Docker 容器化部署的特殊说明

**内容**:
- 内网环境特殊考虑
- Ubuntu 22.04 特定配置
- Docker Compose V2 使用说明
- 内网Registry配置
- 内网网络配置
- 容器化部署特殊配置
- 内网环境故障排查

**适用场景**:
- ✅ **内网环境部署（必读）**
- ✅ Ubuntu 22.04 配置参考
- ✅ Docker容器化部署参考
- ✅ 内网环境故障排查

**预计阅读时间**: 25分钟

---

### 4. 配置文档

#### 4.1 [配置管理最佳实践](./configuration_management_best_practices.md)

**用途**: 配置管理的最佳实践方案

**内容**:
- 问题分析
- 使用.env文件管理配置
- 配置加载优先级
- 配置文件示例

**适用场景**:
- ✅ 配置管理参考
- ✅ 配置问题排查

**预计阅读时间**: 15分钟

---

#### 4.2 [Docker Compose使用指南](./docker_compose_usage_guide.md)

**用途**: Docker Compose配置和使用指南

**内容**:
- Docker Compose基础
- 配置文件说明
- 常用命令
- 多环境配置

**适用场景**:
- ✅ Docker Compose操作参考
- ✅ 容器管理

**预计阅读时间**: 20分钟

---

## 🚀 快速开始

### 首次部署

**推荐阅读顺序**:
1. [部署前准备工作清单](./DEPLOYMENT_PREPARATION_CHECKLIST.md) - 了解需要做什么
2. [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md) - 了解如何执行
3. [生产环境部署指南](./production_deployment_guide.md) - 详细的部署步骤

**快速部署命令**:
```bash
# 1. 生成配置
bash scripts/generate_production_config.sh

# 2. 检查部署就绪
bash scripts/check_deployment_readiness.sh

# 3. 一键部署
bash scripts/quick_deploy.sh <SERVER_IP> ubuntu
```

### 更新部署

**推荐阅读顺序**:
1. [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md) - 更新和回滚部分
2. [生产环境部署指南](./production_deployment_guide.md) - 更新部分

**快速更新命令**:
```bash
# 一键更新
bash scripts/quick_deploy.sh <SERVER_IP> ubuntu
```

### 测试验证

**推荐阅读顺序**:
1. [部署测试计划](./DEPLOYMENT_TEST_PLAN.md) - 完整的测试计划
2. [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md) - 部署后验证部分

**快速测试命令**:
```bash
# 运行集成测试
python tests/integration/test_api_integration.py

# 验证部署
bash scripts/check_deployment_readiness.sh
```

---

## 📋 检查清单快速参考

### 部署前检查 ✅

```
□ 配置文件准备完成 (.env.production)
□ Docker环境准备完成
□ 代码质量检查通过
□ 测试验证通过
□ 部署脚本可执行
```

### 部署中检查 ✅

```
□ 镜像构建成功
□ 镜像推送成功
□ 服务启动成功
□ 健康检查通过
```

### 部署后检查 ✅

```
□ 基础验证通过
□ 功能验证通过
□ 性能验证通过
□ 监控验证通过
```

---

## 🔧 常用命令参考

### 配置管理

```bash
# 生成生产配置
bash scripts/generate_production_config.sh

# 验证配置
python scripts/validate_config.py

# 检查部署就绪
bash scripts/check_deployment_readiness.sh
```

### 镜像管理

```bash
# 构建镜像
docker build -f Dockerfile.prod -t pepgmp-backend:latest .

# 推送镜像
bash scripts/push_to_registry.sh latest v1.0.0

# 拉取镜像
docker pull 192.168.30.83:5433/pepgmp-backend:latest
```

### 部署管理

```bash
# 一键部署
bash scripts/quick_deploy.sh <SERVER_IP> ubuntu

# 从Registry部署
bash scripts/deploy_from_registry.sh <SERVER_IP> ubuntu latest
```

### 服务管理

```bash
# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f api

# 停止服务
docker-compose -f docker-compose.prod.yml down
```

### 测试验证

```bash
# 健康检查
curl http://localhost:8000/api/v1/monitoring/health

# 运行集成测试
python tests/integration/test_api_integration.py

# 运行单元测试
pytest tests/unit/ -v
```

---

## 📊 文档使用场景

### 场景1: 首次部署生产环境（内网环境）

**推荐阅读**:
1. [内网环境部署说明](./INTRANET_DEPLOYMENT_NOTES.md) ⭐ **必读** - 内网环境特殊说明
2. [部署前准备工作清单](./DEPLOYMENT_PREPARATION_CHECKLIST.md) - 完整清单
3. [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md) - 执行步骤
4. [生产环境部署指南](./production_deployment_guide.md) - 详细操作

**预计时间**: 首次部署 10-15分钟

**重要**: 内网环境部署必须阅读 [内网环境部署说明](./INTRANET_DEPLOYMENT_NOTES.md)

---

### 场景2: 更新生产环境

**推荐阅读**:
1. [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md) - 更新部分
2. [生产环境部署指南](./production_deployment_guide.md) - 更新流程

**预计时间**: 更新部署 3-5分钟

---

### 场景3: 部署前测试验证

**推荐阅读**:
1. [部署测试计划](./DEPLOYMENT_TEST_PLAN.md) - 完整测试计划
2. [部署前准备工作清单](./DEPLOYMENT_PREPARATION_CHECKLIST.md) - 测试清单

**预计时间**: 测试执行 20-30分钟

---

### 场景4: 故障排查

**推荐阅读**:
1. [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md) - 故障排查部分
2. [生产环境部署指南](./production_deployment_guide.md) - 故障排查部分

**预计时间**: 根据问题复杂度

---

### 场景5: 性能优化

**推荐阅读**:
1. [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md) - 需要优化调整的内容
2. [生产环境部署指南](./production_deployment_guide.md) - 性能优化部分

**预计时间**: 根据优化内容

---

## 🎯 关键文档优先级

### P0 - 必须阅读（首次部署前）

1. ✅ [内网环境部署说明](./INTRANET_DEPLOYMENT_NOTES.md) ⭐ **内网环境必读**
2. ✅ [部署前准备工作清单](./DEPLOYMENT_PREPARATION_CHECKLIST.md)
3. ✅ [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md)
4. ✅ [生产环境部署指南](./production_deployment_guide.md)

### P1 - 强烈推荐（执行部署时）

1. ✅ [部署测试计划](./DEPLOYMENT_TEST_PLAN.md)
2. ✅ [配置管理最佳实践](./configuration_management_best_practices.md)

### P2 - 可选参考（高级场景）

1. ✅ [生产环境部署实施报告](./production_deployment_implementation.md)
2. ✅ [Docker Compose使用指南](./docker_compose_usage_guide.md)

---

## 📞 获取帮助

### 常见问题

如果遇到问题，请按以下顺序排查：

1. **检查部署就绪状态**
   ```bash
   bash scripts/check_deployment_readiness.sh
   ```

2. **查看部署文档**
   - [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md) - 故障排查部分
   - [生产环境部署指南](./production_deployment_guide.md) - 故障排查部分

3. **查看日志**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f
   ```

4. **验证配置**
   ```bash
   python scripts/validate_config.py
   ```

### 联系支持

如果问题仍未解决，请提供以下信息：

- 部署日志
- 错误信息
- 配置信息（隐藏敏感信息）
- 系统环境信息

---

## 📝 文档更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2025-11-24 | 1.0 | 初始版本，包含所有部署文档索引 |

---

## 📚 相关文档

### 前端相关

- [前端功能详细分析](./FRONTEND_DETAILED_FEATURE_ANALYSIS.md)
- [前端改进完成报告](./FRONTEND_IMPROVEMENT_COMPLETION_REPORT.md)

### 系统架构

- [系统架构文档](./SYSTEM_ARCHITECTURE.md)
- [架构合规规则](./ARCHITECTURE_COMPLIANCE_*.md)

### 测试相关

- [集成测试文档](./integration_test_complete.md)
- [测试计划](./DEPLOYMENT_TEST_PLAN.md)

---

**状态**: ✅ **文档索引已完成**  
**最后更新**: 2025-11-24  
**维护**: 持续更新中

