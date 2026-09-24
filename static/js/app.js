import {
  drawBarChart,
  drawQuality,
  drawComparison,
} from "./charts.js";

const $ = (selector) => document.querySelector(selector);

const state = {
  mode: "image",
  file: null,
  job: null,
  config: null,
  started: 0,
  objectUrl: null,
  pollTimer: null,
  pollToken: 0,
};

const apiInput = $("#api");

/* --------------------------------------------------
   API Configuration
-------------------------------------------------- */

apiInput.value = localStorage.getItem("apiBase") || "";

const base = () => apiInput.value.trim().replace(/\/$/, "");

function updateApiFooter() {
  $("#apiFooter").textContent = base() || location.origin;
}

apiInput.addEventListener("change", () => {
  localStorage.setItem("apiBase", apiInput.value.trim());
  updateApiFooter();
});

updateApiFooter();

/* --------------------------------------------------
   API Request Helper
-------------------------------------------------- */

async function get(path, options = {}) {
  let response;

  try {
    response = await fetch(`${base()}${path}`, options);
  } catch (error) {
    throw new Error(
      `Unable to connect to the API. ${
        error?.message || "Network request failed."
      }`,
    );
  }

  const contentType = response.headers.get("content-type") || "";

  let data;

  if (contentType.includes("application/json")) {
    data = await response.json().catch(() => ({}));
  } else {
    const text = await response.text().catch(() => "");
    data = text ? { detail: text } : {};
  }

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.message ||
      `Request failed (${response.status})`;

    throw new Error(message);
  }

  return data;
}

/* --------------------------------------------------
   Configuration
-------------------------------------------------- */

async function loadConfig() {
  const config = await get("/api/v1/config");

  if (!config || typeof config !== "object") {
    throw new Error("Invalid configuration received from the API.");
  }

  state.config = config;

  return config;
}

/* --------------------------------------------------
   Error Handling
-------------------------------------------------- */

function clearError() {
  $("#error").textContent = "";
}

function err(error) {
  console.error(error);

  $("#error").textContent =
    error?.message || String(error) || "Something went wrong.";
}

/* --------------------------------------------------
   Formatting
-------------------------------------------------- */

function fmt(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  if (number < 1024) {
    return `${number.toFixed(0)} B`;
  }

  if (number < 1048576) {
    return `${(number / 1024).toFixed(1)} KB`;
  }

  return `${(number / 1048576).toFixed(2)} MB`;
}

function info(items) {
  return items
    .map(([label, value]) => {
      const safeValue =
        value === null ||
        value === undefined ||
        value === ""
          ? "—"
          : value;

      return `
        <div>
          <strong>${label}</strong>
          ${safeValue}
        </div>
      `;
    })
    .join("");
}

/* --------------------------------------------------
   Upload Progress
-------------------------------------------------- */

function progress(value, label = "Uploading…") {
  const progressWrap = $("#progressWrap");
  const progressBar = $("#progress");

  progressWrap.hidden = false;

  const safeValue = Math.min(
    100,
    Math.max(0, Number(value) || 0),
  );

  $("#progressLabel").textContent = label;
  $("#progressPct").textContent = `${Math.round(safeValue)}%`;
  progressBar.value = safeValue;
}

function hideProgress() {
  $("#progressWrap").hidden = true;
}

/* --------------------------------------------------
   Object URL Cleanup
-------------------------------------------------- */

function revokeObjectUrl() {
  if (state.objectUrl) {
    URL.revokeObjectURL(state.objectUrl);
    state.objectUrl = null;
  }
}

/* --------------------------------------------------
   Preview
-------------------------------------------------- */

