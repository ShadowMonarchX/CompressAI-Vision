const DEFAULT_HEIGHT = 210;

const COLORS = {
  accent: "#6d5ef0",
  accent2: "#ff6ec7",
  accentLight: "#b9b3ef",
  accentMedium: "#9b6ef3",
  text: "#172033",
  track: "#ece9fd",
  threshold: "#d28b00",
  thresholdText: "#8a6100",
};

/* --------------------------------------------------
   Canvas Setup
-------------------------------------------------- */

function setup(canvas, height = DEFAULT_HEIGHT) {
  if (!(canvas instanceof HTMLCanvasElement)) {
    throw new Error("Invalid chart canvas.");
  }

  const width = Math.max(
    canvas.clientWidth || 320,
    1,
  );

  const pixelRatio = Math.max(
    1,
    window.devicePixelRatio || 1,
  );

  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);

  const context = canvas.getContext("2d");

  if (!context) {
    throw new Error("Unable to create 2D canvas context.");
  }

  /*
   * Reset the transform before applying the HiDPI scale.
   * This prevents blurry/double scaling when a chart
   * is redrawn.
   */
  context.setTransform(
    pixelRatio,
    0,
    0,
    pixelRatio,
    0,
    0,
  );

  context.imageSmoothingEnabled = true;

  return {
    ctx: context,
    width,
    height,
    pixelRatio,
  };
}

/* --------------------------------------------------
   Helpers
-------------------------------------------------- */

function finiteNumber(value, fallback = 0) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function clamp(value, min, max) {
  return Math.min(
    max,
    Math.max(min, value),
  );
}

function clearCanvas(ctx, width, height) {
  ctx.clearRect(0, 0, width, height);
}

function roundValue(value, digits = 1) {
  return finiteNumber(value).toFixed(digits);
}

/* --------------------------------------------------
   Bar Chart
-------------------------------------------------- */

export function drawBarChart(
  canvas,
  data,
  {
    colors = [
      COLORS.accent,
      COLORS.accent2,
    ],
    suffix = "",
    annotation = "",
  } = {},
) {
  const {
    ctx,
    width,
    height,
  } = setup(canvas);

  clearCanvas(ctx, width, height);

  if (!Array.isArray(data) || data.length === 0) {
    ctx.fillStyle = COLORS.text;
    ctx.font = "12px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(
      "No chart data available",
      width / 2,
      height / 2,
    );

    return;
  }

  const values = data.map((item) =>
    Math.max(
      0,
      finiteNumber(item?.value),
    ),
  );

  const maxValue = Math.max(
    ...values,
    1,
  );

  const chartBottom = height - 34;
  const chartTop = 30;
  const chartHeight =
    chartBottom - chartTop;

  const gap = width < 420 ? 12 : 18;

  const availableWidth =
    width - 32;

  const barWidth = Math.min(
    90,
    Math.max(
      28,
      (
        availableWidth -
        gap * Math.max(data.length - 1, 0)
      ) / data.length,
    ),
  );

  const totalWidth =
    data.length * barWidth +
    (data.length - 1) * gap;

  const startX =
    (width - totalWidth) / 2;

  ctx.font =
    "12px system-ui, -apple-system, sans-serif";

  data.forEach((item, index) => {
    const value = values[index];

    const barHeight =
      (value / maxValue) * chartHeight;

    const x =
      startX +
      index * (barWidth + gap);

    const y =
      chartBottom - barHeight;

    const color =
      colors[index % colors.length];

    /*
     * Bar
     */
    ctx.fillStyle = color;

    ctx.fillRect(
      x,
      y,
      barWidth,
      barHeight,
    );

    /*
     * Label
     */
    ctx.fillStyle = COLORS.text;
    ctx.textAlign = "center";

    const label =
      String(item?.label ?? "");

    ctx.fillText(
      label,
      x + barWidth / 2,
      height - 12,
    );

    /*
     * Value
     */
    const formattedValue =
      `${roundValue(value)}${suffix}`;

    /*
     * Keep the value inside the chart
     * when the bar is very small.
     */
    const valueY =
      Math.max(
        chartTop + 12,
        y - 8,
      );

    ctx.fillText(
      formattedValue,
      x + barWidth / 2,
      valueY,
    );
  });

  /*
   * Annotation
   */
  if (annotation) {
    ctx.fillStyle = COLORS.text;
    ctx.font =
      "600 12px system-ui, -apple-system, sans-serif";
    ctx.textAlign = "center";

    ctx.fillText(
      annotation,
      width / 2,
      15,
    );
  }
}

