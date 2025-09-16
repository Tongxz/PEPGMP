#!/usr/bin/env python3
"""
依赖管理脚本
Dependency Management Script

功能：
1. 生成依赖锁定文件
2. 检查依赖安全性
3. 更新依赖版本
4. 检测依赖冲突
"""

import subprocess
import sys
from pathlib import Path
from typing import List

def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """运行命令并返回结果"""
    print(f"运行命令: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)

def generate_lock_file():
    """生成依赖锁定文件"""
    print("📦 生成依赖锁定文件...")
    
    try:
        # 生成基础依赖锁定文件
        run_command([
            "pip-compile", 
            "pyproject.toml", 
            "--output-file", "requirements.lock",
            "--resolver", "backtracking"
        ])
        
        # 生成开发依赖锁定文件  
        run_command([
            "pip-compile",
            "pyproject.toml",
            "--extra", "dev",
            "--extra", "test", 
            "--extra", "docs",
            "--output-file", "requirements-dev.lock",
            "--resolver", "backtracking"
        ])
        
        print("✅ 依赖锁定文件生成完成")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖锁定文件生成失败: {e}")
        return False
    
    return True

def check_security():
    """检查依赖安全性"""
    print("🔒 检查依赖安全性...")
    
    try:
        # 使用pip-audit检查漏洞
        result = run_command(["pip-audit", "--format", "json"], check=False)
        if result.returncode == 0:
            print("✅ 未发现已知安全漏洞")
        else:
            print("⚠️ 发现安全漏洞，请检查输出")
            print(result.stdout)
            
        # 使用safety检查
        result = run_command(["safety", "check", "--json"], check=False)
        if result.returncode == 0:
            print("✅ Safety检查通过")
        else:
            print("⚠️ Safety检查发现问题")
            print(result.stdout)
            
    except FileNotFoundError:
        print("❌ 安全检查工具未安装，请先运行: pip install pip-audit safety")
        return False
    
    return True

def check_outdated():
    """检查过时的依赖"""
    print("📊 检查过时的依赖...")
    
    try:
        result = run_command(["pip", "list", "--outdated", "--format", "json"], check=False)
        if result.stdout.strip() == "[]":
            print("✅ 所有依赖都是最新的")
        else:
            print("📋 发现可更新的依赖:")
            print(result.stdout)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 检查过时依赖失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("🚀 依赖管理脚本启动")
    print("=" * 50)
    
    # 确保在项目根目录
    project_root = Path(__file__).parent.parent
    if not (project_root / "pyproject.toml").exists():
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 切换到项目根目录
    import os
    os.chdir(project_root)
    
    success = True
    
    # 1. 生成锁定文件
    if not generate_lock_file():
        success = False
    
    print()
    
    # 2. 检查安全性
    if not check_security():
        success = False
    
    print()
    
    # 3. 检查过时依赖
    if not check_outdated():
        success = False
    
    print()
    print("=" * 50)
    if success:
        print("✅ 依赖管理检查完成")
    else:
        print("⚠️ 依赖管理检查发现问题，请查看上面的输出")
        sys.exit(1)

if __name__ == "__main__":
    main()
