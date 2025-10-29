# 项目统一知识库 (INDEX)

本文档是整个项目的核心导航地图，旨在帮助所有成员快速定位信息。
请将此文件作为您探索项目文档的起点。

---

### **核心门户与协作 (Root Directory)**

*   **[项目概览 (README)](../README.md)**: 30秒了解项目，5分钟本地运行。
*   **[贡献者指南 (CONTRIBUTING)](../CONTRIBUTING.md)**: 开发流程、代码规范、Git工作流。
*   **[版本更新记录 (CHANGELOG)](../CHANGELOG.md)**: 查看各版本的功能变更。

---

### **1. 架构设计 (`1_architecture`)**

*本部分阐述系统的高层设计、原则和“为什么”。*

*   **[系统架构设计](./1_architecture/system_design.md)**: (建议整合 `架构图.md` 和 `架构优化方案.md` 的核心内容)
*   **[数据流说明](./1_architecture/data_flow.md)**: (建议从 `系统架构深度分析-启动检测流程.md` 中提取)

---

### **2. 操作指南 (`2_guides`)**

*本部分提供针对具体任务的、一步步的操作手册。*

*   **[部署指南](./2_guides/deployment.md)**: (建议整合 `生产环境部署指南.md` 等)
*   **[新人入职指南 (Onboarding)](./2_guides/onboarding.md)**: (建议新建，作为新成员的导航)
*   **[模型训练指南](./2_guides/training_model.md)**: (建议整合 `发网检测与模型训练指南.md`)

---

### **3. 参考手册 (`3_reference`)**

*本部分提供精确、详尽、不含糊的技术参考。*

*   **[API接口文档](./3_reference/api_spec.md)**: (建议整合 `API_文档.md` 等，并最终由代码生成)
*   **[配置项参考](./3_reference/config.md)**: (建议基于 `.env.example` 等文件创建)
*   **[模型卡 (Model Card)](./3_reference/model_card.md)**: (建议整合 `模型使用与准确度分析.md`)

---

### **4. 专题解析 (`4_explanation`)**

*本部分对项目中复杂的技术点或概念进行深入探讨。*

*   **[调度器设计深度解析](./4_explanation/scheduler_deep_dive.md)**: (建议从 `架构优化方案.md` 中提取)

---

### **测试 (`tests`)**

*   **[测试策略与范围](../tests/README.md)**: 描述了项目的测试方法论。
