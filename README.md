# 人体行为检测系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/Framework-FastAPI-green.svg" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/AI-PyTorch-orange.svg" alt="PyTorch"/>
  <img src="https://img.shields.io/badge/License-MIT-lightgrey.svg" alt="License: MIT"/>
</p>

一个基于深度学习的企业级实时人体行为检测系统，专注于工业环境中的安全合规监控。支持发网佩戴、洗手行为等多种场景的智能识别与分析。

---

## ✨ 核心功能

- **多目标实时检测**: 基于YOLOv8的高性能人体检测，并支持GPU加速。
- **多行为复合识别**: 支持发网佩戴、洗手、手部消毒等多种行为的复合检测。
- **高精度姿态分析**: 集成MediaPipe和YOLOv8-Pose，实现高精度姿态估计。
- **可配置监控区域**: 支持自定义多边形监控区域，专注于关键区域的检测。
- **企业级部署**: 提供完整的Docker和Docker Compose部署方案，支持生产环境。
- **完善的API**: 提供丰富的RESTful API和WebSocket接口，易于集成。

## 🚀 快速上手

我们提供基于 Docker Compose 的一键启动方式，让您在5分钟内将整个系统运行起来。

**前提条件**: 已安装 [Docker](https://www.docker.com/) 和 [Docker Compose](https://docs.docker.com/compose/)。

```bash
# 1. 克隆项目
git clone <your-project-repository-url>
cd <project-directory>

# 2. 复制并配置您的生产环境变量
# (请务必修改.env.prod中的密码和密钥)
cp config/production.env.example .env.prod

# 3. 一键启动所有服务 (包括API后端, 数据库, Redis等)
docker-compose -f docker-compose.prod.yml up -d
```

服务启动后，您可以访问：
- **前端界面**: `http://localhost:8080`
- **API 文档**: `http://localhost:8000/docs`

---

## 📚 深入了解

想要更深入地了解项目的设计、部署和贡献方式吗？我们为您准备了全新的、结构化的文档中心。

- **[➡️ 完整知识库 (docs/INDEX.md)](./docs/INDEX.md)**: **所有开发者的必读入口。** 这里包含了项目架构、部署指南、模型说明等所有核心文档。

- **[➡️ 贡献者指南 (CONTRIBUTING.md)](./CONTRIBUTING.md)**: 如果您希望为项目贡献代码，请从这里开始。它详细说明了开发环境搭建、代码规范和Git工作流。

## 🛠️ 技术栈

- **后端**: FastAPI, Python 3.8+, PyTorch, Ultralytics (YOLOv8), MediaPipe
- **前端**: Vue 3, Vite, TypeScript, Naive UI
- **基础设施**: Docker, PostgreSQL, Redis, Nginx

## 📄 许可证

本项目采用 [MIT 许可证](./LICENSE)。