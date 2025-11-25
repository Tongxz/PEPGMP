# 部署测试计划

## 📋 概述

本文档详细列出了部署前、部署中、部署后需要执行的所有测试内容，确保生产环境部署的成功和稳定性。

**更新日期**: 2025-11-24  
**测试环境**: 开发环境 → 测试环境 → 生产环境  
**测试策略**: 自动化测试 + 手动验证

---

## 🎯 测试目标

1. **功能完整性**: 确保所有功能在生产环境中正常工作
2. **性能稳定性**: 验证系统性能满足生产要求
3. **安全性**: 确保生产环境安全配置正确
4. **可靠性**: 验证系统高可用和容错能力
5. **可维护性**: 确保监控、日志、备份等运维功能正常

---

## 📊 一、部署前测试（Pre-Deployment Testing）

### 1.1 单元测试 ✅

**测试范围**: 所有业务逻辑单元

**执行命令**:
```bash
# 运行所有单元测试
pytest tests/unit/ -v --cov=src --cov-report=html

# 运行特定模块
pytest tests/unit/test_domain_models.py -v
pytest tests/unit/test_interfaces.py -v
```

**测试指标**:
- [ ] 单元测试通过率 ≥ 80%
- [ ] 代码覆盖率 ≥ 60%
- [ ] 所有关键业务逻辑测试覆盖

**测试清单**:
- [ ] 领域模型测试 (test_domain_models.py)
- [ ] 接口测试 (test_interfaces.py)
- [ ] 工具函数测试
- [ ] 配置管理测试

### 1.2 集成测试 ✅

**测试范围**: API端点、数据库交互、Redis缓存

**执行命令**:
```bash
# 启动开发服务器
bash scripts/start_dev.sh

# 运行集成测试
python tests/integration/test_api_integration.py

# 或使用pytest
pytest tests/integration/ -v
```

**测试内容**:

#### 1.2.1 API端点测试 (24个端点)

**读操作API** (17个):
- [ ] `GET /api/v1/monitoring/health` - 健康检查
- [ ] `GET /api/v1/system/info` - 系统信息
- [ ] `GET /api/v1/cameras` - 摄像头列表
- [ ] `GET /api/v1/cameras/{camera_id}` - 摄像头详情
- [ ] `GET /api/v1/cameras/{camera_id}/status` - 摄像头状态
- [ ] `GET /api/v1/cameras/{camera_id}/stats` - 摄像头统计
- [ ] `GET /api/v1/cameras/{camera_id}/logs` - 摄像头日志
- [ ] `GET /api/v1/records/violations` - 违规记录列表
- [ ] `GET /api/v1/records/{record_id}` - 检测记录详情
- [ ] `GET /api/v1/statistics/summary` - 统计摘要
- [ ] `GET /api/v1/statistics/detection-realtime` - 实时检测统计 ⭐
- [ ] `GET /api/v1/statistics/trends` - 趋势统计
- [ ] `GET /api/v1/alerts/history-db` - 告警历史 ⭐
- [ ] `GET /api/v1/alerts/rules` - 告警规则列表 ⭐
- [ ] `GET /api/v1/alerts/{alert_id}` - 告警详情
- [ ] `GET /api/v1/mlops/models` - 模型列表
- [ ] `GET /api/v1/mlops/models/{model_id}` - 模型详情

**写操作API** (4个):
- [ ] `POST /api/v1/cameras` - 创建摄像头
- [ ] `PUT /api/v1/cameras/{camera_id}` - 更新摄像头
- [ ] `POST /api/v1/alerts/rules` - 创建告警规则
- [ ] `POST /api/v1/mlops/datasets/upload` - 数据集上传

**领域服务验证** (3个):
- [ ] `GET /api/v1/records/violations?force_domain=true` - 违规记录（领域服务）
- [ ] `GET /api/v1/statistics/summary?force_domain=true` - 统计摘要（领域服务）
- [ ] `GET /api/v1/cameras?force_domain=true` - 摄像头列表（领域服务）

**测试脚本**:
- [ ] `tests/integration/test_api_integration.py` - Python集成测试
- [ ] `tools/integration_test.sh` - Shell快速测试
- [ ] `scripts/test_frontend_improvements.py` - 前端改进测试

**测试指标**:
- [ ] 所有API端点响应时间 < 1s
- [ ] 所有API端点返回正确状态码
- [ ] 所有API端点返回正确的数据结构
- [ ] 领域服务切换功能正常

#### 1.2.2 数据库集成测试

**测试内容**:
```bash
# 运行数据库测试
python scripts/test_database.py

# 检查数据库结构
python scripts/check_db_structure.py
```

