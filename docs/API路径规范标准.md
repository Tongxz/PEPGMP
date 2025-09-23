# API路径规范标准

## 1. 总体规范

### 1.1 基本格式
所有API接口路径必须遵循以下格式：
```
/api/v{version}/{module}/{action}
```

### 1.2 路径组成说明
- **api**: 固定前缀，标识这是API接口
- **v{version}**: 版本号，当前使用v1
- **{module}**: 功能模块名称，使用复数形式
- **{action}**: 具体操作，可选

### 1.3 示例
```
/api/v1/cameras          # 摄像头列表
/api/v1/cameras/{id}     # 特定摄像头
/api/v1/regions          # 区域管理
/api/v1/statistics       # 统计数据
```

## 2. 模块路径定义

### 2.1 系统管理 (System)
```
GET  /api/v1/system/health    # 系统健康检查
GET  /api/v1/system/info      # 系统信息
GET  /api/v1/system/config    # 系统配置
POST /api/v1/system/config    # 更新系统配置
```

### 2.2 摄像头管理 (Cameras)
```
GET    /api/v1/cameras           # 获取摄像头列表
POST   /api/v1/cameras           # 创建摄像头
GET    /api/v1/cameras/{id}      # 获取特定摄像头
PUT    /api/v1/cameras/{id}      # 更新摄像头
DELETE /api/v1/cameras/{id}      # 删除摄像头
GET    /api/v1/cameras/{id}/preview  # 摄像头预览
POST   /api/v1/cameras/{id}/start    # 启动摄像头
POST   /api/v1/cameras/{id}/stop     # 停止摄像头
```

### 2.3 区域管理 (Regions)
```
GET    /api/v1/regions           # 获取区域列表
POST   /api/v1/regions           # 创建区域
GET    /api/v1/regions/{id}      # 获取特定区域
PUT    /api/v1/regions/{id}      # 更新区域
DELETE /api/v1/regions/{id}      # 删除区域
```

### 2.4 统计数据 (Statistics)
```
GET /api/v1/statistics           # 获取统计数据
GET /api/v1/statistics/summary   # 获取统计摘要
GET /api/v1/statistics/events    # 获取事件统计
```

### 2.5 事件管理 (Events)
```
GET /api/v1/events               # 获取事件列表
GET /api/v1/events/recent        # 获取最近事件
GET /api/v1/events/{id}          # 获取特定事件
```

### 2.6 检测管理 (Detection)
```
POST /api/v1/detect              # 执行检测
GET  /api/v1/detect/status       # 检测状态
POST /api/v1/detect/start        # 开始检测
POST /api/v1/detect/stop         # 停止检测
```

### 2.7 用户管理 (Users)
```
GET    /api/v1/users             # 获取用户列表
POST   /api/v1/users             # 创建用户
GET    /api/v1/users/{id}        # 获取特定用户
PUT    /api/v1/users/{id}        # 更新用户
DELETE /api/v1/users/{id}        # 删除用户
```

### 2.8 认证授权 (Auth)
```
POST /api/v1/auth/login          # 用户登录
POST /api/v1/auth/logout         # 用户登出
POST /api/v1/auth/refresh        # 刷新令牌
GET  /api/v1/auth/profile        # 获取用户信息
```

### 2.9 错误监控 (Monitoring)
```
GET /api/v1/monitoring/errors    # 获取错误列表
GET /api/v1/monitoring/metrics   # 获取监控指标
GET /api/v1/monitoring/health    # 健康检查
```

### 2.10 管理功能 (Management)
```
GET  /api/v1/management/status   # 管理状态
POST /api/v1/management/restart  # 重启服务
POST /api/v1/management/backup   # 备份数据
```

## 3. HTTP方法规范

### 3.1 标准CRUD操作
- **GET**: 获取资源（查询）
- **POST**: 创建资源
- **PUT**: 更新整个资源
- **PATCH**: 部分更新资源
- **DELETE**: 删除资源

### 3.2 特殊操作
对于非标准CRUD操作，使用POST方法配合动作名称：
```
POST /api/v1/cameras/{id}/start
POST /api/v1/cameras/{id}/stop
POST /api/v1/detect/restart
```

## 4. 命名规范

### 4.1 路径命名
- 使用小写字母
- 使用连字符(-)分隔单词
- 资源名称使用复数形式
- 避免使用缩写

### 4.2 参数命名
- 使用snake_case格式
- 参数名称要有意义
- 布尔参数使用is_前缀

### 4.3 示例
```
✅ 正确：
/api/v1/camera-configs
/api/v1/detection-results
?is_active=true&max_results=10

❌ 错误：
/api/v1/camCfg
/api/v1/detRes
?active=1&max=10
```

## 5. 版本管理

### 5.1 版本策略
- 当前版本：v1
- 向后兼容的更改不需要版本升级
- 破坏性更改需要新版本
- 同时支持多个版本

### 5.2 版本升级路径
```
v1 → v2 (当有破坏性更改时)
保持v1接口可用，逐步迁移到v2
```

## 6. 响应格式规范

### 6.1 成功响应
```json
{
  "success": true,
  "data": {...},
  "message": "操作成功"
}
```

### 6.2 错误响应
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {...}
  }
}
```

## 7. 特殊接口

### 7.1 WebSocket接口
```
ws://localhost:8000/ws           # WebSocket连接
```

### 7.2 静态资源
```
/static/*                        # 静态文件
/uploads/*                       # 上传文件
```

### 7.3 健康检查
```
GET /health                      # 简单健康检查
GET /api/v1/system/health        # 详细健康检查
```

## 8. 迁移计划

### 8.1 当前不规范路径
需要修复的路径：
```
❌ /v1/system/health    → ✅ /api/v1/system/health
❌ /v1/system/info      → ✅ /api/v1/system/info
❌ /v1/system/config    → ✅ /api/v1/system/config
❌ /api/ping            → ✅ /api/v1/system/health
❌ /metrics             → ✅ /api/v1/monitoring/metrics
```

### 8.2 兼容性处理
在迁移期间，可以同时支持新旧路径：
1. 新路径作为主要接口
2. 旧路径重定向到新路径
3. 逐步废弃旧路径

## 9. 实施检查清单

### 9.1 后端检查
- [ ] 所有路由都有/api/v1前缀
- [ ] 路径命名符合规范
- [ ] HTTP方法使用正确
- [ ] 响应格式统一

### 9.2 前端检查
- [ ] 所有API调用路径正确
- [ ] HTTP客户端配置统一
- [ ] 错误处理一致
- [ ] 类型定义完整

### 9.3 文档检查
- [ ] API文档更新
- [ ] 示例代码正确
- [ ] 变更日志记录
- [ ] 迁移指南完整

---

**注意**: 所有开发人员必须严格遵守此规范，确保API接口的一致性和可维护性。