function preview(file) {
  revokeObjectUrl();

  const url = URL.createObjectURL(file);
  state.objectUrl = url;

  $("#beforeSection").hidden = false;

  $("#beforeMeta").textContent = file.name;

  const meta = [
    ["Filename", file.name],
    ["Size", fmt(file.size)],
    ["Format", file.type || "unknown"],
  ];

  let media;

  if (state.mode === "image") {
    media = new Image();

    media.alt = file.name;
    media.src = url;

    media.onload = () => {
      meta.push([
        "Resolution",
        `${media.naturalWidth} × ${media.naturalHeight}`,
      ]);

      $("#beforeInfo").innerHTML = info(meta);
    };
  } else {
    media = document.createElement("video");

    media.controls = true;
    media.muted = true;
    media.playsInline = true;
    media.preload = "metadata";
    media.src = url;

    media.onloadedmetadata = () => {
      meta.push(
        ["Duration", `${media.duration.toFixed(1)}s`],
        [
          "Resolution",
          `${media.videoWidth} × ${media.videoHeight}`,
        ],
      );

      $("#beforeInfo").innerHTML = info(meta);
    };
  }

  media.onerror = () => {
    $("#beforeInfo").innerHTML = info(meta);
    err(new Error(`Unable to preview "${file.name}".`));
  };

  $("#before").replaceChildren(media);

  const comparisonMedia = media.cloneNode(true);

  if (state.mode === "video") {
    comparisonMedia.controls = true;
    comparisonMedia.muted = true;
    comparisonMedia.playsInline = true;
    comparisonMedia.src = url;
  }

  $("#afterBefore").replaceChildren(comparisonMedia);

  $("#beforeInfo").innerHTML = info(meta);
}

/* --------------------------------------------------
   File Validation
-------------------------------------------------- */

function valid(file) {
  if (!file) {
    throw new Error("Please select a file first.");
  }

  if (!state.config) {
    throw new Error("Compression configuration has not loaded.");
  }

  const isCorrectType =
    state.mode === "image"
      ? file.type.startsWith("image/")
      : file.type.startsWith("video/");

  if (!isCorrectType) {
    throw new Error(
      `Unsupported ${state.mode} file type.`,
    );
  }

  const maxFileSize = Number(state.config.max_file_size);

  if (
    Number.isFinite(maxFileSize) &&
    file.size > maxFileSize
  ) {
    throw new Error(
      `File exceeds configured limit of ${fmt(maxFileSize)}.`,
    );
  }
}

/* --------------------------------------------------
   Upload
-------------------------------------------------- */

async function upload(file) {
  const endpoint = `/api/v1/compress/${state.mode}`;

  const smallFileThreshold = Number(
    state.config.small_file_threshold,
  );

  /*
   * Small-file upload
   */
  if (
    Number.isFinite(smallFileThreshold) &&
    file.size <= smallFileThreshold
  ) {
    progress(0, "Uploading…");

    const formData = new FormData();
    formData.append("file", file);

    const result = await get(endpoint, {
      method: "POST",
      body: formData,
    });

    progress(100, "Upload complete");

    return result;
  }

  /*
   * Chunked upload
   */
  const chunkSize = Number(state.config.chunk_size);

  if (!Number.isFinite(chunkSize) || chunkSize <= 0) {
    throw new Error("Invalid chunk size returned by the API.");
  }

  const storageKey = `upload:${state.mode}:${file.name}:${file.size}`;

  let uploadData = null;

  const savedUploadId = localStorage.getItem(storageKey);

  if (savedUploadId) {
    try {
      const status = await get(
        `/api/v1/upload/status/${encodeURIComponent(
          savedUploadId,
        )}`,
      );

      uploadData = {
        ...status,
        id: savedUploadId,
      };

      const resume = confirm(
        `Resume upload "${file.name}"?`,
      );

      if (!resume) {
        uploadData = null;
        localStorage.removeItem(storageKey);
      }
    } catch {
      localStorage.removeItem(storageKey);
    }
  }

  /*
   * Start a new upload session.
   */
  if (!uploadData) {
    const created = await get("/api/v1/upload/init", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        filename: file.name,
        total_size: file.size,
        mimetype: file.type,
        chunk_size: chunkSize,
      }),
    });

    if (!created?.upload_id) {
      throw new Error(
        "Upload initialization did not return an upload ID.",
      );
    }

    uploadData = {
      id: created.upload_id,
      received_chunks: [],
    };

    localStorage.setItem(
      storageKey,
      created.upload_id,
    );
  }

  const received = new Set(
    Array.isArray(uploadData.received_chunks)
      ? uploadData.received_chunks
      : [],
  );

  const count = Math.ceil(file.size / chunkSize);

  for (let index = 0; index < count; index += 1) {
    if (received.has(index)) {
      progress(
        ((index + 1) / count) * 100,
        "Resuming upload…",
      );

      continue;
    }

    const start = index * chunkSize;
    const end = Math.min(
      file.size,
      start + chunkSize,
    );

    const chunk = file.slice(start, end);

    const buffer = await chunk.arrayBuffer();

    const hash = await crypto.subtle.digest(
      "SHA-256",
      buffer,
    );

    const checksum = Array.from(
      new Uint8Array(hash),
      (byte) => byte.toString(16).padStart(2, "0"),
    ).join("");

    try {
      await get(
        `/api/v1/upload/chunk/${encodeURIComponent(
          uploadData.id,
        )}/${index}?checksum=${encodeURIComponent(
          checksum,
        )}`,
        {
          method: "POST",
          body: chunk,
        },
      );

      progress(
        ((index + 1) / count) * 100,
        "Uploading…",
      );
    } catch (error) {
      $("#progressLabel").textContent =
        "Upload paused — Resume";

      throw error;
    }
  }

  localStorage.removeItem(storageKey);

  progress(100, "Upload complete");

  return get(
    `/api/v1/upload/complete/${encodeURIComponent(
      uploadData.id,
    )}`,
    {
      method: "POST",
    },
  );
}