**测试清单**:
- [ ] 数据库连接正常
- [ ] 表结构正确
- [ ] 索引已创建
- [ ] CRUD操作正常
- [ ] 查询性能可接受
- [ ] 迁移脚本执行成功

#### 1.2.3 Redis集成测试

**测试内容**:
```bash
# 测试Redis连接
docker exec pepgmp-redis-prod redis-cli -a $REDIS_PASSWORD PING
```

**测试清单**:
- [ ] Redis连接正常
- [ ] 缓存读写正常
- [ ] 缓存过期机制正常
- [ ] 持久化配置正确

### 1.3 前端功能测试 ✅

**测试范围**: 所有前端页面和功能

**执行命令**:
```bash
# 启动前端开发服务器
cd frontend && npm run dev

# 运行前端测试
cd frontend && npm test

# 检查构建
cd frontend && npm run build
```

**测试内容**:

#### 1.3.1 页面功能测试

**首页** (Home.vue):
- [ ] 页面加载正常
- [ ] 实时统计显示正常 ⭐
- [ ] 系统健康状态显示
- [ ] 快速操作按钮可用

**实时监控** (RealtimeMonitor.vue):
- [ ] 摄像头列表加载
- [ ] 视频流正常显示
- [ ] 布局切换正常（网格/列表）
- [ ] WebSocket连接正常

**检测记录** (DetectionRecords.vue):
- [ ] 记录列表加载
- [ ] 分页功能正常
- [ ] 筛选功能正常
- [ ] 摄像头选项动态加载 ⭐
- [ ] 详情模态框显示正常
- [ ] 导出功能正常

**统计页面** (Statistics.vue):
- [ ] 统计图表显示
- [ ] 时间范围选择正常
- [ ] 数据刷新正常
- [ ] 导出功能正常

**告警中心** (Alerts.vue):
- [ ] 告警历史列表显示
- [ ] 分页功能正常 ⭐
- [ ] 排序功能正常 ⭐
- [ ] 告警规则列表显示
- [ ] 分页功能正常 ⭐
- [ ] 详情模态框显示

#### 1.3.2 API调用测试

**测试内容**:
- [ ] 所有API调用返回正确数据
- [ ] 错误处理正常
- [ ] 加载状态显示正常
- [ ] 无控制台错误

**关键API测试**:
- [ ] `statisticsApi.getDetectionRealtimeStats()` - 实时统计 ⭐
- [ ] `cameraApi.getCameras()` - 摄像头列表
- [ ] `alertsApi.getHistory()` - 告警历史（分页）⭐
- [ ] `alertsApi.listRules()` - 告警规则（分页）⭐

#### 1.3.3 用户体验测试

**测试内容**:
- [ ] 页面响应速度 < 2s
- [ ] 无明显的UI卡顿
- [ ] 响应式布局正常（移动端/桌面端）
- [ ] 浏览器兼容性（Chrome、Firefox、Safari）

### 1.4 性能测试 ✅

**测试范围**: API响应时间、吞吐量、资源使用

**执行命令**:
```bash
# 使用ab进行压力测试
ab -n 1000 -c 10 http://localhost:8000/api/v1/monitoring/health

# 使用Python性能分析
python scripts/performance/performance_profiler.py
```

**性能指标目标**:

| 指标 | 目标值 | 测试方法 |
|------|--------|----------|
| 健康检查响应时间 | < 50ms | `time curl http://localhost:8000/api/v1/monitoring/health` |
| 简单查询响应时间 | < 200ms | API集成测试 |
| 复杂查询响应时间 | < 1s | API集成测试 |
| QPS (健康检查) | ≥ 100 | `ab` 或 `wrk` |
| QPS (业务API) | ≥ 50 | `ab` 或 `wrk` |
| CPU使用率 | < 80% | `docker stats` |
| 内存使用 | < 4GB | `docker stats` |
| 磁盘IO | < 80% | `iostat` |

**测试清单**:
- [ ] API响应时间测试
- [ ] 并发请求测试
- [ ] 资源使用监控
- [ ] 数据库查询性能
- [ ] Redis缓存性能

### 1.5 Docker环境测试 ✅

**测试范围**: Docker镜像、Docker Compose配置

**执行命令**:
```bash
# 使用生产配置测试本地Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# 验证服务健康
docker-compose -f docker-compose.prod.yml ps

# 测试API
curl http://localhost:8000/api/v1/monitoring/health

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 清理
docker-compose -f docker-compose.prod.yml down
```

