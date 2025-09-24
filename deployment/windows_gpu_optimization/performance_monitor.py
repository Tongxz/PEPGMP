import threading
import time
from typing import Dict

import numpy as np
import torch


class GPUPerformanceMonitor:
    """GPU性能监控器"""

    def __init__(self):
        self.monitoring = False
        self.metrics = {
            "gpu_utilization": [],
            "gpu_memory_used": [],
            "gpu_temperature": [],
            "fps": [],
            "inference_times": [],
            "batch_sizes": [],
        }

    def start_monitoring(self):
        """开始监控"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                if torch.cuda.is_available():
                    # GPU利用率
                    gpu_util = torch.cuda.utilization(0)
                    self.metrics["gpu_utilization"].append(gpu_util)

                    # GPU显存使用
                    memory_info = torch.cuda.mem_get_info(0)
                    memory_used_gb = (memory_info[1] - memory_info[0]) / (1024**3)
                    self.metrics["gpu_memory_used"].append(memory_used_gb)

                    # GPU温度（需要nvidia-ml-py）
                    try:
                        import pynvml

                        pynvml.nvmlInit()
                        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                        temp = pynvml.nvmlDeviceGetTemperature(
                            handle, pynvml.NVML_TEMPERATURE_GPU
                        )
                        self.metrics["gpu_temperature"].append(temp)
                    except:
                        pass

            except Exception as e:
                print(f"监控错误: {e}")

            time.sleep(1)  # 每秒监控一次

    def get_performance_report(self) -> Dict:
        """获取性能报告"""
        if not self.metrics["gpu_utilization"]:
            return {"error": "没有监控数据"}

        return {
            "avg_gpu_utilization": np.mean(self.metrics["gpu_utilization"]),
            "max_gpu_utilization": np.max(self.metrics["gpu_utilization"]),
            "avg_memory_used_gb": np.mean(self.metrics["gpu_memory_used"]),
            "max_memory_used_gb": np.max(self.metrics["gpu_memory_used"]),
            "avg_temperature": np.mean(self.metrics["gpu_temperature"])
            if self.metrics["gpu_temperature"]
            else 0,
            "avg_fps": np.mean(self.metrics["fps"]) if self.metrics["fps"] else 0,
            "avg_inference_time_ms": np.mean(self.metrics["inference_times"])
            if self.metrics["inference_times"]
            else 0,
        }


# 使用示例
monitor = GPUPerformanceMonitor()
monitor.start_monitoring()

# 运行检测任务...
# your_detection_pipeline.process()

# 停止监控并获取报告
monitor.stop_monitoring()
report = monitor.get_performance_report()
print("性能监控报告:", report)
