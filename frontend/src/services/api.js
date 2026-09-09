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
