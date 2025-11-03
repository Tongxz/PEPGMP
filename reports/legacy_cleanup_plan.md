# 遗留清理计划（分阶段）

基于扫描结果（见 reports/legacy_cleanup_report.json/.md），制定如下分阶段清理方案。所有删除动作均先行“归档”到 archive/，验证一周无回归后再物理删除。

## 白名单（不清理）
- 约定动态加载/路由文件：src/api/routers/**, src/api/utils/**
- 核心领域/仓储/接口：src/domain/**, src/infrastructure/**, src/interfaces/**
- 运行期依赖：src/services/**（除标注为 deprecated 的示例实现）

## 第一阶段（可安全归档，预计零影响）
- 体系结构试验性模块（未在运行路径使用）
  - src/architecture/**（architecture_analyzer.py, plugin_system.py, event_system.py, dependency_injection.py）
- MLOps 示例与集成样例（不在生产路径）
  - src/mlops/**（integration_example.py, dvc_integration.py, mlflow_integration.py）
- 性能/优化实验性脚本
  - src/optimization/tensorrt_optimizer.py
- 非核心工具集（未被引用）
  - src/utils/data_collector.py, src/utils/model_optimizer.py, src/utils/gpu_acceleration.py

动作：将上述文件移动到 archive/phase1/，提交并观察 24–72 小时；若无回归，第二阶段继续。

## 第二阶段（弱耦合旧实现，已被新架构替代）
- 旧策略/服务样例：
  - src/services/detection_service_strategy.py, src/services/detection_service_repository.py
  - src/strategies/tracking/byte_tracker_strategy.py（如前端/配置未再引用）
- 旧核心管线实验件：
  - src/core/accelerated_detection_pipeline.py, src/core/performance_optimizer.py, src/core/personalization_engine.py, src/core/quality_assessor.py, src/core/rule_engine.py

动作：先全仓 grep 确认零引用；归档至 archive/phase2/，观测 1 周后删除。

## 第三阶段（按模块合并与瘦身）
- 将零散 utils/*_utils.py 合并为 utils/{image,file,video}.py 模块，保留稳定 API。
- 清理重复配置与未用 config/*。

## 验证与回滚
- 每阶段变更后：
  - 运行单测 + 三条 API 回归（summary/violations/camera_stats）
  - 线上保持 USE_DOMAIN_SERVICE=true 且 ROLLOUT_PERCENT=10% 小流量观察
- 回滚：保留 archive/ 可随时恢复；必要时将 USE_DOMAIN_SERVICE=false。

## 执行记录
- Phase 0：扫描完成，生成 legacy_cleanup_report.json/.md（本次）
- Phase 1：待执行（建议你确认白名单外文件归档）

