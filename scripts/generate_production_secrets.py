#!/usr/bin/env python3
"""
生产环境密钥生成脚本
自动生成安全的密码、密钥和配置
"""

import secrets
import string
import sys
from pathlib import Path


def generate_password(length: int = 24) -> str:
    """生成强密码（包含大小写字母、数字和特殊字符）."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    # 确保至少包含每种类型的字符
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    # 填充剩余长度
    password += [secrets.choice(alphabet) for _ in range(length - len(password))]
    # 打乱顺序
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


def generate_secret_key(length: int = 64) -> str:
    """生成URL安全的随机密钥."""
    return secrets.token_urlsafe(length)


def generate_username() -> str:
    """生成随机管理员用户名."""
    prefixes = ["admin", "sysadmin", "root", "super"]
    suffix = secrets.token_hex(3)
    return f"{secrets.choice(prefixes)}_{suffix}"


def main():
    print("=" * 80)
    print("生产环境密钥生成器".center(80))
    print("=" * 80)
    print()
    
    # 生成各种密钥
    print("正在生成安全密钥...")
    print()
    
    secrets_data = {
        "DATABASE_PASSWORD": generate_password(32),
        "REDIS_PASSWORD": generate_password(32),
        "ADMIN_USERNAME": generate_username(),
        "ADMIN_PASSWORD": generate_password(24),
        "SECRET_KEY": generate_secret_key(64),
        "JWT_SECRET_KEY": generate_secret_key(64),
    }
    
    # 显示生成的密钥
    print("✅ 已生成以下密钥：")
    print("-" * 80)
    for key, value in secrets_data.items():
        # 隐藏部分密钥用于显示
        display_value = value[:10] + "..." + value[-10:] if len(value) > 24 else value
        print(f"{key:25} : {display_value}")
    print("-" * 80)
    print()
    
    # 询问是否保存
    response = input("是否将这些密钥保存到配置文件？(y/n) [y]: ").strip().lower()
    if response in ['', 'y', 'yes']:
        save_to_file(secrets_data)
    else:
        print("\n❌ 已取消保存")
        print("\n💡 提示：您可以手动复制上述密钥到 .env.production 文件")
        return
    
    print()
    print("=" * 80)
    print("✅ 密钥生成完成".center(80))
    print("=" * 80)
    print()
    print("📝 重要提示：")
    print("  1. 请妥善保管这些密钥，不要泄露")
    print("  2. 不要提交 .env.production 到 Git")
    print("  3. 定期更换密钥（建议每季度一次）")
    print("  4. 使用密钥管理服务（如 AWS Secrets Manager）更安全")
    print()


def save_to_file(secrets_data: dict):
    """保存密钥到文件."""
    project_root = Path(__file__).parent.parent
    env_example = project_root / ".env.production.example"
    env_production = project_root / ".env.production"
    
    # 检查文件是否存在
    if env_production.exists():
        print(f"\n⚠️  警告：{env_production} 已存在")
        response = input("是否覆盖？(y/n) [n]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("\n❌ 已取消保存")
            
            # 显示导出命令供手动使用
            print("\n💡 提示：您可以使用以下命令手动设置环境变量：")
            print()
            for key, value in secrets_data.items():
                print(f'export {key}="{value}"')
            print()
            return
    
    # 读取模板文件
    if not env_example.exists():
        print(f"\n❌ 错误：模板文件 {env_example} 不存在")
        return
    
    with open(env_example, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换占位符
    replacements = {
        "CHANGE_ME_STRONG_PASSWORD": secrets_data["DATABASE_PASSWORD"],
        "CHANGE_ME_VERY_STRONG_PASSWORD_MIN_16_CHARS": secrets_data["ADMIN_PASSWORD"],
        "CHANGE_ME_64_CHAR_RANDOM_KEY_USE_SECRETS_TOKEN_URLSAFE": secrets_data["SECRET_KEY"],
        "CHANGE_ME_ANOTHER_64_CHAR_RANDOM_KEY": secrets_data["JWT_SECRET_KEY"],
    }
    
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    
    # 同时替换第二个密码占位符（Redis）
    content = content.replace(
        "redis://:CHANGE_ME_STRONG_PASSWORD@redis:6379/0",
        f"redis://:{secrets_data['REDIS_PASSWORD']}@redis:6379/0"
    )
    
    # 可选：替换管理员用户名
    content = content.replace("ADMIN_USERNAME=admin", f"ADMIN_USERNAME={secrets_data['ADMIN_USERNAME']}")
    
    # 保存到 .env.production
    with open(env_production, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 设置文件权限（仅限Unix系统）
    try:
        import os
        os.chmod(env_production, 0o600)
        print(f"\n✅ 已保存到 {env_production}")
        print(f"✅ 文件权限已设置为 600")
    except Exception as e:
        print(f"\n✅ 已保存到 {env_production}")
        print(f"⚠️  警告：无法设置文件权限：{e}")
        print(f"   请手动执行：chmod 600 {env_production}")
    
    # 保存密钥备份（加密或安全位置）
    backup_file = project_root / "secrets" / "production_secrets_backup.txt"
    backup_file.parent.mkdir(exist_ok=True)
    
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write("# 生产环境密钥备份\n")
            f.write(f"# 生成时间: {__import__('datetime').datetime.now().isoformat()}\n")
            f.write("# ⚠️ 警告：妥善保管此文件，不要泄露\n\n")
            for key, value in secrets_data.items():
                f.write(f"{key}={value}\n")
        
        import os
        os.chmod(backup_file, 0o600)
        print(f"✅ 密钥备份已保存到 {backup_file}")
        print(f"   （已添加到 .gitignore）")
    except Exception as e:
        print(f"⚠️  警告：无法保存备份：{e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