**测试清单**:
- [ ] 镜像构建成功
- [ ] 镜像大小 < 1GB
- [ ] 所有容器正常启动
- [ ] 健康检查通过
- [ ] 服务间通信正常
- [ ] 日志输出正常
- [ ] 资源限制生效
- [ ] 网络配置正确
- [ ] 数据卷挂载正常

---

## 🚀 二、部署中测试（Deployment Testing）

### 2.1 部署脚本测试 ✅

**测试范围**: 部署脚本、配置验证

**执行命令**:
```bash
# 运行部署就绪检查
bash scripts/check_deployment_readiness.sh

# 验证配置
python scripts/validate_config.py
```

**测试清单**:
- [ ] 部署脚本可执行
- [ ] 配置验证通过
- [ ] 密码强度检查通过
- [ ] 文件权限正确
- [ ] Registry连接正常

### 2.2 镜像构建和推送测试 ✅

**测试范围**: Docker镜像构建、Registry推送

**执行命令**:
```bash
# 构建镜像
docker build -f Dockerfile.prod -t pepgmp-backend:latest .

# 验证镜像
docker images pepgmp-backend:latest

# 推送镜像
bash scripts/push_to_registry.sh latest v1.0.0

# 验证推送
curl http://192.168.30.83:5433/v2/pepgmp-backend/tags/list
```

**测试清单**:
- [ ] 镜像构建成功
- [ ] 镜像大小合理
- [ ] 镜像推送成功
- [ ] Registry中镜像可访问

### 2.3 服务启动测试 ✅

**测试范围**: 生产服务启动、依赖检查

**执行命令**:
```bash
# 在生产服务器上
cd /opt/pyt
docker-compose -f docker-compose.prod.yml up -d

# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f api
```

**测试清单**:
- [ ] 数据库容器启动成功
- [ ] Redis容器启动成功
- [ ] API容器启动成功
- [ ] 服务依赖顺序正确
- [ ] 健康检查通过
- [ ] 无启动错误

---

## ✅ 三、部署后测试（Post-Deployment Testing）

### 3.1 基础验证 ✅

**测试范围**: 服务可用性、基本功能

**执行命令**:
```bash
# 健康检查
curl http://localhost:8000/api/v1/monitoring/health

# 系统信息
curl http://localhost:8000/api/v1/system/info

# 检查容器状态
docker ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs --tail=100 api
```

**测试清单**:
- [ ] 健康检查返回 `healthy`
- [ ] 系统信息正确返回
- [ ] 所有容器状态为 `Up`
- [ ] 日志无错误信息

### 3.2 功能验证 ✅

**测试范围**: 所有核心功能

**执行命令**:
```bash
# 运行完整集成测试
python tests/integration/test_api_integration.py --base-url http://<SERVER_IP>:8000

# 测试关键API
curl http://<SERVER_IP>:8000/api/v1/cameras
curl http://<SERVER_IP>:8000/api/v1/records/violations?limit=10
curl http://<SERVER_IP>:8000/api/v1/statistics/detection-realtime
curl http://<SERVER_IP>:8000/api/v1/alerts/history-db?limit=10&offset=0
```

**测试清单**:
- [ ] 所有API端点可访问
- [ ] 返回正确的数据结构
- [ ] 分页功能正常
- [ ] 排序功能正常
- [ ] 筛选功能正常
- [ ] 实时统计功能正常 ⭐
- [ ] 告警分页功能正常 ⭐

### 3.3 前端验证 ✅

**测试范围**: 前端页面、用户交互

**测试方法**: 浏览器访问和手动测试

**测试清单**:
- [ ] 首页加载正常
- [ ] 实时统计显示 ⭐
- [ ] 实时监控视频流正常
- [ ] 检测记录页面正常
- [ ] 统计页面图表显示
- [ ] 告警中心分页正常 ⭐
- [ ] 无JavaScript错误
- [ ] 响应式布局正常

### 3.4 性能验证 ✅

**测试范围**: 响应时间、吞吐量、资源使用

**执行命令**:
```bash
# 响应时间测试
time curl http://<SERVER_IP>:8000/api/v1/monitoring/health

# 资源使用监控
docker stats

# 压力测试
ab -n 1000 -c 10 http://<SERVER_IP>:8000/api/v1/monitoring/health
```

**测试清单**:
- [ ] 响应时间满足要求
- [ ] 吞吐量满足要求
- [ ] CPU使用率正常
- [ ] 内存使用正常
- [ ] 磁盘IO正常
- [ ] 无资源泄漏

### 3.5 安全验证 ✅

**测试范围**: 安全配置、访问控制

