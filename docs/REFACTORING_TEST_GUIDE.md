# 重构后测试指南

## 🎯 测试目标

验证重构后的架构能够正常工作，并且功能与重构前一致。

---

## ✅ 快速测试清单

### 1. 代码检查
```bash
# 检查语法错误
python -m py_compile main.py
python -m py_compile src/application/detection_loop_service.py
python -m py_compile src/application/video_stream_application_service.py

# 检查导入
python -c "from src.application.detection_loop_service import DetectionLoopService"
python -c "from src.application.video_stream_application_service import get_video_stream_service"
```

### 2. 基础功能测试

#### 2.1 启动检测（使用新架构）
```bash
# 启动摄像头检测
python main.py --mode detection --source 0 --camera-id test_cam

# 检查日志输出
# 应该看到：🚀 使用新架构运行检测循环
tail -f logs/detect_test_cam.log
```

#### 2.2 检查API服务
```bash
# 启动API服务
python main.py --mode server

# 在另一个终端测试
curl http://localhost:8000/api/v1/cameras
```

#### 2.3 前端测试
```bash
# 启动前端
cd frontend
npm run dev

# 打开浏览器
# http://localhost:5173
# 测试：
# 1. 启动摄像头
# 2. 停止摄像头
# 3. 查看视频流
# 4. 查看日志
```

---

## 📋 详细测试步骤

### 测试 1: DetectionLoopService 基础功能

**目标**：验证新的检测循环服务可以正常工作

**步骤**：
1. 启动检测：
   ```bash
   python main.py --mode detection --source 0 --camera-id cam0
   ```

2. 观察日志输出：
   ```
   ✅ 应该看到：
   - "🚀 使用新架构运行检测循环"
   - "检测循环服务已初始化: camera=cam0"
   - "视频信息: WIDTHxHEIGHT @ XFPS"
   - "开始视频处理循环..."

   ❌ 不应该看到：
   - "⚠️ 使用旧实现运行检测循环"
   - "新架构服务不可用"
   ```

3. 检查摄像头是否正常释放：
   ```bash
   # Ctrl+C 停止
   # 应该看到：
   - "收到信号 2，准备退出..."
   - "收到退出信号，立即释放摄像头..."
   - "摄像头已释放"
   - "资源释放完成"
   ```

**预期结果**：
- ✅ 检测循环正常运行
- ✅ 摄像头资源正确释放
- ✅ 日志显示使用新架构

---

### 测试 2: VideoStreamApplicationService

**目标**：验证视频流推送功能正常

**步骤**：
1. 启动检测（确保Redis正在运行）：
   ```bash
   # 启动Redis（如果还没启动）
   redis-server

   # 启动检测
   python main.py --mode detection --source 0 --camera-id cam0
   ```

2. 启动API服务（另一个终端）：
   ```bash
   python main.py --mode server
   ```

3. 打开前端并查看视频流：
   - 浏览器打开 http://localhost:5173
   - 点击"启动"按钮启动摄像头（如果通过API启动）
   - 点击"📹 查看视频"按钮

4. 检查日志：
   ```bash
   tail -f logs/detect_cam0.log

   # 应该看到：
   - "✓ 视频流服务已启用"
   - "视频帧已推送: camera=cam0"
   ```

**预期结果**：
- ✅ 视频流实时显示
- ✅ FPS显示正常（>5 FPS）
- ✅ 延迟在可接受范围内

---

### 测试 3: CameraControlService 业务规则

**目标**：验证增强的业务规则验证

#### 测试 3.1: 重复启动防护
```bash
# 终端1：启动摄像头
python main.py --mode detection --source 0 --camera-id cam0

# 终端2：尝试再次启动（通过API）
curl -X POST http://localhost:8000/api/v1/cameras/cam0/start

# 应该返回错误：
{
  "detail": "摄像头 cam0 已在运行（PID: xxxxx），请先停止后再启动"
}
```

#### 测试 3.2: 停止未运行的摄像头
```bash
# 确保摄像头未运行
curl -X POST http://localhost:8000/api/v1/cameras/cam0/stop

# 应该返回成功（不报错）：
{
  "ok": true,
  "running": false,
  "message": "摄像头未在运行"
}
```

#### 测试 3.3: 资源限制
```bash
# 修改 CameraControlService.py 中的 MAX_CONCURRENT_CAMERAS = 2
# 启动3个摄像头，第3个应该失败

curl -X POST http://localhost:8000/api/v1/cameras/cam0/start
curl -X POST http://localhost:8000/api/v1/cameras/cam1/start
curl -X POST http://localhost:8000/api/v1/cameras/cam2/start

# 第3个应该返回错误：
{
  "detail": "系统资源不足：当前运行 2 个摄像头，已达上限 2"
}
```

**预期结果**：
- ✅ 重复启动被阻止
- ✅ 停止未运行摄像头不报错
- ✅ 资源限制生效

---

### 测试 4: 回退机制

**目标**：验证新架构出错时能正确回退到旧实现

**步骤**：
1. 临时重命名新服务文件（模拟不可用）：
   ```bash
   mv src/application/detection_loop_service.py src/application/detection_loop_service.py.bak
   ```

2. 启动检测：
   ```bash
   python main.py --mode detection --source 0 --camera-id cam0
   ```

3. 观察日志：
   ```
   应该看到：
   - "新架构服务不可用: No module named 'src.application.detection_loop_service'，回退到旧实现"
   - "⚠️ 使用旧实现运行检测循环"
   ```

4. 恢复文件：
   ```bash
   mv src/application/detection_loop_service.py.bak src/application/detection_loop_service.py
   ```

**预期结果**：
- ✅ 自动回退到旧实现
- ✅ 功能仍然正常
- ✅ 日志清楚标识使用旧实现

