// ============================================
// SatQuery API Service
// ============================================

// Keep this TRUE only when the real backend is unavailable.
const USE_MOCK_API = false;

const MOCK_VISUALIZATIONS_AVAILABLE = true;

const BASE_ANALYSIS = {
  detectedRegions: 6,
  changedAreaPercentage: 0.27,
  largestRegionPixels: 516,
};

function generateMockResponse(query) {
  const q = query.toLowerCase().trim();
  const spatial =
    q.includes("where") ||
    q.includes("changed") ||
    q.includes("building") ||
    q.includes("vegetation") ||
    q.includes("road") ||
    q.includes("water") ||
    q.includes("largest");

  if (!spatial) {
    return {
      answer:
        "The detected differences are based on the comparison between the uploaded satellite images. Review the spatial outputs for more detail.",
      card: null,
    };
  }

  return {
    answer:
      "Potential changes were detected in the satellite imagery. The candidate regions below can be inspected in the change explorer.",
    card: {
      summary: `${BASE_ANALYSIS.detectedRegions} candidate change regions were detected.`,
      stats: [
        { label: "Regions detected", value: String(BASE_ANALYSIS.detectedRegions) },
        { label: "Changed area", value: `${BASE_ANALYSIS.changedAreaPercentage}%` },
        { label: "Largest region", value: String(BASE_ANALYSIS.largestRegionPixels) },
      ],
      regions: Array.from({ length: BASE_ANALYSIS.detectedRegions }, (_, index) => ({
        id: index + 1,
        label: "Potential change",
        confidence: `${82 - index}%`,
        x: 10 + index * 9,
        y: 12 + index * 7,
        w: 10,
        h: 9,
      })),
    },
  };
}

const wait = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

export async function analyzeImages({
  beforeImage,
  afterImage,
  query,
  attachments = [],
}) {
  if (USE_MOCK_API) {
    await wait(900);
    const analysis = generateMockResponse(query);

    return {
      ...analysis,
      query,
      summary: analysis.card
        ? {
            detectedRegions: analysis.card.stats[0].value,
            changedAreaPercentage: BASE_ANALYSIS.changedAreaPercentage,
            largestRegionPixels: BASE_ANALYSIS.largestRegionPixels,
          }
        : null,
      visualizations: MOCK_VISUALIZATIONS_AVAILABLE
        ? {
            alignment: "/visualizations/alignment_overlay.jpg",
            changeOverlay: "/visualizations/change_overlay.jpg",
            heatmap: "/visualizations/change_heatmap.jpg",
            mask: "/visualizations/change_mask.jpg",
            regions: "/visualizations/change_regions.jpg",
            difference: "/visualizations/raw_difference.jpg",
          }
        : null,
      receivedImages: {
        before: Boolean(beforeImage),
        after: Boolean(afterImage),
        attachments: attachments.length,
      },
    };
  }

  const formData = new FormData();
  formData.append("before_image", beforeImage);
  formData.append("after_image", afterImage);
  formData.append("query", query);

  // Optional follow-up attachments. The existing /analyze endpoint can
  // continue to accept the original three fields unchanged.
  attachments.forEach((file) => {
    formData.append("attachments", file);
  });

  const response = await fetch("http://localhost:8000/analyze", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Analysis request failed (${response.status})`);
  }

  return response.json();
}

// ============================================
// SINGLE-IMAGE VISUAL QUESTION ANSWERING
// ============================================

function generateMockVqaResponse(query) {
  const q = query.toLowerCase().trim();

  if (q.includes("water") || q.includes("river") || q.includes("lake")) {
    return {
      success: true,
      message:
        "Approximately 8.4% of the frame is classified as water-like based on pixel color composition.",
      query,
      stats: { waterLikePercentage: 8.4, vegetationLikePercentage: 41.2, edgeDensity: 12.7 },
    };
  }

  if (q.includes("vegetation") || q.includes("tree") || q.includes("green")) {
    return {
      success: true,
      message:
        "Roughly 41.2% of the visible surface shows vegetation-like coloring, concentrated in the upper-left region of the image.",
      query,
      stats: { waterLikePercentage: 8.4, vegetationLikePercentage: 41.2, edgeDensity: 12.7 },
    };
  }

  if (q.includes("building") || q.includes("structure") || q.includes("urban")) {
    return {
      success: true,
      message:
        "The image shows a moderate edge density consistent with built structures, suggesting a partially developed area.",
      query,
      stats: { waterLikePercentage: 8.4, vegetationLikePercentage: 41.2, edgeDensity: 12.7 },
    };
  }

  return {
    success: true,
    message:
      "The image shows a mix of vegetation, open ground, and some built structures, with no dominant water body visible.",
    query,
    stats: { waterLikePercentage: 8.4, vegetationLikePercentage: 41.2, edgeDensity: 12.7 },
  };
}

export async function askVisualQuestion({ image, query }) {
  if (USE_MOCK_API) {
    await wait(700);
    return generateMockVqaResponse(query);
  }

  const formData = new FormData();
  formData.append("image", image);
  formData.append("query", query);

  const response = await fetch("http://localhost:8000/vqa", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`VQA request failed (${response.status})`);
  }

  return response.json();
}
