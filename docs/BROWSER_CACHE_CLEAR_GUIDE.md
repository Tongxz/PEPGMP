# 浏览器缓存清除指南

## 为什么需要清除缓存？

前端 JavaScript 文件更新后，浏览器可能仍然使用旧的缓存文件，导致：
- 加载旧版本的 JS 文件
- 出现 `Uncaught ReferenceError` 等错误
- 页面显示异常

## 清除缓存方法

### Chrome / Edge

#### 方法 1：快捷键（推荐）

1. 按 `Ctrl + Shift + Delete`（Windows）或 `Cmd + Shift + Delete`（Mac）
2. 选择时间范围：**全部时间**
3. 勾选：
   - ✅ 缓存的图片和文件
   - ✅ Cookie 和其他网站数据（可选）
4. 点击"清除数据"

#### 方法 2：开发者工具

1. 打开开发者工具（F12）
2. 右键点击刷新按钮
3. 选择"清空缓存并硬性重新加载"

#### 方法 3：隐身模式

1. 按 `Ctrl + Shift + N`（Windows）或 `Cmd + Shift + N`（Mac）
2. 在隐身窗口中访问 `http://localhost/`

---

### Firefox

#### 方法 1：快捷键

1. 按 `Ctrl + Shift + Delete`（Windows）或 `Cmd + Shift + Delete`（Mac）
2. 选择时间范围：**全部**
3. 勾选：
   - ✅ 缓存
   - ✅ Cookie（可选）
4. 点击"立即清除"

#### 方法 2：开发者工具

1. 打开开发者工具（F12）
2. 右键点击刷新按钮
3. 选择"清空缓存并强制刷新"

---

### Safari

1. 按 `Cmd + Option + E`（清空缓存）
2. 或者：Safari → 偏好设置 → 高级 → 勾选"在菜单栏中显示开发菜单"
3. 开发 → 清空缓存

---

## 验证缓存已清除

### 方法 1：检查网络请求

1. 打开开发者工具（F12）
2. 切换到"Network"（网络）标签
3. 勾选"Disable cache"（禁用缓存）
4. 刷新页面（F5）
5. 查看 JS 文件的请求状态：
   - ✅ 状态码 200（从服务器加载）
   - ❌ 状态码 304 或 "(from cache)"（使用缓存）

### 方法 2：检查文件哈希

1. 查看页面源代码（Ctrl+U）
2. 检查 JS 文件名中的哈希值：
   ```html
   <script src="/assets/js/vue-vendor-oq9SroqG.js"></script>
   ```
3. 刷新页面后，哈希值应该保持一致（如果文件未变化）

---

## 测试步骤

### 1. 清除缓存

按照上述方法清除浏览器缓存

### 2. 访问前端

```
http://localhost/
```

### 3. 打开开发者工具

按 `F12` 打开开发者工具

### 4. 检查控制台

切换到"Console"（控制台）标签，查看是否有错误：

**成功**：
```
无错误信息
或只有一些 warning（警告）
```

**失败**：
```
Uncaught ReferenceError: Cannot access 'ql' before initialization
```

### 5. 检查网络请求

切换到"Network"（网络）标签，查看 JS 文件加载情况：

**成功**：
```
vue-vendor-*.js  200  OK
index-*.js       200  OK
vendor-*.js      200  OK
```

**失败**：
```
某些 JS 文件 404 Not Found
或加载顺序错误
```

---

## 常见问题

### Q1: 清除缓存后仍然报错

**可能原因**：
1. 镜像本身有问题（需要重新构建）
2. 静态文件混合了多个版本
3. 服务器端缓存（Nginx）

**解决方法**：
```bash
# 在 WSL2 中
cd ~/projects/Pyt

# 重启 nginx
docker-compose -f docker-compose.prod.yml restart nginx

# 或重新部署
docker-compose -f docker-compose.prod.yml down
rm -rf frontend/dist
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

### Q2: 隐身模式可以，正常模式不行

**原因**：浏览器缓存未清除干净

**解决方法**：
1. 关闭所有浏览器窗口
2. 重新打开浏览器
3. 按 `Ctrl + Shift + Delete` 清除缓存
4. 重新访问

---

### Q3: 不同浏览器表现不同

**原因**：各浏览器缓存策略不同

**建议**：
- 开发/测试：使用 Chrome/Edge 的"禁用缓存"功能
- 生产环境：配置合理的缓存策略（Cache-Control）

---

## 开发环境最佳实践

### Chrome DevTools 设置

1. 打开开发者工具（F12）
2. 切换到"Network"标签
3. 勾选"Disable cache"（禁用缓存）
4. **保持开发者工具打开**

这样每次刷新都会从服务器重新加载文件，避免缓存问题。

### 生产环境缓存策略

在 `nginx.conf` 中配置：

```nginx
location ~* \.(js|css)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    # 使用文件哈希确保更新时自动失效
}
```

**原理**：
- 文件名包含哈希值（如 `vue-vendor-oq9SroqG.js`）
- 文件内容变化 → 哈希值变化 → 文件名变化 → 浏览器自动加载新文件
- 旧文件可以长期缓存（1年），提高性能

---

## 总结

1. **开发/测试**：始终开启"Disable cache"
2. **部署后**：清除浏览器缓存（Ctrl+Shift+Delete）
3. **生产环境**：使用文件哈希 + 长期缓存策略