---

### 测试 5: 前端集成测试

**目标**：验证前端所有功能正常

**步骤**：

1. **启动摄像头**
   - 点击"启动"按钮
   - 状态变为"🟢 运行中"
   - 显示PID

2. **查看视频流**
   - 点击"📹 查看视频"
   - 弹窗显示实时视频
   - FPS显示正常

3. **查看日志**
   - 点击"日志"按钮
   - 显示最新日志内容
   - 可以滚动查看

4. **停止摄像头**
   - 点击"停止"按钮
   - 状态变为"⚪ 已停止"
   - 视频流断开连接

5. **前端状态刷新**
   - 停止后自动刷新状态
   - 轮询确认进程已停止
   - 状态更新及时（1-2秒内）

**预期结果**：
- ✅ 所有按钮功能正常
- ✅ 状态显示准确
- ✅ 视频流流畅
- ✅ 日志实时更新

---

## 🐛 常见问题排查

### 问题 1: 导入错误
```
ImportError: No module named 'src.application.detection_loop_service'
```

**解决**：
```bash
# 确保在项目根目录
cd /Users/zhou/Code/Pyt

# 检查文件是否存在
ls -l src/application/detection_loop_service.py

# 检查Python路径
python -c "import sys; print('\n'.join(sys.path))"
```

### 问题 2: 视频流不显示
```
WebSocket连接成功，但没有视频画面
```

**解决**：
```bash
# 1. 检查Redis是否运行
redis-cli ping
# 应该返回：PONG

# 2. 检查检测进程是否推送
tail -f logs/detect_cam0.log | grep "视频帧已推送"

# 3. 检查VideoStreamManager是否接收
# 查看API服务日志
```

### 问题 3: 摄像头未释放
```
停止后，摄像头指示灯仍亮
```

**解决**：
```bash
# 1. 检查进程是否真正停止
ps aux | grep "main.py.*detection"

# 2. 手动kill进程
kill -9 <PID>

# 3. 检查macOS权限
# 系统偏好设置 > 安全性与隐私 > 摄像头
```

### 问题 4: 前端停止摄像头后状态未更新
```
点击停止后，状态仍显示"运行中"
```

**解决**：
- 等待1-2秒（前端有延迟和轮询机制）
- 手动刷新页面
- 检查后端日志是否有错误

---

## 📊 性能基准测试

### 检测性能
```bash
# 运行5分钟，记录指标
python main.py --mode detection --source 0 --camera-id cam0

# 检查日志中的性能统计
grep "性能统计" logs/detect_cam0.log

# 应该看到：
# 平均FPS > 20 （取决于硬件）
# CPU使用率 < 80%
# 内存稳定，无泄漏
```

### 视频流性能
```bash
# 打开浏览器开发者工具 > Network > WS
# 连接视频流，观察：
# - 帧率：10-15 FPS
# - 每帧大小：10-50 KB
# - 延迟：< 200ms
```

---

## ✅ 测试通过标准

所有测试通过的标准：

- [ ] 新架构正常启动（日志显示 🚀）
- [ ] 检测功能正常（能检测到人、发网等）
- [ ] 视频流正常显示
- [ ] 摄像头正确释放（退出后指示灯熄灭）
- [ ] 前端所有按钮功能正常
- [ ] 停止后状态及时更新
- [ ] 业务规则验证生效（重复启动被阻止）
- [ ] 回退机制正常（新服务不可用时）
- [ ] 性能指标在正常范围内
- [ ] 无明显错误或警告日志

---

## 📝 测试报告模板

```markdown
# 重构测试报告

## 测试环境
- 操作系统：macOS 14.6.0
- Python版本：3.10.x
- 摄像头：内置摄像头 / USB摄像头
- 测试时间：2025-11-04

## 测试结果

### 1. DetectionLoopService
- [x] 新架构启动成功
- [x] 检测循环正常运行
- [x] 摄像头资源正确释放

### 2. VideoStreamApplicationService
- [x] 视频流推送成功
- [x] 前端正常显示
- [x] FPS: 12 FPS（正常）

### 3. CameraControlService
- [x] 重复启动防护生效
- [x] 停止未运行摄像头不报错
- [x] 资源限制正常

### 4. 回退机制
- [x] 新服务不可用时自动回退
- [x] 旧实现功能正常

### 5. 前端集成
- [x] 启动/停止功能正常
- [x] 视频流查看正常
- [x] 日志查看正常
- [x] 状态刷新及时

## 问题记录
无

## 性能指标
- 平均FPS：23 FPS
- CPU使用率：65%
- 内存使用：稳定在 1.2GB

## 结论
✅ 所有测试通过，重构成功！
```

---

## 🎉 测试完成后

1. **提交代码**：
   ```bash
   git add .
   git commit -m "refactor: 重构检测循环，提升架构质量

   - 创建 DetectionLoopService 独立服务
   - 创建 VideoStreamApplicationService 视频流服务
   - 增强 CameraControlService 业务规则验证
   - 修复摄像头资源释放问题
   - 添加新架构/旧实现灰度切换

   详见：docs/REFACTORING_SUMMARY.md"
   ```

2. **更新文档**：
   - ✅ 架构评审报告
   - ✅ 重构总结
   - ✅ 测试指南

3. **监控运行**：
   - 在生产环境运行几天
   - 监控日志和性能指标
   - 收集用户反馈

---

## 📚 相关文档

- [重构总结](./REFACTORING_SUMMARY.md)
- [架构评审报告](./CAMERA_DETECTION_FLOW_ARCHITECTURE_REVIEW.md)
- [视频流修复报告](./VIDEO_STREAM_FIX_REPORT.md)
