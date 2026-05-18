import sys
import shutil
import os

print("=" * 40)
print("环境诊断 (Final Environment Check)")
print("=" * 40)

print(f"Python 版本:\t{sys.version.split()[0]}")
if sys.version_info.major == 3 and sys.version_info.minor == 10:
    print("   -> [OK] 版本正确 (3.10)")
else:
    print("   -> [WARN] 不是 Python 3.10，可能会有兼容性风险")

print("-" * 20)

try:
    import torch

    print(f"PyTorch 版本:\t{torch.__version__}")

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        print(f"显卡状态:\t[OK] 已检测到 GPU")
        print(f"   -> 型号: {gpu_name}")

        x = torch.rand(5, 3).cuda()
        print("   -> GPU 运算测试: 通过")
    else:
        print("显卡状态:\t[WARN] 未检测到 GPU (将使用 CPU，速度会慢)")
except ImportError:
    print("PyTorch:\t[ERROR] 未安装 (ImportError)")
except Exception as e:
    print(f"PyTorch:\t[ERROR] 发生错误: {e}")

print("-" * 20)

try:
    import whisper

    print(f"Whisper 库:\t[OK] 已安装")

    if shutil.which("ffmpeg"):
        print(f"FFmpeg 工具:\t[OK] 已检测到")
    else:
        if os.path.exists("ffmpeg.exe"):
            print(f"FFmpeg 工具:\t[OK] 在当前目录下找到")
        else:
            print(f"FFmpeg 工具:\t[ERROR] 未找到 (Whisper 无法运行)")
            print("   -> 请下载 ffmpeg.exe 并放到此脚本旁边")
except ImportError:
    print(f"Whisper 库:\t[ERROR] 未安装")

print("=" * 40)
print("诊断结束。如果以上全是 [OK]，即可运行筛选脚本。")
