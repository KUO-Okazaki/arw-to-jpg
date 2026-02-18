"""Sony ARW → JPG 変換コアモジュール"""

import time
from pathlib import Path

import rawpy
from PIL import Image


def convert_arw_to_jpg(input_path: str, output_path: str, quality: int = 95) -> dict:
    """
    Sony ARWファイルをJPGに変換する（カラー正規化付き）。

    Args:
        input_path: 入力ARWファイルパス
        output_path: 出力JPGファイルパス
        quality: JPG品質 (1-100)

    Returns:
        変換結果のメタデータ辞書
    """
    start_time = time.time()

    try:
        with rawpy.imread(input_path) as raw:
            rgb = raw.postprocess(
                use_camera_wb=True,
                output_color=rawpy.ColorSpace.sRGB,
                output_bps=8,
                no_auto_bright=False,
                gamma=(2.222, 4.5),
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
                fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Light,
                median_filter_passes=1,
            )

        image = Image.fromarray(rgb)
        image.save(output_path, "JPEG", quality=quality, optimize=True, subsampling=0)

        file_size = Path(output_path).stat().st_size
        elapsed = time.time() - start_time

        return {
            "success": True,
            "output_path": output_path,
            "width": image.width,
            "height": image.height,
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
            img.save(thumb_path, "JPEG", quality=80)
        return True
    except Exception:
        return False