/* --------------------------------------------------
   Job Polling
-------------------------------------------------- */

function stopPolling() {
  if (state.pollTimer) {
    clearTimeout(state.pollTimer);
    state.pollTimer = null;
  }
}

function resetPolling() {
  stopPolling();
  state.pollToken += 1;

  return state.pollToken;
}

async function poll(jobId, token = state.pollToken) {
  if (token !== state.pollToken) {
    return;
  }

  const job = await get(
    `/api/v1/jobs/${encodeURIComponent(jobId)}`,
  );

  if (token !== state.pollToken) {
    return;
  }

  const rawStatus = job?.status;

  const status =
    rawStatus &&
    typeof rawStatus === "object"
      ? rawStatus.value
      : rawStatus;

  const normalizedStatus = String(
    status || "",
  ).toLowerCase();

  const statusError =
    job?.error ||
    rawStatus?.error ||
    "Compression failed.";

  $("#statusText").textContent =
    normalizedStatus === "failed"
      ? statusError
      : `Job ${normalizedStatus || "unknown"}`;

  const steps = ["queued", "processing", "done"];

  const currentIndex = steps.indexOf(
    normalizedStatus,
  );

  document
    .querySelectorAll("[data-step]")
    .forEach((element) => {
      const stepIndex = steps.indexOf(
        element.dataset.step,
      );

      element.classList.remove(
        "current",
        "done",
      );

      if (
        currentIndex >= 0 &&
        stepIndex <= currentIndex
      ) {
        element.classList.add("done");
      }
    });

  if (normalizedStatus === "processing") {
    $(
      '[data-step="processing"]',
    )?.classList.add("current");
  }

  if (normalizedStatus === "failed") {
    $("#retry").hidden = false;

    stopPolling();

    throw new Error(statusError);
  }

  if (normalizedStatus === "done") {
    stopPolling();
    renderAfter(job);
    return;
  }

  $("#elapsed").textContent =
    `${((Date.now() - state.started) / 1000).toFixed(1)}s`;

  const delay =
    normalizedStatus === "queued"
      ? 1800
      : 1000;

  stopPolling();

  state.pollTimer = setTimeout(() => {
    poll(jobId, token).catch(err);
  }, delay);
}

/* --------------------------------------------------
   Render Result
-------------------------------------------------- */

