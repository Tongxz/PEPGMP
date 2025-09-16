@echo off
REM Windows GPU优化环境设置脚本
echo 🚀 设置Windows GPU优化环境...

REM 设置CUDA环境变量
set CUDA_LAUNCH_BLOCKING=0
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512,roundup_power2_divisions:16
set CUBLAS_WORKSPACE_CONFIG=:16:8
set CUDA_MODULE_LOADING=LAZY
set TORCH_CUDNN_V8_API_ENABLED=1

REM 设置并行处理优化
set OMP_NUM_THREADS=8
set MKL_NUM_THREADS=8
set NUMEXPR_MAX_THREADS=8

echo ✅ GPU优化环境设置完成
echo GPU数量: 未知
echo 总显存: 0.0GB

REM 运行检测程序
python main.py --mode detection --optimize-gpu
