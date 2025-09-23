#!/usr/bin/env python3
"""
修复XGBoost模型加载警告
Fix XGBoost Model Loading Warning

功能：
1. 将旧版joblib保存的XGBoost模型转换为新格式
2. 使用XGBoost推荐的save_model/load_model方法
3. 保持向后兼容性
"""

import logging
import os
from pathlib import Path

import joblib
import xgboost as xgb

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_xgboost_model(old_model_path: str, new_model_path: str):
    """转换XGBoost模型格式"""
    try:
        # 加载旧模型（使用joblib）
        logger.info(f"Loading old model from {old_model_path}")
        old_model = joblib.load(old_model_path)

        # 检查是否是XGBoost模型
        if not hasattr(old_model, "save_model"):
            logger.warning(f"Model {old_model_path} is not an XGBoost model")
            return False

        # 使用XGBoost推荐的方式保存
        logger.info(f"Saving model in new format to {new_model_path}")
        old_model.save_model(new_model_path)

        # 测试加载新模型
        test_model = xgb.Booster()
        test_model.load_model(new_model_path)
        logger.info("✅ Model conversion successful")

        return True

    except Exception as e:
        logger.error(f"Failed to convert model: {e}")
        return False


def update_behavior_recognizer():
    """更新BehaviorRecognizer的模型加载代码"""
    behavior_file = Path("src/core/behavior.py")

    if not behavior_file.exists():
        logger.error("behavior.py not found")
        return False

    # 读取文件
    with open(behavior_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找并替换模型加载代码
    old_code = """                if joblib is not None and os.path.exists(self.ml_model_path):
                    self.ml_model = joblib.load(self.ml_model_path)"""

    new_code = """                if os.path.exists(self.ml_model_path):
                    # 优先使用XGBoost native格式
                    if self.ml_model_path.endswith('.json') or self.ml_model_path.endswith('.ubj'):
                        self.ml_model = xgb.Booster()
                        self.ml_model.load_model(self.ml_model_path)
                    # 向后兼容joblib格式（但会有警告）
                    elif joblib is not None and self.ml_model_path.endswith('.joblib'):
                        self.ml_model = joblib.load(self.ml_model_path)"""

    if old_code in content:
        content = content.replace(old_code, new_code)

        # 写回文件
        with open(behavior_file, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("✅ Updated behavior.py model loading code")
        return True
    else:
        logger.warning("Could not find target code in behavior.py")
        return False


def main():
    """主函数"""
    logger.info("🚀 XGBoost模型修复脚本启动")

    # 确保在项目根目录
    if not Path("pyproject.toml").exists():
        logger.error("请在项目根目录运行此脚本")
        return

    # 1. 转换现有的joblib模型为XGBoost native格式
    old_model_path = "models/handwash_xgb.joblib"
    new_model_path = "models/handwash_xgb.json"

    if Path(old_model_path).exists():
        logger.info("转换XGBoost模型格式...")
        if convert_xgboost_model(old_model_path, new_model_path):
            # 备份旧模型
            backup_path = f"{old_model_path}.backup"
            Path(old_model_path).rename(backup_path)
            logger.info(f"旧模型已备份到 {backup_path}")

            # 创建符号链接保持兼容性
            Path(old_model_path).symlink_to(Path(new_model_path).name)
            logger.info(f"创建符号链接: {old_model_path} -> {new_model_path}")
    else:
        logger.warning(f"模型文件 {old_model_path} 不存在")

    # 2. 更新配置文件中的模型路径
    config_file = Path("config/unified_params.yaml")
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config_content = f.read()

        # 更新模型路径为新格式
        if "ml_model_path: models/handwash_xgb.joblib" in config_content:
            config_content = config_content.replace(
                "ml_model_path: models/handwash_xgb.joblib",
                "ml_model_path: models/handwash_xgb.json",
            )

            with open(config_file, "w", encoding="utf-8") as f:
                f.write(config_content)

            logger.info("✅ 更新配置文件中的模型路径")

    # 3. 更新代码
    logger.info("更新模型加载代码...")
    if update_behavior_recognizer():
        logger.info("✅ 代码更新完成")

    logger.info("🎉 XGBoost模型修复完成！")
    logger.info("建议：")
    logger.info("1. 运行测试确认模型加载正常")
    logger.info("2. 今后保存XGBoost模型时使用 model.save_model() 方法")
    logger.info("3. 考虑将所有ML模型迁移到统一的native格式")


if __name__ == "__main__":
    main()
