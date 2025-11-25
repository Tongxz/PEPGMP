# 视频流Redis Docker环境修复指南

## 问题分析

### Redis运行状态 ✅
- Redis容器正在运行：`pyt-redis-dev`
- 端口映射：`0.0.0.0:6379->6379/tcp`
- 容器状态：健康（healthy）

### Redis配置
- **密码**：`pepgmp_dev_redis`（从docker-compose.yml）
- **端口**：6379（映射到主机的6379）
- **数据库**：0（默认）

### 问题
1. **检测进程未设置Redis密码**：检测进程在本地运行，需要连接到Docker中的Redis，需要密码
2. **环境变量缺失**：检测进程启动时可能没有设置 `REDIS_PASSWORD` 或 `REDIS_URL`

## 解决方案

### 方案1：设置环境变量（推荐）

在启动检测进程之前，设置Redis连接环境变量：

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=pepgmp_dev_redis
export REDIS_DB=0

# 或者使用URL格式
export REDIS_URL=redis://:pepgmp_dev_redis@localhost:6379/0
```

### 方案2：修改LocalProcessExecutor传递环境变量

在 `src/services/executors/local.py` 中，确保检测进程启动时继承Redis环境变量：

```python
# 在_build_command方法中，添加Redis环境变量
env = os.environ.copy()
# 如果REDIS_URL不存在，尝试从单独的环境变量构建
if "REDIS_URL" not in env:
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    redis_password = os.getenv("REDIS_PASSWORD", "pepgmp_dev_redis")  # 默认密码
    if redis_password:
        env["REDIS_URL"] = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        env["REDIS_URL"] = f"redis://{redis_host}:{redis_port}/{redis_db}"
```

### 方案3：创建.env文件

在项目根目录创建 `.env` 文件（如果不存在）：

```bash
# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=pepgmp_dev_redis
REDIS_DB=0
REDIS_URL=redis://:pepgmp_dev_redis@localhost:6379/0

# 视频流配置
VIDEO_STREAM_USE_REDIS=1
VIDEO_STREAM_INTERVAL=3
VIDEO_STREAM_QUALITY=60
VIDEO_STREAM_WIDTH=800
VIDEO_STREAM_HEIGHT=450
```

然后在启动API服务器时，确保加载 `.env` 文件。

## 验证步骤

### 1. 测试Redis连接

```bash
redis-cli -h localhost -p 6379 -a pepgmp_dev_redis ping
# 应该返回 PONG
```

### 2. 检查环境变量

在检测进程启动前，检查环境变量：

```bash
echo $REDIS_URL
echo $REDIS_PASSWORD
```

### 3. 查看检测进程日志

重启检测进程后，查看日志：

```bash
tail -f logs/detect_vid1.log | grep -i "redis\|video\|stream"
```

应该看到：
- `Redis发布成功: channel=video:vid1, subscribers=X`
- `视频帧已通过Redis推送: camera=vid1`

### 4. 查看API服务器日志

查看API服务器日志，确认Redis订阅正常：

```bash
# 查找Redis订阅相关日志
grep -i "redis\|video-stream" <API服务器日志>
```

应该看到：
- `视频流Redis订阅已启动`
- `Redis已接收帧: X (camera=vid1)`

## 快速修复

### 立即修复（临时方案）

在启动检测进程之前，设置环境变量：

```bash
export REDIS_PASSWORD=pepgmp_dev_redis
export REDIS_URL=redis://:pepgmp_dev_redis@localhost:6379/0
```

然后重启检测进程。

### 永久修复（推荐）

修改 `src/services/executors/local.py`，确保检测进程启动时自动设置Redis环境变量。