function renderAfter(job) {
  const metrics = job?.metrics;

  if (!metrics) {
    throw new Error(
      "Compression completed but the API returned no metrics.",
    );
  }

  const originalSize = Number(
    metrics.original_size,
  );

  const compressedSize = Number(
    metrics.compressed_size,
  );

  const reductionPercent = Number(
    metrics.reduction_percent,
  );

  const processingTime = Number(
    metrics.processing_time_seconds,
  );

  const ssim = Number(metrics.ssim);
  const psnr = Number(metrics.psnr);

  $("#elapsed").textContent =
    Number.isFinite(processingTime)
      ? `${processingTime}s`
      : "—";

  $("#afterSection").hidden = false;

  if (job.download_url) {
    $("#download").href =
      `${base()}${job.download_url}`;
  } else {
    $("#download").removeAttribute("href");
  }

  $("#badge").textContent =
    Number.isFinite(reductionPercent)
      ? `${reductionPercent}% smaller`
      : "Compression complete";

  let badgeClass = "badge";

  if (Number.isFinite(reductionPercent)) {
    if (reductionPercent <= 15) {
      badgeClass += " red";
    } else if (reductionPercent <= 40) {
      badgeClass += " amber";
    }
  }

  $("#badge").className = badgeClass;

  const params = metrics.params_used || {};

  $("#stats").innerHTML = info([
    ["Original", fmt(originalSize)],
    ["Compressed", fmt(compressedSize)],
    [
      "Reduction",
      Number.isFinite(reductionPercent)
        ? `${reductionPercent}%`
        : "—",
    ],
    [
      "SSIM",
      Number.isFinite(ssim)
        ? ssim.toFixed(3)
        : "—",
    ],
    [
      "PSNR",
      Number.isFinite(psnr)
        ? psnr.toFixed(2)
        : "—",
    ],
    ["Codec", params.codec],
    [
      "Quality",
      params.quality ??
        params.crf ??
        "—",
    ],
    ["Iterations", metrics.iterations],
    [
      "Processing",
      Number.isFinite(processingTime)
        ? `${processingTime}s`
        : "—",
    ],
  ]);

  if (job.download_url) {
    const mediaUrl =
      `${base()}${job.download_url}`;

    if (state.mode === "image") {
      const image = new Image();

      image.alt = "Compressed image";
      image.src = mediaUrl;

      $("#after").replaceChildren(image);
    } else {
      const video =
        document.createElement("video");

      video.controls = true;
      video.playsInline = true;
      video.preload = "metadata";
      video.src = mediaUrl;

      $("#after").replaceChildren(video);
    }
  } else {
    $("#after").replaceChildren();
  }

  if (
    Number.isFinite(originalSize) &&
    Number.isFinite(compressedSize)
  ) {
    drawBarChart(
      $("#sizeChart"),
      [
        {
          label: "Original",
          value: originalSize / 1048576,
        },
        {
          label: "Compressed",
          value: compressedSize / 1048576,
        },
      ],
      {
        suffix: " MB",
        annotation: Number.isFinite(reductionPercent)
          ? `${reductionPercent}% reduction`
          : "",
      },
    );
  }

  if (
    Number.isFinite(ssim) &&
    Number.isFinite(psnr)
  ) {
    drawQuality(
      $("#qualityChart"),
      ssim,
      psnr,
      state.config?.ssim_threshold,
    );
  }

  $("#compareBtn").disabled = false;
}

/* --------------------------------------------------
   Reset UI
-------------------------------------------------- */

function resetResultState() {
  stopPolling();

  $("#afterSection").hidden = true;

  $("#retry").hidden = true;

  $("#compareBtn").disabled = true;

  $("#compareSummary").textContent =
    "Compress a file first to enable comparison.";

  $("#compareError").textContent = "";

  $("#compareTable").replaceChildren();

  $("#after").replaceChildren();

  $("#afterBefore").replaceChildren();

  $("#stats").replaceChildren();

  $("#badge").textContent = "";
  $("#badge").className = "badge";

  hideProgress();
}

/* --------------------------------------------------
   Main Compression Flow
-------------------------------------------------- */

async function run() {
  const file = state.file;

  if (!file) {
    return;
  }

  const token = resetPolling();

  clearError();

  $("#retry").hidden = true;

  try {
    if (!state.config) {
      await loadConfig();
    }

    valid(file);

    preview(file);

    $("#statusSection").hidden = false;

    state.started = Date.now();

    $("#elapsed").textContent = "0.0s";
    $("#statusText").textContent =
      "Uploading…";

    const result = await upload(file);

    if (token !== state.pollToken) {
      return;
    }

    if (!result?.job_id) {
      throw new Error(
        "Compression request did not return a job ID.",
      );
    }

    state.job = result.job_id;

    await poll(result.job_id, token);
  } catch (error) {
    if (token === state.pollToken) {
      stopPolling();
      err(error);
    }
  }
}

/* --------------------------------------------------
   Upload Binding
-------------------------------------------------- */

