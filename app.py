"""Sony ARW → JPG 変換Webアプリ"""

import atexit
import gc
import os
import shutil
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
)

from converter import convert_arw_to_jpg, create_thumbnail

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB

# セッション管理
sessions: dict = {}


def cleanup_session(session_id: str) -> None:
    """セッションの一時ファイルを削除する。"""
    if session_id not in sessions:
        return
    session_dir = sessions[session_id].get("dir")
    if session_dir and os.path.isdir(session_dir):
        shutil.rmtree(session_dir, ignore_errors=True)
    del sessions[session_id]


def cleanup_old_sessions(max_age_seconds: int = 1800) -> None:
    """30分以上前のセッションをクリーンアップする。"""
    now = time.time()
    expired = [
        sid for sid, data in sessions.items()
        if now - data.get("created_at", now) > max_age_seconds
    ]
    for sid in expired:
        cleanup_session(sid)
    gc.collect()


def cleanup_all() -> None:
    """アプリ終了時に全セッションをクリーンアップする。"""
    for sid in list(sessions.keys()):
        cleanup_session(sid)


atexit.register(cleanup_all)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    cleanup_old_sessions()

    quality = int(request.form.get("quality", 95))
    quality = max(1, min(100, quality))
    wb_shift = int(request.form.get("wb_shift", 0))
    wb_shift = max(-50, min(50, wb_shift))
    files = request.files.getlist("files")

    if not files:
        return jsonify({"error": "ファイルが選択されていません"}), 400

    session_id = str(uuid.uuid4())
    session_dir = tempfile.mkdtemp(prefix=f"arw_{session_id[:8]}_")
    sessions[session_id] = {
        "dir": session_dir,
        "results": [],
        "created_at": time.time(),
    }

    # アップロードされたファイルを保存
    tasks = []
    for f in files:
        if not f.filename:
            continue
        if not f.filename.lower().endswith(".arw"):
            continue
        file_id = uuid.uuid4().hex[:12]
        input_path = os.path.join(session_dir, f"input_{file_id}.arw")
        stem = Path(f.filename).stem
        output_path = os.path.join(session_dir, f"{file_id}.jpg")
        thumb_path = os.path.join(session_dir, f"{file_id}_thumb.jpg")
        f.save(input_path)
        input_size = os.path.getsize(input_path)
        tasks.append({
            "input_path": input_path,
            "output_path": output_path,
            "thumb_path": thumb_path,
            "original_name": f.filename,
            "output_name": f"{stem}.jpg",
            "file_id": file_id,
            "input_size": input_size,
        })

    if not tasks:
        cleanup_session(session_id)
        return jsonify({"error": "ARWファイルが見つかりません"}), 400

    # 順次変換（メモリ節約のため1ファイルずつ処理+GC）
    results = []
    for task in tasks:
        try:
            result = convert_arw_to_jpg(
                task["input_path"],
                task["output_path"],
                quality,
                wb_shift,
            )
        except Exception as e:
            result = {"success": False, "error": str(e)}

        result["original_name"] = task["original_name"]
        result["output_name"] = task["output_name"]
        result["file_id"] = task["file_id"]
        result["input_size"] = task["input_size"]

        if result.get("success"):
            create_thumbnail(task["output_path"], task["thumb_path"])

        # 入力ファイル削除+GC（メモリ解放）
        try:
            os.remove(task["input_path"])
        except OSError:
            pass
        gc.collect()

        results.append(result)

    sessions[session_id]["results"] = results
    return jsonify({"session_id": session_id, "results": results})


@app.route("/preview/<session_id>/<file_id>")
def preview(session_id, file_id):
    if session_id not in sessions:
        return "セッションが見つかりません", 404
    session_dir = sessions[session_id]["dir"]
    thumb_path = os.path.join(session_dir, f"{file_id}_thumb.jpg")
    if not os.path.isfile(thumb_path):
        return "サムネイルが見つかりません", 404
    return send_file(thumb_path, mimetype="image/jpeg")


@app.route("/download/<session_id>/<file_id>")
def download(session_id, file_id):
    if session_id not in sessions:
        return "セッションが見つかりません", 404
    session_dir = sessions[session_id]["dir"]
    jpg_path = os.path.join(session_dir, f"{file_id}.jpg")
    if not os.path.isfile(jpg_path):
        return "ファイルが見つかりません", 404

    original_name = None
    for r in sessions[session_id].get("results", []):
        if r.get("file_id") == file_id:
            original_name = r.get("output_name")
            break

    return send_file(
        jpg_path,
        mimetype="image/jpeg",
        as_attachment=True,
        download_name=original_name or f"{file_id}.jpg",
    )


@app.route("/download-zip/<session_id>")
def download_zip(session_id):
    if session_id not in sessions:
        return "セッションが見つかりません", 404

    session_dir = sessions[session_id]["dir"]
    results = sessions[session_id].get("results", [])
    successful = [r for r in results if r.get("success")]

    if not successful:
        return "変換されたファイルがありません", 404

    zip_path = os.path.join(session_dir, "converted.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for r in successful:
            jpg_path = os.path.join(session_dir, f"{r['file_id']}.jpg")
            if os.path.isfile(jpg_path):
                zf.write(jpg_path, r["output_name"])

    return send_file(
        zip_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name="converted_images.zip",
    )


@app.route("/clear/<session_id>", methods=["POST"])
def clear(session_id):
    cleanup_session(session_id)
    gc.collect()
    return jsonify({"success": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"\n  Sony ARW → JPG 変換ツール")
    print(f"  http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
