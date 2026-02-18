#!/bin/bash
# Sony RAW → JPG 変換ツール 起動スクリプト

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# venvが存在しなければ作成
if [ ! -d "$VENV_DIR" ]; then
    echo "初回セットアップ中..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip -q
    "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    echo "セットアップ完了!"
    echo ""
fi

echo "============================================"
echo "  Sony RAW → JPG 変換ツール"
echo "  http://localhost:5000"
echo "  終了するには Ctrl+C を押してください"
echo "============================================"
echo ""

# ブラウザを少し遅らせて開く
(sleep 2 && open http://localhost:5001) &

"$VENV_DIR/bin/python" "$SCRIPT_DIR/app.py"
