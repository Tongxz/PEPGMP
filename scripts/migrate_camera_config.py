#!/usr/bin/env python3
"""
配置文件迁移脚本: enabled → active + auto_start

将旧的 enabled 字段迁移为新的 active 和 auto_start 字段
"""
import yaml
from pathlib import Path
import shutil
from datetime import datetime


def migrate_camera_config():
    """迁移摄像头配置文件"""
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config" / "cameras.yaml"
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return False
    
    print(f"📂 读取配置文件: {config_path}")
    
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    
    cameras = data.get('cameras', [])
    if not cameras:
        print("⚠️  没有摄像头配置")
        return True
    
    # 检查是否需要迁移
    need_migration = False
    for camera in cameras:
        if 'enabled' in camera:
            need_migration = True
            break
    
    if not need_migration:
        print("✅ 配置文件已经是最新格式，无需迁移")
        return True
    
    # 备份原配置
    backup_path = config_path.with_suffix(f'.yaml.bak.{datetime.now().strftime("%Y%m%d%H%M%S")}')
    shutil.copy2(config_path, backup_path)
    print(f"💾 已备份原配置到: {backup_path}")
    
    # 迁移配置
    migrated_count = 0
    for camera in cameras:
        if 'enabled' in camera:
            # enabled=true → active=true, auto_start=false (默认不自动启动)
            enabled_value = camera.pop('enabled')
            camera['active'] = enabled_value
            camera['auto_start'] = False  # 默认不自动启动，保持现有行为
            migrated_count += 1
            
            print(f"  ✓ 迁移摄像头 {camera.get('id')}: enabled={enabled_value} → active={enabled_value}, auto_start=False")
    
    # 写入新配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ 迁移完成！共迁移 {migrated_count} 个摄像头配置")
    print(f"📝 新配置已保存到: {config_path}")
    print(f"💡 提示: 如需回滚，可使用备份文件: {backup_path}")
    
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("摄像头配置迁移工具")
    print("enabled → active + auto_start")
    print("=" * 60)
    print()
    
    success = migrate_camera_config()
    
    if success:
        print("\n🎉 迁移成功！")
    else:
        print("\n❌ 迁移失败，请检查错误信息")
        exit(1)

