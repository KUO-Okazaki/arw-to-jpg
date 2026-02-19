document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const qualitySlider = document.getElementById("quality-slider");
    const qualityValue = document.getElementById("quality-value");
    const wbSlider = document.getElementById("wb-slider");
    const wbValue = document.getElementById("wb-value");
    const wbPreviewSection = document.getElementById("wb-preview-section");
    const wbPreviewImg = document.getElementById("wb-preview-img");
    const wbPreviewName = document.getElementById("wb-preview-name");
    const wbPreviewLoading = document.getElementById("wb-preview-loading");
    const fileList = document.getElementById("file-list");
    const fileItems = document.getElementById("file-items");
    const fileCount = document.getElementById("file-count");
    const convertBtn = document.getElementById("convert-btn");
    const progressSection = document.getElementById("progress-section");
    const progressText = document.getElementById("progress-text");
    const progressFill = document.getElementById("progress-fill");
    const resultsSection = document.getElementById("results-section");
    const resultsGrid = document.getElementById("results-grid");
    const downloadZipBtn = document.getElementById("download-zip-btn");
    const clearBtn = document.getElementById("clear-btn");

    let selectedFiles = [];
    let currentSessionId = null;
    let previewSessionId = null;
    let wbDebounceTimer = null;

    // 品質スライダー
    qualitySlider.addEventListener("input", () => {
        qualityValue.textContent = qualitySlider.value + "%";
    });

    // WBスライダー（値表示 + プレビュー更新）
    wbSlider.addEventListener("input", () => {
        const v = parseInt(wbSlider.value);
        if (v === 0) {
            wbValue.textContent = "±0";
            wbValue.style.color = "#555";
        } else if (v > 0) {
            wbValue.textContent = "+" + v;
            wbValue.style.color = "#E8734A";
        } else {
            wbValue.textContent = String(v);
            wbValue.style.color = "#4A90D9";
        }

        // プレビューがあればデバウンスで更新
        if (previewSessionId) {
            clearTimeout(wbDebounceTimer);
            wbDebounceTimer = setTimeout(() => updateWbPreview(v), 300);
        }
    });

    async function updateWbPreview(wb) {
        if (!previewSessionId) return;
        wbPreviewLoading.hidden = false;
        try {
            const url = `/wb-preview/${previewSessionId}?wb=${wb}&t=${Date.now()}`;
            const resp = await fetch(url);
            if (resp.ok) {
                const blob = await resp.blob();
                wbPreviewImg.src = URL.createObjectURL(blob);
            }
        } catch (e) {
            // ignore
        }
        wbPreviewLoading.hidden = true;
    }

    async function uploadForPreview() {
        if (selectedFiles.length === 0) return;

        const formData = new FormData();
        formData.append("files", selectedFiles[0]);

        wbPreviewSection.hidden = false;
        wbPreviewName.textContent = selectedFiles[0].name;
        wbPreviewLoading.hidden = false;
        wbPreviewImg.src = "";

        try {
            const resp = await fetch("/upload-preview", {
                method: "POST",
                body: formData,
            });
            if (resp.ok) {
                const data = await resp.json();
                previewSessionId = data.session_id;
                // 初期プレビュー表示
                await updateWbPreview(parseInt(wbSlider.value));
            }
        } catch (e) {
            // ignore
        }
        wbPreviewLoading.hidden = true;
    }

    // ドラッグ&ドロップ
    dropZone.addEventListener("click", () => fileInput.click());

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("drag-over");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("drag-over");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        const files = Array.from(e.dataTransfer.files).filter(
            (f) => f.name.toLowerCase().endsWith(".arw")
        );
        if (files.length > 0) {
            addFiles(files);
        }
    });

    fileInput.addEventListener("change", () => {
        const files = Array.from(fileInput.files);
        if (files.length > 0) {
            addFiles(files);
        }
        fileInput.value = "";
    });

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    function addFiles(files) {
        const isFirst = selectedFiles.length === 0;
        selectedFiles = selectedFiles.concat(files);
        renderFileList();

        // 初回ファイル追加時にプレビューをアップロード
        if (isFirst) {
            uploadForPreview();
        }
    }

    function renderFileList() {
        if (selectedFiles.length === 0) {
            fileList.hidden = true;
            return;
        }
        fileList.hidden = false;
        fileCount.textContent = selectedFiles.length;
        fileItems.innerHTML = "";

        selectedFiles.forEach((file, index) => {
            const li = document.createElement("li");
            li.innerHTML = `
                <span class="file-name">${file.name}</span>
                <span class="file-size">${formatSize(file.size)}</span>
            `;
            fileItems.appendChild(li);
        });
    }

    // 変換開始
    convertBtn.addEventListener("click", async () => {
        if (selectedFiles.length === 0) return;

        convertBtn.disabled = true;
        fileList.hidden = true;
        wbPreviewSection.hidden = true;
        progressSection.hidden = false;
        resultsSection.hidden = true;
        progressFill.style.width = "0%";
        progressText.textContent = `0/${selectedFiles.length}`;

        let fakeProgress = 0;
        const progressInterval = setInterval(() => {
            fakeProgress = Math.min(fakeProgress + 2, 90);
            progressFill.style.width = fakeProgress + "%";
        }, 500);

        const formData = new FormData();
        selectedFiles.forEach((file) => formData.append("files", file));
        formData.append("quality", qualitySlider.value);
        formData.append("wb_shift", wbSlider.value);

        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData,
            });

            clearInterval(progressInterval);

            if (!response.ok) {
                const err = await response.json();
                alert(err.error || "変換に失敗しました");
                resetUI();
                return;
            }

            const data = await response.json();
            currentSessionId = data.session_id;

            progressFill.style.width = "100%";
            progressText.textContent = `${selectedFiles.length}/${selectedFiles.length}`;

            setTimeout(() => {
                progressSection.hidden = true;
                showResults(data.results);
            }, 500);
        } catch (err) {
            clearInterval(progressInterval);
            alert("通信エラーが発生しました: " + err.message);
            resetUI();
        }
    });

    function showResults(results) {
        resultsSection.hidden = false;
        resultsGrid.innerHTML = "";

        let successCount = 0;

        results.forEach((r) => {
            const card = document.createElement("div");
            card.className = "result-card";

            if (r.success) {
                successCount++;
                card.innerHTML = `
                    <img src="/preview/${currentSessionId}/${r.file_id}" alt="${r.output_name}" loading="lazy">
                    <div class="result-info">
                        <div class="result-name">${r.output_name}</div>
                        <div class="result-meta">${formatSize(r.file_size)} ・ ${r.width}x${r.height} ・ ${r.elapsed_seconds}秒</div>
                    </div>
                    <button class="btn-download-single" onclick="window.location.href='/download/${currentSessionId}/${r.file_id}'">ダウンロード</button>
                `;
            } else {
                card.innerHTML = `
                    <div class="result-error">
                        <div class="result-name">${r.original_name}</div>
                        <div>エラー: ${r.error}</div>
                    </div>
                `;
            }

            resultsGrid.appendChild(card);
        });

        downloadZipBtn.disabled = successCount === 0;
    }

    // ZIPダウンロード
    downloadZipBtn.addEventListener("click", () => {
        if (!currentSessionId) return;
        window.location.href = `/download-zip/${currentSessionId}`;
    });

    // クリア
    clearBtn.addEventListener("click", async () => {
        if (currentSessionId) {
            try {
                await fetch(`/clear/${currentSessionId}`, { method: "POST" });
            } catch (e) {
                // ignore
            }
        }
        if (previewSessionId) {
            try {
                await fetch(`/clear/${previewSessionId}`, { method: "POST" });
            } catch (e) {
                // ignore
            }
        }
        resetUI();
    });

    function resetUI() {
        selectedFiles = [];
        currentSessionId = null;
        previewSessionId = null;
        fileList.hidden = true;
        progressSection.hidden = true;
        resultsSection.hidden = true;
        wbPreviewSection.hidden = true;
        convertBtn.disabled = false;
        fileItems.innerHTML = "";
        resultsGrid.innerHTML = "";
        progressFill.style.width = "0%";
        wbSlider.value = 0;
        wbValue.textContent = "±0";
        wbValue.style.color = "#555";
    }
});
