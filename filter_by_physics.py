import os
import shutil
import librosa
import numpy as np
from tqdm import tqdm

# Legacy standalone script. The maintained implementation lives in core_pipeline.
SOURCE_FOLDER = r"E:\sound\vo\say-music"
FOLDER_ELITE = os.path.join(SOURCE_FOLDER, "Approved_Elite")
FOLDER_TRASH = os.path.join(SOURCE_FOLDER, "Rejected_Trash")
MIN_RMS = 0.015
MIN_CENTROID = 1000
MIN_DURATION = 0.4


# ===========================================

def physics_filter():
    print(f"启动声学特征分析筛选...")
    print(f"门槛: RMS>{MIN_RMS} | 质心>{MIN_CENTROID}Hz")

    if not os.path.exists(FOLDER_ELITE): os.makedirs(FOLDER_ELITE)
    if not os.path.exists(FOLDER_TRASH): os.makedirs(FOLDER_TRASH)

    files = [f for f in os.listdir(SOURCE_FOLDER) if f.endswith(('.ogg', '.wav', '.flac'))]

    accepted_count = 0
    rejected_count = 0

    for filename in tqdm(files, desc="分析音频中"):
        file_path = os.path.join(SOURCE_FOLDER, filename)

        try:
            y, sr = librosa.load(file_path, sr=None)

            duration = librosa.get_duration(y=y, sr=sr)
            if duration < MIN_DURATION:
                shutil.move(file_path, os.path.join(FOLDER_TRASH, filename))
                rejected_count += 1
                continue

            rms = np.mean(librosa.feature.rms(y=y))
            if rms < MIN_RMS:
                shutil.move(file_path, os.path.join(FOLDER_TRASH, filename))
                rejected_count += 1
                continue

            centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
            if centroid < MIN_CENTROID:
                shutil.move(file_path, os.path.join(FOLDER_TRASH, filename))
                rejected_count += 1
                continue

            shutil.move(file_path, os.path.join(FOLDER_ELITE, filename))
            accepted_count += 1

        except Exception as e:
            print(f"无法读取 {filename}: {e}")

    print("-" * 40)
    print(f"筛选完成！")
    print(f"精英音频 (Elite): {accepted_count} 个")
    print(f"淘汰音频 (Trash): {rejected_count} 个 (过短、过轻、过闷)")


if __name__ == "__main__":
    physics_filter()
