// ============================================
// SatQuery AI — Downloadable Report Generator
// ============================================
//
// No PDF library is bundled with this project, so reports are produced
// by opening a print-formatted document in a new window and invoking the
// browser's native print dialog, where "Save as PDF" produces a real PDF
// with no extra dependency.

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    switch (char) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      default:
        return "&#39;";
    }
  });
}

function buildReportHtml({
  title,
  subtitle,
  createdAt,
  query,
  answer,
  summaryStats,
  changes,
  images,
}) {
  const imagesHtml = (images || [])
    .filter((image) => image && image.src)
    .map(
      (image) => `
        <figure>
          <img src="${escapeHtml(image.src)}" alt="${escapeHtml(image.label)}" />
          <figcaption>${escapeHtml(image.label)}</figcaption>
        </figure>`
    )
    .join("");

  const statsHtml =
    summaryStats && summaryStats.length
      ? `
        <table class="stats">
          <tbody>
            ${summaryStats
              .map(
                (stat) => `
              <tr>
                <td>${escapeHtml(stat.label)}</td>
                <td>${escapeHtml(stat.value)}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>`
      : "";

  const changesHtml =
    changes && changes.length
      ? `
        <h3>Detected Change Regions</h3>
        <table class="stats">
          <thead>
            <tr>
              <th>#</th>
              <th>Area (px)</th>
              <th>Position (x, y)</th>
            </tr>
          </thead>
          <tbody>
            ${changes
              .map(
                (change) => `
              <tr>
                <td>${escapeHtml(change.id)}</td>
                <td>${escapeHtml(change.area)}</td>
                <td>${escapeHtml(change.x)}, ${escapeHtml(change.y)}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>`
      : "";

  return `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>${escapeHtml(title)}</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 40px;
    color: #1B2530;
    background: #FFFFFF;
    font-family: "Segoe UI", Inter, system-ui, sans-serif;
  }
  header {
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 2px solid #1E5F8C;
  }
  header .brand {
    color: #1E5F8C;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
  }
  header h1 {
    margin: 6px 0 4px;
    font-size: 22px;
  }
  header .meta {
    color: #66727F;
    font-size: 11px;
  }
  h3 {
    margin: 24px 0 10px;
    font-size: 14px;
  }
  .query-block {
    padding: 14px 16px;
    border: 1px solid #DCE8F2;
    border-radius: 10px;
    background: #F4F8FC;
  }
  .query-block .label {
    display: block;
    margin-bottom: 4px;
    color: #66727F;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  .query-block .question {
    margin: 0 0 10px;
    font-size: 13px;
    font-weight: 600;
  }
  .query-block .answer {
    margin: 0;
    font-size: 13px;
    line-height: 1.6;
  }
  .images {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-top: 20px;
  }
  figure {
    margin: 0;
    width: 260px;
  }
  figure img {
    display: block;
    width: 100%;
    border: 1px solid #CDD3DA;
    border-radius: 8px;
  }
  figcaption {
    margin-top: 6px;
    color: #66727F;
    font-size: 10px;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  table.stats {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }
  table.stats th,
  table.stats td {
    padding: 8px 10px;
    border-bottom: 1px solid #E5EAF0;
    text-align: left;
  }
  table.stats th {
    color: #66727F;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  footer {
    margin-top: 32px;
    padding-top: 12px;
    border-top: 1px solid #E5EAF0;
    color: #94A3B8;
    font-size: 10px;
  }
  @media print {
    body { padding: 0; }
  }
</style>
</head>
<body>
  <header>
    <span class="brand">SatQuery AI</span>
    <h1>${escapeHtml(title)}</h1>
    <span class="meta">${escapeHtml(subtitle)} &middot; Generated ${escapeHtml(createdAt)}</span>
  </header>

  <div class="query-block">
    <span class="label">Question</span>
    <p class="question">${escapeHtml(query)}</p>
    <span class="label">Answer</span>
    <p class="answer">${escapeHtml(answer)}</p>
  </div>

  ${imagesHtml ? `<div class="images">${imagesHtml}</div>` : ""}

  ${statsHtml ? `<h3>Summary</h3>${statsHtml}` : ""}

  ${changesHtml}

  <footer>SatQuery AI &middot; AI-Powered Earth Observation &middot; This report reflects computed values from the analysis backend.</footer>
</body>
</html>`;
}

// Opens the report in a new tab and triggers the browser's print dialog
// once every embedded image has finished loading, so "Save as PDF" in
// that dialog produces a complete downloadable PDF.
export function downloadReport(reportData) {
  const html = buildReportHtml(reportData);

  const reportWindow = window.open("", "_blank");

  if (!reportWindow) {
    throw new Error(
      "Your browser blocked the report window. Please allow pop-ups for this site and try again."
    );
  }

  reportWindow.document.open();
  reportWindow.document.write(html);
  reportWindow.document.close();

  const triggerPrint = () => {
    reportWindow.focus();
    reportWindow.print();
  };

  const images = reportWindow.document.images;

  if (!images || images.length === 0) {
    setTimeout(triggerPrint, 300);
    return;
  }

  let settled = 0;

  const onImageSettled = () => {
    settled += 1;
    if (settled >= images.length) {
      setTimeout(triggerPrint, 200);
    }
  };

  Array.from(images).forEach((image) => {
    if (image.complete) {
      onImageSettled();
    } else {
      image.addEventListener("load", onImageSettled);
      image.addEventListener("error", onImageSettled);
    }
  });
}
