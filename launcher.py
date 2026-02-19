"""Windows .exe 用ランチャー: Flaskサーバー起動 + ブラウザ自動オープン"""

import os
import sys
import threading
import webbrowser

# ローカルモード有効化（フル解像度・高品質変換）
os.environ["LOCAL_MODE"] = "1"

# PyInstaller で固められた場合のパス解決
if getattr(sys, "frozen", False):
    base_dir = sys._MEIPASS
    os.chdir(base_dir)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# テンプレートと静的ファイルのパスを設定
template_dir = os.path.join(base_dir, "templates")
static_dir = os.path.join(base_dir, "static")

PORT = 5001


def open_browser():
    """少し待ってからブラウザを開く。"""
    import time
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    from app import app

    app.template_folder = template_dir
    app.static_folder = static_dir

    print("=" * 44)
    print("  Sony RAW → JPG 変換ツール")
    print(f"  http://localhost:{PORT}")
    print("  閉じるにはこのウィンドウを閉じてください")
    print("=" * 44)

    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
