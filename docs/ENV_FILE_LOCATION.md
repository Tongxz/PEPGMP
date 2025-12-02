# .env.production 文件位置说明

## 文件创建位置

脚本 `generate_production_config.sh` 会在**运行脚本时的当前工作目录**创建 `.env.production` 文件。

### 示例

如果你在 WSL Ubuntu 中运行：

```bash
# 在 /mnt/f/code/PythonCode/Pyt 目录运行
cd /mnt/f/code/PythonCode/Pyt
bash scripts/generate_production_config.sh
```

那么文件会创建在：
- **WSL 路径**: `/mnt/f/code/PythonCode/Pyt/.env.production`
- **Windows 路径**: `F:\Code\PythonCode\Pyt\.env.production`

## 检查文件是否存在

### 方法 1: 在 WSL 中检查

```bash
cd /mnt/f/code/PythonCode/Pyt

# 检查文件是否存在
ls -la .env.production

# 如果文件存在，查看内容
cat .env.production | head -20

# 检查文件权限
stat .env.production
```

### 方法 2: 在 Windows 中检查

在 Windows PowerShell 或文件资源管理器中：

```powershell
# 在 PowerShell 中
cd F:\Code\PythonCode\Pyt
Get-ChildItem -Force .env.production

# 查看文件内容（前20行）
Get-Content .env.production | Select-Object -First 20
```

**注意**: `.env.production` 文件可能：
- 被 Windows 文件资源管理器隐藏（因为是隐藏文件，以 `.` 开头）
- 需要显示隐藏文件才能看到

### 方法 3: 使用查找脚本

```bash
cd /mnt/f/code/PythonCode/Pyt
bash scripts/find_env_file.sh
```

## 文件权限

脚本会设置文件权限为 `600`（只有所有者可以读写），这是安全最佳实践。

在 Windows 文件系统中，权限可能显示不同，但功能正常。

## 如果文件不存在

如果文件确实不存在，可能的原因：

1. **脚本执行失败但没有报错**
   - 检查脚本输出是否有错误信息
   - 重新运行脚本并观察输出

2. **文件创建在错误的位置**
   - 检查脚本执行时的工作目录
   - 使用 `pwd` 命令确认当前目录

3. **权限问题**
   - 确保有写入权限
   - 尝试手动创建测试文件：`touch test.txt`

## 重新生成文件

如果文件不存在或需要重新生成：

```bash
cd /mnt/f/code/PythonCode/Pyt

# 确认当前目录
pwd

# 重新运行脚本
bash scripts/generate_production_config.sh

# 确认文件已创建
ls -la .env.production
```

## 复制到部署目录

如果需要将文件复制到 WSL Ubuntu 的部署目录：

```bash
# 从 Windows 项目目录复制到 WSL 部署目录
cp /mnt/f/code/PythonCode/Pyt/.env.production ~/projects/Pyt/.env.production

# 设置正确的权限
chmod 600 ~/projects/Pyt/.env.production

# 验证
ls -la ~/projects/Pyt/.env.production
```

