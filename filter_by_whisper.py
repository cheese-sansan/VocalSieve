import os
import re
import shutil

import torch
import whisper
from tqdm import tqdm


# Legacy standalone script. The maintained implementation lives in core_pipeline.
SOURCE_FOLDER = r"E:\sound\vo\say-music\Approved_Elite"
TARGET_FOLDER = r"E:\sound\vo\say-music\Final_ASR_Selected_say_music"
TARGET_COUNT = 1200
MODEL_SIZE = "small"


# ===========================================

def contains_repeating_chars(text, threshold=4):
    """检测是否包含连续重复字符。"""
    return re.search(r'(.)\1{' + str(threshold - 1) + r',}', text) is not None


def asr_filter():
    print(f"[INFO] 正在加载 Whisper 模型 ({MODEL_SIZE})...")

    if torch.cuda.is_available():
        print(f"[OK] GPU 加速: {torch.cuda.get_device_name(0)}")
        device = "cuda"
    else:
        print("[WARN] 未检测到 GPU，将使用 CPU 运行")
        device = "cpu"

    try:
        model = whisper.load_model(MODEL_SIZE, device=device)
    except Exception as e:
        print(f"[ERROR] 模型加载失败: {e}")
        return

    if not os.path.exists(SOURCE_FOLDER):
        print(f"[ERROR] 找不到源文件夹: {SOURCE_FOLDER}")
        return
    if os.path.exists(TARGET_FOLDER): shutil.rmtree(TARGET_FOLDER)
    os.makedirs(TARGET_FOLDER)

    files = [f for f in os.listdir(SOURCE_FOLDER) if f.endswith(('.ogg', '.wav', '.flac'))]
    candidates = []

    print(f"[INFO] 开始转录 {len(files)} 个文件...")

    for filename in tqdm(files):
        path = os.path.join(SOURCE_FOLDER, filename)

        try:
            result = model.transcribe(path, language="ja", fp16=(device == "cuda"))
            text = result["text"].strip()
            no_speech_prob = result["segments"][0]["no_speech_prob"] if result["segments"] else 1.0

            if no_speech_prob > 0.45:
                continue

            if len(text) < 2:
                continue

            if len(text) > 40:
                continue

            if contains_repeating_chars(text):
                continue

            if "Subtitle" in text or "視聴" in text or ".." in text:
                continue

            candidates.append({
                "name": filename,
                "path": path,
                "text": text,
                "len": len(text)
            })

        except Exception as e:
            print(f"[WARN] 跳过 {filename}: {e}")

    print(f"\n[OK] 初筛合格: {len(candidates)} 个。正在进行最终排名...")

    candidates.sort(key=lambda x: abs(x["len"] - 10))
    final_selection = candidates[:TARGET_COUNT]

    print(f"[INFO] 正在迁移 {len(final_selection)} 个最佳音频...")

    log_path = os.path.join(TARGET_FOLDER, "transcription_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        for item in final_selection:
            shutil.copy2(item["path"], os.path.join(TARGET_FOLDER, item["name"]))
            f.write(f"{item['name']}: {item['text']}\n")

    print("-" * 40)
    print(f"[OK] 处理完成，结果目录: {TARGET_FOLDER}")
    print(f"[INFO] 转录日志: {log_path}")


if __name__ == "__main__":
    asr_filter()
