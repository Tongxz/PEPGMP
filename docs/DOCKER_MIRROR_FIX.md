# Docker 镜像源配置问题解决方案

## 问题描述

构建 Docker 镜像时可能出现以下错误：

### 后端镜像构建错误
```
ERROR: failed to solve: python:3.10-slim-bookworm: failed to resolve source metadata for docker.io/library/python:3.10-slim-bookworm: unexpected status from HEAD request to https://5gmxobzm.mirror.aliyuncs.com/v2/library/python/manifests/3.10-slim-bookworm?ns=docker.io: 403 Forbidden
```

### 前端镜像构建错误
```
ERROR: failed to solve: node:20-alpine: failed to resolve source metadata for docker.io/library/node:20-alpine: unexpected status from HEAD request to https://5gmxobzm.mirror.aliyuncs.com/v2/library/node/manifests/20-alpine?ns=docker.io: 403 Forbidden
```

这是因为配置的阿里云镜像源返回 403 错误，可能是：
- 镜像源已失效
- 需要认证
- 网络问题

## 解决方案

### 方案1: 修改 Docker Desktop 镜像源配置（推荐）

1. **打开 Docker Desktop**
2. **进入设置**：点击右上角设置图标 ⚙️
3. **Docker Engine**：在左侧菜单选择 "Docker Engine"
4. **修改配置**：在 JSON 配置中添加或修改 `registry-mirrors`：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

5. **应用并重启**：点击 "Apply & Restart"

### 方案2: 临时禁用镜像源，使用 Docker Hub 官方源

1. **打开 Docker Desktop 设置**
2. **Docker Engine**：清空或注释掉 `registry-mirrors` 配置：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false
}
```

3. **应用并重启**

### 方案3: 使用代理构建（如果有代理）

在 PowerShell 中设置代理环境变量后构建：

```powershell
$env:HTTP_PROXY="http://proxy:port"
$env:HTTPS_PROXY="http://proxy:port"
.\scripts\build_prod_only.ps1
```

### 方案4: 手动拉取基础镜像

在构建前先手动拉取基础镜像：

**后端镜像：**
```powershell
docker pull python:3.10-slim-bookworm
```

**前端镜像：**
```powershell
docker pull node:20-alpine
docker pull nginx:1.27-alpine
```

**然后运行构建脚本：**
```powershell
.\scripts\build_prod_only.ps1
```

**注意**：脚本已自动包含预拉取功能，但如果镜像源配置有问题，可以手动拉取后再构建。

## 推荐的镜像源列表

以下是中国大陆可用的 Docker 镜像源（按推荐顺序）：

1. **中科大镜像源**（推荐）
   ```
   https://docker.mirrors.ustc.edu.cn
   ```

2. **网易镜像源**
   ```
   https://hub-mirror.c.163.com
   ```

3. **百度云镜像源**
   ```
   https://mirror.baidubce.com
   ```

4. **Docker 官方源**（如果网络允许）
   ```
   https://registry-1.docker.io
   ```

## 验证配置

配置完成后，验证镜像源是否生效：

```powershell
docker info | Select-String -Pattern "Registry"
```

或者测试拉取镜像：

```powershell
docker pull python:3.10-slim-bookworm
```

## 注意事项

1. **Windows Docker Desktop**：配置在 Docker Desktop 的图形界面中，不需要手动编辑配置文件
2. **多个镜像源**：可以配置多个镜像源，Docker 会按顺序尝试
3. **网络环境**：如果使用 VPN 或代理，可能需要配置 Docker 的代理设置
4. **镜像源稳定性**：不同镜像源的稳定性和速度可能不同，建议多配置几个备用

## Debian 软件包源问题

如果构建过程中出现 `502 Bad Gateway` 或 `Failed to fetch` 错误（来自 `deb.debian.org`），这是 Debian 软件包源的问题。

### 解决方案

**Dockerfile 已自动配置国内镜像源**（清华镜像），如果仍有问题：

1. **手动切换镜像源**：编辑 `Dockerfile.prod`，修改镜像源配置：

```dockerfile
# 使用中科大镜像（备选）
RUN sed -i 's|http://deb.debian.org|https://mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http://security.debian.org|https://mirrors.ustc.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources
```

2. **使用网易镜像**：
```dockerfile
RUN sed -i 's|http://deb.debian.org|https://mirrors.163.com|g' /etc/apt/sources.list.d/debian.sources
```

3. **使用阿里云镜像**：
```dockerfile
RUN sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources
```

4. **临时使用官方源**（如果网络允许）：
```dockerfile
# 注释掉镜像源配置行，使用默认官方源
# RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' ...
```

## 故障排查

如果仍然无法拉取镜像：

1. **检查网络连接**：
   ```powershell
   Test-NetConnection docker.mirrors.ustc.edu.cn -Port 443
   Test-NetConnection mirrors.tuna.tsinghua.edu.cn -Port 443
   ```

2. **检查 Docker 服务状态**：
   ```powershell
   docker info
   ```

3. **清除 Docker 缓存**：
   ```powershell
   docker system prune -a
   ```

4. **查看详细错误信息**：
   ```powershell
   docker pull python:3.10-slim-bookworm --debug
   ```

5. **测试 Debian 镜像源**：
   ```powershell
   # 在容器中测试
   docker run --rm python:3.10-slim-bookworm bash -c "apt-get update"
   ```

