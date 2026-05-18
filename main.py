# -*- coding: utf-8 -*-
"""
main.py
========
CLI 入口。

用于在终端中执行完整管线或做环境诊断，便于脱离图形界面验证后端行为。

使用方式:
    python main.py --source "E:\\data\\raw_audio" --output "E:\\data\\output"
    python main.py --source "E:\\data\\raw_audio" --output "E:\\data\\output" --preset quality --lang ja
    python main.py --check-env   (仅执行环境诊断)
"""

import argparse
import sys

from core_pipeline import (
    Pipeline,
    PipelineConfig,
    QualityPreset,
    EnvironmentChecker,
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="VocalSieve -- 高质量人声语料筛选工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--source", "-s",
        type=str,
        help="原始音频文件所在目录",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="筛选结果输出目录",
    )
    parser.add_argument(
        "--preset", "-p",
        type=str,
        choices=["performance", "balanced", "quality"],
        default="balanced",
        help="质量预设 (默认: balanced)",
    )
    parser.add_argument(
        "--lang", "-l",
        type=str,
        default="auto",
        help="目标语种代码，如 ja/zh/en/auto (默认: auto)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=1200,
        help="Whisper 阶段最终取前 N 条 (默认: 1200)",
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="仅执行环境诊断，不启动管线",
    )

    return parser.parse_args()


def run_env_check() -> None:
    """仅执行环境诊断并打印结果。"""
    checker = EnvironmentChecker()
    report = checker.check()

    print(f"\n{'=' * 50}")
    print("环境诊断报告")
    print(f"{'=' * 50}")
    print(f"  Python 版本:    {report.python_version} {'[OK]' if report.python_ok else '[WARN]'}")
    print(f"  PyTorch:        {'已安装 ' + (report.torch_version or '') if report.torch_available else '未安装'}")
    print(f"  CUDA GPU:       {report.gpu_name or '未检测到'}")
    if report.gpu_vram_mb:
        print(f"  GPU 显存:       {report.gpu_vram_mb} MB")
    print(f"  Whisper:        {'已安装' if report.whisper_available else '未安装'}")
    print(f"  FFmpeg:         {report.ffmpeg_path or '未找到'}")
    print(f"{'=' * 50}")

    if report.issues:
        print("\n  问题列表:")
        for issue in report.issues:
            print(f"    - {issue}")

    recommended = checker.recommend_preset(report)
    print(f"\n  推荐预设: {recommended.value}")
    print(f"{'=' * 50}")


def main() -> None:
    """CLI 主入口函数。"""
    args = parse_args()

    if args.check_env:
        run_env_check()
        return

    if not args.source or not args.output:
        print("错误: 必须指定 --source 和 --output 参数")
        print("使用 --help 查看完整用法")
        sys.exit(1)

    preset_map = {
        "performance": QualityPreset.PERFORMANCE,
        "balanced": QualityPreset.BALANCED,
        "quality": QualityPreset.QUALITY,
    }

    config = PipelineConfig(
        source_dir=args.source,
        output_dir=args.output,
        preset=preset_map[args.preset],
        target_language=args.lang,
        top_n=args.top_n,
    )

    pipeline = Pipeline(config)
    result = pipeline.run()

    print(f"\n{'=' * 50}")
    if result.success:
        print(f"管线执行成功!")
        print(f"最终输出目录: {result.final_output_dir}")
        if result.whisper_result:
            print(f"最终选取文件数: {result.whisper_result.accepted_count}")
    elif result.cancelled:
        print("管线已被用户取消")
    else:
        print(f"管线执行失败: {result.error_message}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
