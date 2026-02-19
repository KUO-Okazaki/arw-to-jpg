"""Sony ARW → JPG 変換コアモジュール"""

import gc
import os
import time
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image

# ローカルモード（.exe / ローカル実行）ではフル品質
LOCAL_MODE = os.environ.get("LOCAL_MODE", "0") == "1"


def _adjust_wb(camera_wb, wb_shift: int):
    """
    カメラWBにユーザーの色温度シフトを適用する。

    wb_shift: -50（寒色/青）〜 0（カメラWB）〜 +50（暖色/赤）
    """
    if wb_shift == 0:
        return list(camera_wb)

    # カメラWBをコピー [R, G, B, G2]
    wb = list(camera_wb)

    # シフト量を係数に変換（-50〜+50 → 0.7〜1.3倍）
    factor = 1.0 + wb_shift / 166.0

    # 暖色(+): Rを増やしBを減らす / 寒色(-): Rを減らしBを増やす
    wb[0] = wb[0] * factor        # R
    wb[2] = wb[2] / factor        # B
    # G, G2 はそのまま

    return wb


def convert_arw_to_jpg(
    input_path: str, output_path: str, quality: int = 95, wb_shift: int = 0
) -> dict:
    """Sony ARWファイルをJPGに変換する（カラー正規化+WB調整付き）。"""
    start_time = time.time()

    try:
        with rawpy.imread(input_path) as raw:
            # WB設定
            if wb_shift == 0:
                wb_kwargs = {"use_camera_wb": True}
            else:
                cam_wb = raw.camera_whitebalance
                user_wb = _adjust_wb(cam_wb, wb_shift)
                wb_kwargs = {"user_wb": user_wb}

            if LOCAL_MODE:
                rgb = raw.postprocess(
                    **wb_kwargs,
                    output_color=rawpy.ColorSpace.sRGB,
                    output_bps=8,
                    no_auto_bright=False,
                    gamma=(2.222, 4.5),
                    demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
                    fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Light,
                    median_filter_passes=1,
                )
            else:
                rgb = raw.postprocess(
                    **wb_kwargs,
                    output_color=rawpy.ColorSpace.sRGB,
                    output_bps=8,
                    no_auto_bright=False,
                    gamma=(2.222, 4.5),
                    half_size=True,
                    demosaic_algorithm=rawpy.DemosaicAlgorithm.LINEAR,
                    fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                    median_filter_passes=0,
                )

        image = Image.fromarray(rgb)
        del rgb
        gc.collect()

        image.save(output_path, "JPEG", quality=quality, optimize=True, subsampling=0)

        file_size = Path(output_path).stat().st_size
        width, height = image.width, image.height
        elapsed = time.time() - start_time

        del image
        gc.collect()

        return {
            "success": True,
            "output_path": output_path,
            "width": width,
            "height": height,
            "file_size": file_size,
            "elapsed_seconds": round(elapsed, 2),
        }
    except rawpy.LibRawError as e:
        return {"success": False, "error": f"RAWファイルの読み込みに失敗: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_thumbnail(jpg_path: str, thumb_path: str, max_size: int = 400) -> bool:
    """JPGからサムネイルを生成する。"""
    try:
        with Image.open(jpg_path) as img:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
            img.save(thumb_path, "JPEG", quality=70)
        return True
    except Exception:
        return False