function bindUpload(mode) {
  const drop = $(`#${mode}Drop`);
  const picker = $(`#${mode}Picker`);
  const choose = $(`#${mode}Choose`);

  if (!drop || !picker || !choose) {
    console.warn(
      `Upload controls not found for mode: ${mode}`,
    );

    return;
  }

  choose.addEventListener("click", () => {
    picker.click();
  });

  picker.addEventListener("change", (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    state.file = file;
    run();
  });

  ["dragenter", "dragover"].forEach(
    (eventName) => {
      drop.addEventListener(
        eventName,
        (event) => {
          event.preventDefault();
          event.stopPropagation();

          drop.classList.add("drag");
        },
      );
    },
  );

  ["dragleave", "dragend"].forEach(
    (eventName) => {
      drop.addEventListener(
        eventName,
        (event) => {
          event.preventDefault();

          drop.classList.remove("drag");
        },
      );
    },
  );

  drop.addEventListener("drop", (event) => {
    event.preventDefault();
    event.stopPropagation();

    drop.classList.remove("drag");

    const file =
      event.dataTransfer?.files?.[0];

    if (!file) {
      return;
    }

    state.file = file;

    /*
     * Reset picker so selecting the same file
     * again still triggers change.
     */
    picker.value = "";

    run();
  });
}

bindUpload("image");
bindUpload("video");

/* --------------------------------------------------
   Mode Switching
-------------------------------------------------- */

document
  .querySelectorAll(".tabs button")
  .forEach((button) => {
    button.addEventListener("click", () => {
      const mode = button.dataset.mode;

      if (!mode || mode === state.mode) {
        return;
      }

      resetPolling();

      state.mode = mode;
      state.file = null;
      state.job = null;

      document
        .querySelectorAll(".tabs button")
        .forEach((tab) => {
          const active =
            tab.dataset.mode === mode;

          tab.classList.toggle(
            "active",
            active,
          );

          tab.setAttribute(
            "aria-selected",
            String(active),
          );
        });

      const imagePanel = $("#imagePanel");
      const videoPanel = $("#videoPanel");

      const imageActive = mode === "image";

      imagePanel.hidden = !imageActive;

      videoPanel.hidden = imageActive;

      clearError();
      resetResultState();
    });
  });

/* --------------------------------------------------
   Retry
-------------------------------------------------- */

$("#retry").addEventListener("click", () => {
  if (!state.file) {
    return;
  }

  run();
});

/* --------------------------------------------------
   AI vs Baseline Comparison
-------------------------------------------------- */

$("#compareBtn").addEventListener(
  "click",
  async () => {
    const button = $("#compareBtn");

    button.disabled = true;

    $("#compareError").textContent = "";
    $("#compareSummary").textContent =
      "Running comparison…";

    try {
      const result = await get(
        "/api/v1/compare",
        {
          method: "POST",
        },
      );

      const ai =
        result.ai ||
        result.ai_assisted;

      const baseline =
        result.baseline ||
        result.fixed;

      if (!ai || !baseline) {
        throw new Error(
          "Comparison response is missing AI or baseline results.",
        );
      }

      drawComparison(
        $("#compareChart"),
        ai,
        baseline,
      );

      $("#compareSummary").textContent =
        `AI-assisted compression achieved ${ai.reduction_percent}% ` +
        `size reduction at SSIM ${ai.ssim}, vs ` +
        `${baseline.reduction_percent}% at SSIM ${baseline.ssim} ` +
        `for fixed compression.`;

      $("#compareTable").innerHTML = info([
        [
          "Metric",
          "Fixed compression",
          "AI-assisted",
        ],
        [
          "Reduction",
          `${baseline.reduction_percent}%`,
          `${ai.reduction_percent}%`,
        ],
        [
          "SSIM",
          baseline.ssim,
          ai.ssim,
        ],
        [
          "Processing",
          `${baseline.processing_time_seconds}s`,
          `${ai.processing_time_seconds}s`,
        ],
      ]);
    } catch (error) {
      console.error(error);

      $("#compareSummary").textContent =
        "Comparison could not be completed.";

      $("#compareError").textContent =
        error?.message ||
        "Comparison endpoint is unavailable.";
    } finally {
      button.disabled = false;
    }
  },
);

/* --------------------------------------------------
   Cleanup
-------------------------------------------------- */

window.addEventListener("beforeunload", () => {
  stopPolling();
  revokeObjectUrl();
});

/* --------------------------------------------------
   Initial Configuration
-------------------------------------------------- */

loadConfig().catch(err);
