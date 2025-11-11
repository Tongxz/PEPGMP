#!/usr/bin/env python3
"""
测试 XGBoost ML 分类器是否已正确启用
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_xgboost_import():
    """测试 XGBoost 是否已安装"""
    print("=" * 60)
    print("测试 1: XGBoost 导入")
    print("=" * 60)

    try:
        import xgboost as xgb

        print(f"✅ XGBoost {xgb.__version__} 已安装")
        return True
    except ImportError:
        print("❌ XGBoost 未安装")
        print("   安装方法: pip install -e '.[ml]' 或 pip install xgboost")
        return False


def test_model_file():
    """测试模型文件是否存在"""
    print("\n" + "=" * 60)
    print("测试 2: 模型文件")
    print("=" * 60)

    model_paths = [
        "models/handwash_xgb.json",
        "models/handwash_xgb.joblib",
    ]

    for path in model_paths:
        if Path(path).exists():
            print(f"✅ 模型文件存在: {path}")

            # 尝试加载验证
            try:
                import xgboost as xgb

                model = xgb.Booster()
                if path.endswith(".json") or path.endswith(".ubj"):
                    model.load_model(path)
                    print(f"✅ 模型文件有效: {path}")
                    return True
            except Exception as e:
                print(f"⚠️  模型文件加载失败: {e}")
                continue

    print("❌ 未找到有效的模型文件")
    print("   期望路径: models/handwash_xgb.json")
    return False


def test_config():
    """测试配置是否正确"""
    print("\n" + "=" * 60)
    print("测试 3: 配置检查")
    print("=" * 60)

    try:
        from src.config.unified_params import get_unified_params

        params = get_unified_params()

        br = params.behavior_recognition
        print(f"ML分类器启用: {br.use_ml_classifier}")
        print(f"模型路径: {br.ml_model_path}")
        print(f"时序窗口: {br.ml_window} 帧")
        print(f"融合权重: {br.ml_fusion_alpha}")

        if br.use_ml_classifier:
            print("✅ ML分类器已启用")
            return True
        else:
            print("⚠️  ML分类器未启用（在配置文件中设置 use_ml_classifier: true）")
            return False

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False


def test_behavior_recognizer():
    """测试 BehaviorRecognizer 初始化"""
    print("\n" + "=" * 60)
    print("测试 4: BehaviorRecognizer 初始化")
    print("=" * 60)

    try:
        from src.core.behavior import BehaviorRecognizer

        recognizer = BehaviorRecognizer()

        if hasattr(recognizer, "use_ml_classifier"):
            print("✅ BehaviorRecognizer 已初始化")
            print(f"   ML分类器状态: {recognizer.use_ml_classifier}")

            if recognizer.use_ml_classifier:
                if recognizer.ml_model is not None:
                    print(f"✅ ML模型已加载: {recognizer.ml_model_path}")
                    return True
                else:
                    print("⚠️  ML分类器启用但模型未加载")
                    print(f"   模型路径: {recognizer.ml_model_path}")
                    return False
            else:
                print("⚠️  ML分类器未启用")
                return False
        else:
            print("❌ BehaviorRecognizer 缺少 ML 分类器属性")
            return False

    except Exception as e:
        print(f"❌ BehaviorRecognizer 初始化失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("XGBoost ML 分类器启用状态检查")
    print("=" * 60 + "\n")

    results = {
        "XGBoost 导入": test_xgboost_import(),
        "模型文件": test_model_file(),
        "配置检查": test_config(),
        "BehaviorRecognizer": test_behavior_recognizer(),
    }

    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)

    all_passed = all(results.values())

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！XGBoost ML 分类器已正确启用！")
        print("=" * 60)
        return 0
    else:
        print("⚠️  部分测试未通过，请检查上述问题")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