**测试清单**:
- [ ] 密码强度满足要求
- [ ] 文件权限正确
- [ ] API认证正常
- [ ] HTTPS配置正确（如配置）
- [ ] 防火墙规则正确
- [ ] 敏感信息未泄露

### 3.6 监控和日志验证 ✅

**测试范围**: 监控系统、日志系统

**执行命令**:
```bash
# 检查日志
docker-compose -f docker-compose.prod.yml logs -f

# 检查监控（如配置）
curl http://localhost:9090/api/v1/query?query=up  # Prometheus
```

**测试清单**:
- [ ] 日志正常输出
- [ ] 日志轮转正常
- [ ] 监控指标收集正常（如配置）
- [ ] 告警规则配置正确（如配置）
- [ ] Grafana仪表板正常（如配置）

### 3.7 备份和恢复验证 ✅

**测试范围**: 备份脚本、恢复流程

**执行命令**:
```bash
# 测试备份
bash scripts/backup_db.sh

# 验证备份文件
ls -lh backups/

# 测试恢复（在测试环境）
bash scripts/restore_db.sh backups/backup_*.sql
```

**测试清单**:
- [ ] 备份脚本可执行
- [ ] 备份文件生成正常
- [ ] 恢复流程测试通过
- [ ] 恢复后功能正常

---

## 📋 四、测试执行记录模板

### 测试执行记录

```yaml
测试日期: 2025-11-24
测试人员: <姓名>
测试环境: 开发/测试/生产
部署版本: v1.0.0

部署前测试:
  单元测试:
    - 状态: ✅/❌
    - 通过率: XX%
    - 覆盖率: XX%
    - 备注: 
  
  集成测试:
    - API端点测试: ✅/❌ (XX/24 通过)
    - 数据库测试: ✅/❌
    - Redis测试: ✅/❌
    - 备注: 
  
  前端测试:
    - 页面功能: ✅/❌
    - API调用: ✅/❌
    - 用户体验: ✅/❌
    - 备注: 
  
  性能测试:
    - 响应时间: ✅/❌
    - 吞吐量: ✅/❌
    - 资源使用: ✅/❌
    - 备注: 

部署中测试:
  部署脚本: ✅/❌
  镜像构建: ✅/❌
  镜像推送: ✅/❌
  服务启动: ✅/❌
  备注: 

部署后测试:
  基础验证: ✅/❌
  功能验证: ✅/❌
  前端验证: ✅/❌
  性能验证: ✅/❌
  安全验证: ✅/❌
  监控验证: ✅/❌
  备份验证: ✅/❌
  备注: 

问题记录:
  - 无

总结:
  - 测试通过/失败
  - 是否可以进行生产部署
```

---

## 🔍 五、测试自动化建议

### 5.1 CI/CD集成

**GitHub Actions示例**:
```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src
      - name: Run integration tests
        run: pytest tests/integration/ -v
```

### 5.2 自动化测试脚本

**完整测试脚本**:
```bash
#!/bin/bash
# scripts/run_all_tests.sh

echo "运行所有测试..."

# 单元测试
echo "1. 运行单元测试..."
pytest tests/unit/ -v --cov=src

# 集成测试
echo "2. 运行集成测试..."
# 需要先启动服务
bash scripts/start_dev.sh &
sleep 10
pytest tests/integration/ -v
pkill -f "uvicorn"

# 前端测试
echo "3. 运行前端测试..."
cd frontend && npm test

echo "所有测试完成！"
```

---

## 📊 六、测试结果评估

### 测试通过标准

| 测试类型 | 通过标准 |
|----------|----------|
| 单元测试 | 通过率 ≥ 80% |
| 集成测试 | 所有关键API通过 |
| 前端测试 | 无阻塞性问题 |
| 性能测试 | 满足性能指标 |
| 安全测试 | 无严重安全漏洞 |

### 部署决策

- ✅ **可以部署**: 所有P0测试通过
- ⚠️ **有条件部署**: P0测试通过，部分P1测试失败
- ❌ **不能部署**: P0测试失败

---

## 📚 相关文档

- [部署前准备工作清单](./DEPLOYMENT_PREPARATION_CHECKLIST.md)
- [生产环境部署指南](./production_deployment_guide.md)
- [集成测试文档](./integration_test_complete.md)
- [性能测试文档](./OPTIMIZATION_TEST_VERIFICATION_SUMMARY.md)

---

**状态**: ✅ **测试计划已完成**  
**下一步**: 根据测试计划逐项执行测试  
**优先级**: P0测试必须通过，P1测试强烈推荐通过