/* --------------------------------------------------
   Quality Chart
-------------------------------------------------- */

export function drawQuality(
  canvas,
  ssim,
  psnr,
  threshold,
) {
  const {
    ctx,
    width,
    height,
  } = setup(canvas);

  clearCanvas(ctx, width, height);

  const safeSsim = clamp(
    finiteNumber(ssim),
    0,
    1,
  );

  const safePsnr = Math.max(
    0,
    finiteNumber(psnr),
  );

  /*
   * SSIM threshold is expected to be
   * between 0 and 1.
   */
  const safeThreshold = clamp(
    finiteNumber(threshold, 0),
    0,
    1,
  );

  const left = 70;
  const right = 20;
  const barWidth = Math.max(
    1,
    width - left - right,
  );

  const barHeight = 24;

  const rows = [
    {
      label: "SSIM",
      value: safeSsim,
      max: 1,
      color: COLORS.accent,
      format: (value) =>
        value.toFixed(3),
    },
    {
      label: "PSNR",
      value: safePsnr,
      max: 60,
      color: COLORS.accent2,
      format: (value) =>
        value.toFixed(2),
    },
  ];

  ctx.font =
    "12px system-ui, -apple-system, sans-serif";

  rows.forEach((row, index) => {
    const y =
      48 +
      index * 65;

    const ratio = clamp(
      row.value / row.max,
      0,
      1,
    );

    /*
     * Track
     */
    ctx.fillStyle = COLORS.track;

    ctx.fillRect(
      left,
      y,
      barWidth,
      barHeight,
    );

    /*
     * Value
     */
    ctx.fillStyle = row.color;

    ctx.fillRect(
      left,
      y,
      barWidth * ratio,
      barHeight,
    );

    /*
     * Label
     */
    ctx.fillStyle = COLORS.text;
    ctx.textAlign = "left";

    ctx.fillText(
      `${row.label}: ${row.format(row.value)}`,
      8,
      y + 17,
    );
  });

  /*
   * SSIM threshold marker.
   *
   * The threshold is shown only on the
   * SSIM scale, because PSNR uses a
   * different scale.
   */
  const thresholdX =
    left +
    barWidth * safeThreshold;

  ctx.strokeStyle =
    COLORS.threshold;

  ctx.lineWidth = 1;

  ctx.setLineDash([4, 3]);

  ctx.beginPath();
  ctx.moveTo(
    thresholdX,
    48,
  );
  ctx.lineTo(
    thresholdX,
    48 + barHeight,
  );
  ctx.stroke();

  ctx.setLineDash([]);

  ctx.fillStyle =
    COLORS.thresholdText;

  ctx.textAlign = "left";

  ctx.fillText(
    `SSIM threshold: ${(
      safeThreshold * 100
    ).toFixed(0)}%`,
    left,
    28,
  );
}

/* --------------------------------------------------
   AI vs Baseline Comparison
-------------------------------------------------- */

export function drawComparison(
  canvas,
  ai,
  baseline,
) {
  if (!ai || !baseline) {
    throw new Error(
      "Comparison data is incomplete.",
    );
  }

  /*
   * Keep the comparison chart focused
   * on compression reduction.
   *
   * SSIM uses a completely different scale,
   * so mixing SSIM × 100 with reduction
   * percentages in the same chart is misleading.
   */
  drawBarChart(
    canvas,
    [
      {
        label: "Fixed reduction",
        value: finiteNumber(
          baseline.reduction_percent,
        ),
      },
      {
        label: "AI reduction",
        value: finiteNumber(
          ai.reduction_percent,
        ),
      },
    ],
    {
      suffix: "%",
      colors: [
        COLORS.accentLight,
        COLORS.accent2,
      ],
      annotation:
        "Compression size reduction",
    },
  );
}
