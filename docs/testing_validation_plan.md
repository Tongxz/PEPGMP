# 灰度验证与渐进切换测试验证方案

本文档定义从现有实现逐步切换到领域驱动（DDD）新服务的测试与发布策略，覆盖范围、开关、环境矩阵、验证分层、通过标准、观测与回滚、清单、工具与节奏。

## 1. 范围与开关
- 开关位置
  - 容器绑定：`src/container/service_config.py` 绑定仓储与 `DetectionServiceDomain`
  - 环境变量：`USE_DOMAIN_SERVICE=true|false`（新增），在依赖注入处读取
- 首批试点范围（仅读接口）
  - 统计摘要：`GET /api/v1/statistics/summary`
  - 违规列表：`GET /api/v1/records/violations`
  - 摄像头统计：`GET /api/v1/cameras/{id}/stats`
- 暂不改动的路径
  - 实时检测执行、进程调度/管理、WebSocket 广播（保持现状）

## 2. 环境矩阵
- 开发本地：PostgreSQL 本地、Redis 本地（现有）
- 预发（可选）：与生产一致的 Docker Compose（含 GPU/无 GPU）
- 生产：仅对“试点路由”开启 `USE_DOMAIN_SERVICE=true` 灰度

## 3. 验证分层与通过标准
### 3.1 单元/组件级（本地）
- 覆盖：领域层单元测试 + 既有单测回归
- 通过标准：
  - 单测全绿（当前 213 通过/9 跳过）；新增领域服务单测≥90% 覆盖
  - 规范通过：flake8/black/isort

### 3.2 集成级（本地 + 预发）
- 用例：
  - `GET /api/v1/statistics/summary`
  - `GET /api/v1/records/violations`
  - `GET /api/v1/cameras/{id}/stats`
  - 领域事件仅记录日志（不接入消息总线）
- 通过标准：
  - 返回结构与前端期望对齐（字段齐全、类型一致）
  - 无异常堆栈；平均响应时间与旧实现同量级（±15%）

### 3.3 E2E 回归（本地/预发）
- 前端页面：仪表盘、MLOps 管理页关键读 API 正常加载
- WebSocket：状态初始化/增量推送不受影响（仍走原路径）
- 通过标准：
  - 前端无空白页/报错；关键按钮/卡片数据正确
  - WS 心跳、消息格式保持不变

### 3.4 性能与稳定性（预发）
- 数据：本地视频 + 小批量真实数据回放（10–30 分钟）
- 指标：QPS、P95、CPU/GPU、内存峰值、Redis/PG 连接峰值
- 通过标准：
  - 对比旧实现退化≤10%；无内存泄漏；无异常重启

### 3.5 观测与回滚（生产）
- 灰度开启方式：仅对试点路由设置 `USE_DOMAIN_SERVICE=true`
- 观测窗口：24–72 小时
- 回滚标准：
  - 任一指标退化>15% 或出现不可接受错误，立即切回 `false`

## 4. 执行清单（Checklist）
### 4.1 配置与依赖注入
- [ ] 新增 `USE_DOMAIN_SERVICE` 环境变量并在容器层读取
- [ ] `RepositoryFactory` 按配置创建 `postgresql|redis|hybrid`
- [ ] `get_detection_service_domain()` 可被 API 注入

### 4.2 单元测试
- [ ] 领域实体/值对象/服务/事件单测齐全
- [ ] 示例脚本 `examples/domain_model_usage.py` 可运行

### 4.3 集成与接口一致性
- [ ] 试点 API 的服务注入切到领域服务（仅读接口）
- [ ] 对比旧接口响应结构（字段名、空值策略、分页/排序）

### 4.4 前端验证
- [ ] 调用上述 API 的页面数据正确（无 TS 报错、无空白）
- [ ] WS 与轮询后备逻辑不受影响

### 4.5 性能与稳定性
- [ ] 本地简压/预发小规模回放
- [ ] 指标采集：Uvicorn 访问日志、容器 stats、PG/Redis 指标

### 4.6 回滚与文档
- [ ] 预案：一键切回 `USE_DOMAIN_SERVICE=false`
- [ ] 变更清单与责任人

## 5. 数据与兼容性注意点
- 序列化：`DetectionRecord.to_dict()` 与前端期望一致（ISO 时间戳、数值类型）
- 分页/排序：对齐历史接口参数与默认值
- 空数据：返回空数组/默认统计值，避免 4xx
- 事件：领域事件仅记录日志，不影响 Redis/WS 线路

## 6. 工具与命令
- 单测：`pytest -q` 或分组执行 `tests/unit/*.py`
- 示例：`python examples/domain_model_usage.py`
- 本地后端：现有 `uvicorn` 命令
- 预发布/生产：既有 `docker-compose` 流程
- 性能观测：`docker stats`、日志采集、PG/Redis 连接与慢查询

## 7. 渐进切换节奏（建议）
- 第1天：加开关 + 注入试点 API + 本地/预发集成验证
- 第2–3天：预发小规模回放 + 性能观察
- 第4天：生产打开试点路由灰度（5–10% 流量）
- 第5–7天：扩大到全部“读类”接口
- 第2周：评估将“写类/核心检测流程”逐步接入（如需要）

## 8. 责任与交付
- 责任划分：后端（DI/接口/性能）、前端（页面与契约）、运维（发布与观测）
- 交付物：
  - 变更 PR（试点注入 + 开关）
  - 验证报告（功能一致性、性能对比、问题清单）
  - 回滚验证记录


