import { useEffect, useState } from "react";
import "./App.css";
import { analyzeImages, askVisualQuestion } from "./services/api";
import { downloadReport } from "./utils/report";

const visualizationLayers = [
  {
    id: "before",
    name: "Before · 2025",
    description: "Original satellite observation",
  },
  {
    id: "after",
    name: "After · 2026",
    description: "Latest satellite observation",
  },
  {
    id: "compare",
    name: "Before / After",
    description: "Interactive before and after comparison",
  },
  {
    id: "alignment",
    name: "Alignment",
    description: "Registration overlay",
    visualizationKey: "alignment",
  },
  {
    id: "change-overlay",
    name: "Change Overlay",
    description: "Detected changes on imagery",
    visualizationKey: "changeOverlay",
  },
  {
    id: "heatmap",
    name: "Change Heatmap",
    description: "Pixel-level difference intensity",
    visualizationKey: "heatmap",
  },
  {
    id: "mask",
    name: "Change Mask",
    description: "Binary change detection mask",
    visualizationKey: "mask",
  },
  {
    id: "regions",
    name: "Change Regions",
    description: "Detected regions with bounding boxes",
    visualizationKey: "regions",
  },
  {
    id: "difference",
    name: "Raw Difference",
    description: "Absolute pixel difference",
    visualizationKey: "difference",
  },
];
function App() {
  const [mode, setMode] = useState("change");

  const [beforeImage, setBeforeImage] = useState(null);
  const [afterImage, setAfterImage] = useState(null);

  const [beforeFile, setBeforeFile] = useState(null);
  const [afterFile, setAfterFile] = useState(null);

  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [showVisualization, setShowVisualization] = useState(false);
  const [activeLayer, setActiveLayer] = useState("change-overlay");
  const [comparePosition, setComparePosition] = useState(50);

  const [analysisHistory, setAnalysisHistory] = useState(() => {
    try {
      const savedHistory = localStorage.getItem(
        "satquery-analysis-history"
      );

      return savedHistory
        ? JSON.parse(savedHistory)
        : [];
    } catch {
      return [];
    }
  });

  const [activeHistoryId, setActiveHistoryId] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(true);

  const [showFollowUpModal, setShowFollowUpModal] = useState(false);
  const [followUpQuery, setFollowUpQuery] = useState("");
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [followUpError, setFollowUpError] = useState("");
  const [followUpThread, setFollowUpThread] = useState([]);

  // ==========================================
  // SINGLE-IMAGE VQA STATE
  // ==========================================

  const [vqaImage, setVqaImage] = useState(null);
  const [vqaFile, setVqaFile] = useState(null);
  const [vqaQuery, setVqaQuery] = useState("");
  const [vqaResult, setVqaResult] = useState(null);
  const [vqaLoading, setVqaLoading] = useState(false);
  const [vqaError, setVqaError] = useState("");

  const handleClearHistory = () => {
  const confirmed = window.confirm(
    "Clear all analysis history?"
  );

  if (!confirmed) return;

  localStorage.removeItem("satquery-analysis-history");
  setAnalysisHistory([]);
  setActiveHistoryId(null);
};

  useEffect(() => {
    localStorage.setItem(
      "satquery-analysis-history",
      JSON.stringify(analysisHistory)
    );
  }, [analysisHistory]);

  useEffect(() => {
    setFollowUpQuery("");
    setFollowUpError("");
    setShowFollowUpModal(false);
  }, [activeHistoryId]);

  // ==========================================
  // IMAGE UPLOAD
  // ==========================================

  const handleBeforeUpload = (event) => {
    const file = event.target.files[0];

    if (!file) return;

    setBeforeFile(file);
    setBeforeImage(URL.createObjectURL(file));
    setResult(null);
    setError("");
    setShowVisualization(false);
  };

  const handleAfterUpload = (event) => {
    const file = event.target.files[0];

    if (!file) return;

    setAfterFile(file);
    setAfterImage(URL.createObjectURL(file));
    setResult(null);
    setError("");
    setShowVisualization(false);
  };

    const removeBeforeImage = () => {
    setBeforeImage(null);
    setBeforeFile(null);
    setResult(null);
    setError("");
    setShowVisualization(false);
    setActiveHistoryId(null);
  };

  const removeAfterImage = () => {
    setAfterImage(null);
    setAfterFile(null);
    setResult(null);
    setError("");
    setShowVisualization(false);
    setActiveHistoryId(null);
  };

  const handleVqaUpload = (event) => {
    const file = event.target.files[0];

    if (!file) return;

    setVqaFile(file);
    setVqaImage(URL.createObjectURL(file));
    setVqaResult(null);
    setVqaError("");
  };

  const removeVqaImage = () => {
    setVqaImage(null);
    setVqaFile(null);
    setVqaResult(null);
    setVqaError("");
    setActiveHistoryId(null);
  };

  // ==========================================
  // ANALYSIS
  // ==========================================

  const handleAnalyze = async () => {
    setError("");
    setResult(null);

    if (!beforeFile || !afterFile) {
      setError("Please upload both satellite images first.");
      return;
    }

    if (!query.trim()) {
      setError("Please enter a question about the detected change.");
      return;
    }

    try {
      setLoading(true);

      const response = await analyzeImages({
        beforeImage: beforeFile,
        afterImage: afterFile,
        query: query.trim(),
      });

      setResult(response);

      const historyEntry = {
        id: Date.now(),
        query: query.trim(),
        result: response,
        beforeImage,
        afterImage,
        followUpThread: [],
        createdAt: new Date().toLocaleString(),
      };

      setAnalysisHistory((previousHistory) => [
        historyEntry,
        ...previousHistory,
      ]);

      setActiveHistoryId(historyEntry.id);    } catch (err) {
      if (err.message === "Failed to fetch") {
        setError(
          "Unable to connect to the analysis server. Please make sure the backend is running and try again."
        );
      } else {
        setError(
          err.message ||
            "Something went wrong while analyzing the images."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // ==========================================
  // FOLLOW-UP QUESTIONS
  // ==========================================

  const handleFollowUpAsk = async () => {
    const trimmed = followUpQuery.trim();

    if (!trimmed) return;

    if (mode === "vqa") {
      if (!vqaFile) {
        setFollowUpError("Please upload an image first.");
        return;
      }
    } else if (!beforeFile || !afterFile) {
      setFollowUpError("Please upload both satellite images first.");
      return;
    }

    setFollowUpError("");

    try {
      setFollowUpLoading(true);

      const response =
        mode === "vqa"
          ? await askVisualQuestion({
              image: vqaFile,
              query: trimmed,
            })
          : await analyzeImages({
              beforeImage: beforeFile,
              afterImage: afterFile,
              query: trimmed,
            });

      setFollowUpThread((previousThread) => {
        const updatedThread = [
          ...previousThread,
          { query: trimmed, response },
        ];

        setAnalysisHistory((previousHistory) =>
          previousHistory.map((entry) =>
            entry.id === activeHistoryId
              ? {
                  ...entry,
                  followUpThread: updatedThread,
                }
              : entry
          )
        );

        return updatedThread;
      });

      setFollowUpQuery("");
    } catch (err) {
      if (err.message === "Failed to fetch") {
        setFollowUpError(
          "Unable to connect to the analysis server. Please make sure the backend is running and try again."
        );
      } else {
        setFollowUpError(
          err.message ||
            "Something went wrong while processing the follow-up."
        );
      }
    } finally {
      setFollowUpLoading(false);
    }
  };

  // ==========================================
  // SINGLE-IMAGE VQA
  // ==========================================

  const handleVqaAsk = async () => {
    setVqaError("");
    setVqaResult(null);

    if (!vqaFile) {
      setVqaError("Please upload a satellite image first.");
      return;
    }

    if (!vqaQuery.trim()) {
      setVqaError("Please enter a question about the image.");
      return;
    }

    try {
      setVqaLoading(true);

      const response = await askVisualQuestion({
        image: vqaFile,
        query: vqaQuery.trim(),
      });

      setVqaResult(response);

      const historyEntry = {
        id: Date.now(),
        type: "vqa",
        query: vqaQuery.trim(),
        result: response,
        image: vqaImage,
        followUpThread: [],
        createdAt: new Date().toLocaleString(),
      };

      setAnalysisHistory((previousHistory) => [
        historyEntry,
        ...previousHistory,
      ]);

      setActiveHistoryId(historyEntry.id);
    } catch (err) {
      if (err.message === "Failed to fetch") {
        setVqaError(
          "Unable to connect to the analysis server. Please make sure the backend is running and try again."
        );
      } else {
        setVqaError(
          err.message ||
            "Something went wrong while analyzing the image."
        );
      }
    } finally {
      setVqaLoading(false);
    }
  };

  // ==========================================
  // DOWNLOADABLE REPORT
  // ==========================================

  const resolveVisualizationUrl = (visualizationKey) => {
    const visualization = result?.visualizations?.[visualizationKey];

    if (!visualization) return null;

    if (visualization.startsWith("/visualizations/")) {
      return visualization;
    }

    if (visualization.startsWith("/")) {
      return `http://localhost:8000${visualization}`;
    }

    return visualization;
  };

  const handleDownloadReport = (reportType) => {
    try {
      if (reportType === "vqa") {
        if (!vqaResult) return;

        downloadReport({
          title: "Visual Question Answering Report",
          subtitle: "Single-image analysis",
          createdAt: new Date().toLocaleString(),
          query: vqaResult.query || vqaQuery,
          answer: vqaResult.message,
          summaryStats: vqaResult.stats
            ? Object.entries(vqaResult.stats).map(([label, value]) => ({
                label,
                value,
              }))
            : null,
          images: [{ label: "Analyzed Image", src: vqaImage }],
        });

        return;
      }

      if (!result) return;

      downloadReport({
        title: "Change Detection Report",
        subtitle: "Bi-temporal satellite change analysis",
        createdAt: new Date().toLocaleString(),
        query: result.query || query,
        answer: result.message,
        summaryStats: result.summary
          ? [
              {
                label: "Regions detected",
                value: result.summary.detectedRegions,
              },
              {
                label: "Changed area",
                value: `${result.summary.changedAreaPercentage}%`,
              },
              {
                label: "Largest region (px)",
                value: result.summary.largestRegionPixels,
              },
            ]
          : null,
        changes: result.changes,
        images: [
          { label: "Before", src: beforeImage },
          { label: "After", src: afterImage },
          {
            label: "Change Overlay",
            src: resolveVisualizationUrl("changeOverlay"),
          },
        ],
      });
    } catch (err) {
      if (reportType === "vqa") {
        setVqaError(err.message || "Could not generate the report.");
      } else {
        setError(err.message || "Could not generate the report.");
      }
    }
  };

  // ==========================================
  // BEFORE / AFTER COMPARISON
  // ==========================================

  const renderComparisonSlider = () => {
    if (!beforeImage || !afterImage) {
      return (
        <div className="visualization-empty">
          <strong>
            Comparison unavailable
          </strong>

          <span>
            Upload both satellite images to compare them.
          </span>
        </div>
      );
    }

    const showingBefore = comparePosition < 50;

    return (
      <div className="comparison-container">

        {/* ============================================
            BEFORE IMAGE — BASE LAYER
            ============================================ */}

        <div className="comparison-before-layer">
          <img
            src={beforeImage}
            alt="Before satellite imagery"
            className="comparison-image"
          />
        </div>


        {/* ============================================
            AFTER IMAGE — REVEALED BY SLIDER
            ============================================ */}

        <div
          className="comparison-after-layer"
          style={{
            clipPath: `inset(
              0
              ${100 - comparePosition}%
              0
              0
            )`,
          }}
        >
          <img
            src={afterImage}
            alt="After satellite imagery"
            className="comparison-image comparison-after-image"
          />
        </div>

        {/* ============================================
            DIVIDER
            ============================================ */}

        <div
          className="comparison-divider"
          style={{
            left: `${comparePosition}%`,
          }}
        >
          <div className="comparison-handle">
            ↔
          </div>
        </div>


        {/* ============================================
            ACTIVE IMAGE LABEL
            ============================================ */}

        <div
          className={`comparison-active-label ${
            showingBefore
              ? "comparison-active-before"
              : "comparison-active-after"
          }`}
        >
          {showingBefore
            ? "BEFORE · 2025"
            : "AFTER · 2026"}
        </div>


        {/* ============================================
            SLIDER
            ============================================ */}

        <input
          type="range"
          min="0"
          max="100"
          value={comparePosition}
          onChange={(event) =>
            setComparePosition(
              Number(event.target.value)
            )
          }
          className="comparison-range"
          aria-label="Before and after comparison slider"
        />

      </div>
    );
  };
  // ==========================================
  // VISUALIZATION IMAGE
  // ==========================================

  const getActiveVisualization = () => {
    const layer = visualizationLayers.find(
      (item) => item.id === activeLayer
    );

    if (!layer) {
      return null;
    }

    // Uploaded images belong to the current analysis pair.
    if (layer.id === "before") {
      return beforeImage;
    }

    if (layer.id === "after") {
      return afterImage;
    }

    // Processing outputs come from the current backend response.
    if (layer.visualizationKey) {
      return resolveVisualizationUrl(layer.visualizationKey);
    }

    return null;
  };

  return (
    <div
      className={`app ${
        historyOpen
          ? "history-open"
          : "history-closed"
      }`}
    >
      {/* ======================================
          HEADER
      ====================================== */}

      <header className="header">

        <div className="header-left">

          <button
            type="button"
            className="history-toggle"
            onClick={() =>
              setHistoryOpen((open) => !open)
            }
            aria-label={
              historyOpen
                ? "Close analysis history"
                : "Open analysis history"
            }
            title={
              historyOpen
                ? "Close analysis history"
                : "Open analysis history"
            }
          >
            {historyOpen ? "‹" : "☰"}
          </button>

          <div>
            <h1>SatQuery AI</h1>
            <p>Intelligent Satellite Change Detection</p>
          </div>

        </div>

        <div className="status">
          <span className="status-dot"></span>
          {loading ? "Analyzing..." : "System Ready"}
        </div>

      </header>

      {/* ======================================
          MAIN
      ====================================== */}

      <main className="main-content">

        {/* ======================================
            ANALYSIS HISTORY
        ====================================== */}

        <aside
          className={`history-sidebar ${
            historyOpen ? "open" : "closed"
          }`}
        >
          <button
            type="button"
            className="new-analysis-button"
            onClick={() => {
              setQuery("");
              setResult(null);
              setError("");
              setBeforeImage(null);
              setAfterImage(null);
              setBeforeFile(null);
              setAfterFile(null);
              setFollowUpThread([]);
              setFollowUpQuery("");
              setFollowUpError("");
              setActiveHistoryId(null);
              setShowVisualization(false);
              setVqaImage(null);
              setVqaFile(null);
              setVqaQuery("");
              setVqaResult(null);
              setVqaError("");
            }}
          >
            <span>＋</span>
            <span>New Analysis</span>
          </button>

          <div className="history-title">
            <span>ANALYSIS HISTORY</span>

            {analysisHistory.length > 0 && (
              <button
                type="button"
                className="clear-history-button"
                onClick={handleClearHistory}
              >
                Clear All
              </button>
            )}
          </div>

          <div className="history-list">

            {analysisHistory.length === 0 ? (

              <div className="history-empty">
                <span>No previous analyses</span>
                <small>
                  Your analysis questions will appear here.
                </small>
              </div>

            ) : (

              analysisHistory.map((entry) => (
                <button
                  type="button"
                  key={entry.id}
                  className={`history-item ${
                    activeHistoryId === entry.id
                      ? "active"
                      : ""
                  }`}
                  onClick={() => {
                    if (entry.type === "vqa") {
                      setMode("vqa");
                      setVqaQuery(entry.query);
                      setVqaResult(entry.result);
                      setVqaImage(entry.image || null);
                      setFollowUpThread(entry.followUpThread || []);
                      setVqaError("");
                    } else {
                      setMode("change");
                      setQuery(entry.query);
                      setResult(entry.result);
                      setBeforeImage(entry.beforeImage || null);
                      setAfterImage(entry.afterImage || null);
                      setFollowUpThread(entry.followUpThread || []);
                      setError("");
                      setShowVisualization(false);
                    }
                    setActiveHistoryId(entry.id);
                  }}
                >
                  <span className="history-question">
                    <span className="history-type">
                      {entry.type === "vqa" ? "VQA" : "Change"}
                    </span>
                    {entry.query}
                  </span>

                  <span className="history-date">
                    {entry.createdAt}
                  </span>
                </button>
              ))

            )}

          </div>

        </aside>

        <section className="intro">
          <p className="tag">SATELLITE INTELLIGENCE</p>

          <h2>
            Understand what changed
            <br />
            <span>from above.</span>
          </h2>

          <p className="description">
            {mode === "vqa"
              ? "Upload a single satellite image and ask a direct question about what it shows."
              : "Compare satellite imagery across time and ask natural-language questions about meaningful changes in the landscape."}
          </p>
        </section>

        {/* ====================================
            MODE SELECTION
        ==================================== */}

        <section className="mode-tabs" role="tablist" aria-label="Analysis mode">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "change"}
            className={`mode-tab ${mode === "change" ? "active" : ""}`}
            onClick={() => setMode("change")}
          >
            <span className="mode-tab-title">Change Detection</span>
            <span className="mode-tab-desc">
              Compare a before/after image pair over time
            </span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={mode === "vqa"}
            className={`mode-tab ${mode === "vqa" ? "active" : ""}`}
            onClick={() => setMode("vqa")}
          >
            <span className="mode-tab-title">Ask About an Image</span>
            <span className="mode-tab-desc">
              Visual question answering on a single image
            </span>
          </button>
        </section>

        {mode === "change" && (
        <>
        {/* ====================================
            IMAGE INPUT
        ==================================== */}

        <section className="upload-section">
          {/* BEFORE */}

          <div className="upload-card">
            <div className="card-heading">
              <span>01</span>
              <h3>Before Image</h3>
            </div>

            <div className="image-upload">
              {beforeImage ? (
                <div className="image-preview">
                  <img
                    src={beforeImage}
                    alt="Before satellite imagery"
                  />

                  <button
                    type="button"
                    className="remove-image-button"
                    onClick={removeBeforeImage}
                    aria-label="Remove before image"
                    title="Remove image"
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M3 6h18" />
                      <path d="M8 6V4h8v2" />
                      <path d="M19 6l-1 14H6L5 6" />
                      <path d="M10 11v5" />
                      <path d="M14 11v5" />
                    </svg>
                  </button>

                  <div className="image-label">
                    BEFORE · 2025
                  </div>
                </div>
              ) : (
                <label className="upload-placeholder">
                  <span className="upload-icon">↑</span>

                  <strong>Upload satellite image</strong>

                  <small>PNG, JPG, JPEG or GeoTIFF</small>

                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleBeforeUpload}
                  />
                </label>
              )}
            </div>
          </div>

          {/* AFTER */}

          <div className="upload-card">
            <div className="card-heading">
              <span>02</span>
              <h3>After Image</h3>
            </div>

            <div className="image-upload">
              {afterImage ? (
                <div className="image-preview">
                  <img
                    src={afterImage}
                    alt="After satellite imagery"
                  />

                  <button
                    type="button"
                    className="remove-image-button"
                    onClick={removeAfterImage}
                    aria-label="Remove after image"
                    title="Remove image"
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M3 6h18" />
                      <path d="M8 6V4h8v2" />
                      <path d="M19 6l-1 14H6L5 6" />
                      <path d="M10 11v5" />
                      <path d="M14 11v5" />
                    </svg>
                  </button>

                  <div className="image-label">
                    AFTER · 2026
                  </div>
                </div>
              ) : (
                <label className="upload-placeholder">
                  <span className="upload-icon">↑</span>

                  <strong>Upload satellite image</strong>

                  <small>PNG, JPG, JPEG or GeoTIFF</small>

                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleAfterUpload}
                  />
                </label>
              )}
            </div>
          </div>
        </section>

        {/* ====================================
            QUERY
        ==================================== */}

        <section className="query-section">
          <label htmlFor="query">Ask about the change</label>

          <div className="query-box">
            <input
              id="query"
              type="text"
              placeholder='Try: "What changed in this area?"'
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  handleAnalyze();
                }
              }}
              disabled={loading}
            />

            <button
              type="button"
              onClick={handleAnalyze}
              disabled={loading}
            >
              {loading ? "Analyzing..." : "Analyze →"}
            </button>
          </div>

          <p className="query-hint">
            Ask questions about buildings, vegetation, roads, water, or other
            visible changes.
          </p>

          <div className="query-suggestions">
            <button
              type="button"
              onClick={() => setQuery("What changed here?")}
              disabled={loading}
            >
              What changed here?
            </button>

            <button
              type="button"
              onClick={() => setQuery("Did any buildings appear?")}
              disabled={loading}
            >
              Did any buildings appear?
            </button>

            <button
              type="button"
              onClick={() => setQuery("Was vegetation lost?")}
              disabled={loading}
            >
              Was vegetation lost?
            </button>

            <button
              type="button"
              onClick={() => setQuery("Where are the largest changes?")}
              disabled={loading}
            >
              Where are the largest changes?
            </button>
          </div>

          {/* LOADING */}

          {loading && (
            <div className="loading-message">
              Analyzing satellite images...
            </div>
          )}

          {/* ERROR */}

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {/* ==================================
              FOLLOW-UP TRIGGER
          ================================== */}

          {result && (
            <button
              type="button"
              className="follow-up-trigger"
              onClick={() => setShowFollowUpModal(true)}
            >
              <span className="follow-up-trigger-label">
                FOLLOW-UP ANALYSIS
              </span>
              <span className="follow-up-trigger-title">
                Ask a follow-up question
                {followUpThread.length > 0 &&
                  ` (${followUpThread.length})`}
              </span>
              <span className="explore-arrow">→</span>
            </button>
          )}

          {/* ==================================
              RESULT
          ================================== */}

          {result && (
            <section className="result-card">
              <div className="result-header">
                <span className="result-label">
                  ANALYSIS RESULT
                </span>

                <span className="result-status">
                  Complete
                </span>
              </div>

              <p className="result-message">
                {result.message}
              </p>

              {result.summary && (
                <div className="result-summary">
                  <div>
                    <strong>
                      {result.summary.detectedRegions}
                    </strong>

                    <span>
                      Regions detected
                    </span>
                  </div>

                  <div>
                    <strong>
                      {result.summary.changedAreaPercentage}%
                    </strong>

                    <span>
                      Estimated changed area
                    </span>
                  </div>

                  <div>
                    <strong>
                      {result.summary.largestRegionPixels}
                    </strong>

                    <span>
                      Largest region
                    </span>
                  </div>
                </div>
              )}

              {result.changes?.length > 0 && (
                <div className="change-list">
                  <h4>Candidate Changes</h4>

                  {result.changes.map((change) => (
                    <div
                      className="change-item"
                      key={change.id}
                    >
                      <div>
                        <strong>
                          Change {change.id}
                        </strong>

                        <span>
                          {change.type}
                        </span>
                      </div>

                      <span className="confidence">
                        {Math.round(
                          change.confidence * 100
                        )}
                        %
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {result.query && (
                <div className="query-result">
                  <span>Your question</span>

                  <strong>
                    "{result.query}"
                  </strong>
                </div>
              )}

              {/* ==================================
                  EXPLORE BUTTON
              ================================== */}

              <button
                type="button"
                className="explore-button"
                onClick={() =>
                  setShowVisualization(true)
                }
              >
                <span>
                  Explore Changes
                </span>

                <span className="explore-arrow">
                  →
                </span>
              </button>

              {/* ==================================
                  DOWNLOAD REPORT
              ================================== */}

              <button
                type="button"
                className="explore-button download-report-button"
                onClick={() => handleDownloadReport("change")}
              >
                <span>
                  Download Report
                </span>

                <span className="explore-arrow">
                  ↓
                </span>
              </button>
            </section>
          )}
        </section>
        </>
        )}

        {mode === "vqa" && (
        <>
        {/* ====================================
            SINGLE IMAGE INPUT
        ==================================== */}

        <section className="upload-section vqa-upload-section">
          <div className="upload-card">
            <div className="card-heading">
              <span>01</span>
              <h3>Satellite Image</h3>
            </div>

            <div className="image-upload">
              {vqaImage ? (
                <div className="image-preview">
                  <img
                    src={vqaImage}
                    alt="Uploaded satellite imagery"
                  />

                  <button
                    type="button"
                    className="remove-image-button"
                    onClick={removeVqaImage}
                    aria-label="Remove image"
                    title="Remove image"
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M3 6h18" />
                      <path d="M8 6V4h8v2" />
                      <path d="M19 6l-1 14H6L5 6" />
                      <path d="M10 11v5" />
                      <path d="M14 11v5" />
                    </svg>
                  </button>

                  <div className="image-label">
                    IMAGE
                  </div>
                </div>
              ) : (
                <label className="upload-placeholder">
                  <span className="upload-icon">↑</span>

                  <strong>Upload satellite image</strong>

                  <small>PNG, JPG, JPEG or GeoTIFF</small>

                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleVqaUpload}
                  />
                </label>
              )}
            </div>
          </div>
        </section>

        {/* ====================================
            VQA QUERY
        ==================================== */}

        <section className="query-section">
          <label htmlFor="vqa-query">Ask a question about this image</label>

          <div className="query-box">
            <input
              id="vqa-query"
              type="text"
              placeholder='Try: "Is there a river in this image?"'
              value={vqaQuery}
              onChange={(event) => setVqaQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  handleVqaAsk();
                }
              }}
              disabled={vqaLoading}
            />

            <button
              type="button"
              onClick={handleVqaAsk}
              disabled={vqaLoading}
            >
              {vqaLoading ? "Analyzing..." : "Ask →"}
            </button>
          </div>

          <p className="query-hint">
            Ask about vegetation, water, buildings, or the general scene.
          </p>

          <div className="query-suggestions">
            <button
              type="button"
              onClick={() => setVqaQuery("What is visible in this image?")}
              disabled={vqaLoading}
            >
              What is visible in this image?
            </button>

            <button
              type="button"
              onClick={() => setVqaQuery("Is there a river in this image?")}
              disabled={vqaLoading}
            >
              Is there a river in this image?
            </button>

            <button
              type="button"
              onClick={() => setVqaQuery("Are there any buildings here?")}
              disabled={vqaLoading}
            >
              Are there any buildings here?
            </button>

            <button
              type="button"
              onClick={() => setVqaQuery("Describe the vegetation cover.")}
              disabled={vqaLoading}
            >
              Describe the vegetation cover.
            </button>
          </div>

          {/* LOADING */}

          {vqaLoading && (
            <div className="loading-message">
              Analyzing image...
            </div>
          )}

          {/* ERROR */}

          {vqaError && (
            <div className="error-message">
              {vqaError}
            </div>
          )}

          {/* ==================================
              FOLLOW-UP TRIGGER
          ================================== */}

          {vqaResult && (
            <button
              type="button"
              className="follow-up-trigger"
              onClick={() => setShowFollowUpModal(true)}
            >
              <span className="follow-up-trigger-label">
                FOLLOW-UP QUESTION
              </span>
              <span className="follow-up-trigger-title">
                Ask a follow-up question
                {followUpThread.length > 0 &&
                  ` (${followUpThread.length})`}
              </span>
              <span className="explore-arrow">→</span>
            </button>
          )}

          {/* ==================================
              VQA RESULT
          ================================== */}

          {vqaResult && (
            <section className="result-card">
              <div className="result-header">
                <span className="result-label">
                  VQA RESULT
                </span>

                <span className="result-status">
                  Complete
                </span>
              </div>

              <p className="result-message">
                {vqaResult.message}
              </p>

              {vqaResult.stats && (
                <div className="result-summary">
                  {Object.entries(vqaResult.stats).map(([label, value]) => (
                    <div key={label}>
                      <strong>{value}</strong>
                      <span>{label}</span>
                    </div>
                  ))}
                </div>
              )}

              {vqaResult.query && (
                <div className="query-result">
                  <span>Your question</span>

                  <strong>
                    "{vqaResult.query}"
                  </strong>
                </div>
              )}

              {/* ==================================
                  DOWNLOAD REPORT
              ================================== */}

              <button
                type="button"
                className="explore-button download-report-button"
                onClick={() => handleDownloadReport("vqa")}
              >
                <span>
                  Download Report
                </span>

                <span className="explore-arrow">
                  ↓
                </span>
              </button>
            </section>
          )}
        </section>
        </>
        )}
      </main>

      {/* ======================================
          VISUALIZATION WORKSPACE
      ====================================== */}

      {showVisualization && (
        <div className="visualization-overlay">
          <div className="visualization-modal">

            {/* HEADER */}

            <div className="visualization-header">

              <div>

                <span className="section-label">
                  SATELLITE ANALYSIS
                </span>

                <h2>
                  Change Visualization
                </h2>

                <p>
                  Explore the processing outputs for this
                  satellite image pair.
                </p>

              </div>

              <button
                type="button"
                className="close-button"
                onClick={() => setShowVisualization(false)}
              >
                ×
              </button>

            </div>

            {/* BODY */}

            <div className="visualization-body">

              {/* LAYER SIDEBAR */}

              <aside className="visualization-sidebar">

                <div className="sidebar-title">
                  VISUALIZATION LAYERS
                </div>

                {visualizationLayers.map((layer) => (
                  <button
                    type="button"
                    key={layer.id}
                    className={`layer-button ${
                      activeLayer === layer.id
                        ? "active"
                        : ""
                    }`}
                    onClick={() => setActiveLayer(layer.id)}
                  >
                    <span className="layer-name">
                      {layer.name}
                    </span>

                    <span className="layer-description">
                      {layer.description}
                    </span>
                  </button>
                ))}

              </aside>

              {/* IMAGE AREA */}

              <section className="visualization-view">

                <div className="visualization-toolbar">

                  <div>

                    <span className="view-label">
                      CURRENT VIEW
                    </span>

                    <strong>
                      {
                        visualizationLayers.find(
                          (layer) =>
                            layer.id === activeLayer
                        )?.name
                      }
                    </strong>

                  </div>

                  {activeLayer === "regions" && result?.summary && (
                    <div className="view-stat">

                      <strong>
                        {result.summary.detectedRegions}
                      </strong>

                      <span>
                        regions
                      </span>

                    </div>
                  )}

                </div>

                <div className="visualization-image">

                  {activeLayer === "compare" ? (
                    renderComparisonSlider()
                  ) : getActiveVisualization() ? (
                    <img
                      src={getActiveVisualization()}
                      alt="Satellite visualization"
                    />
                  ) : (
                    <div className="visualization-empty">

                      <strong>
                        Processing output unavailable
                      </strong>

                      <span>
                        This visualization will appear once the
                        analysis backend processes the current
                        image pair.
                      </span>

                    </div>
                  )}

                </div>

              </section>

            </div>

            {/* FOOTER */}

            <div className="visualization-footer">

              <span>
                SatQuery AI · Earth Observation Analysis
              </span>

              <button
                type="button"
                onClick={() => setShowVisualization(false)}
              >
                Back to Analysis
              </button>

            </div>

          </div>
        </div>
      )}

      {/* ======================================
          FOLLOW-UP MODAL
      ====================================== */}

      {showFollowUpModal && (
        <div className="followup-overlay">
          <div className="followup-modal">

            {/* HEADER */}

            <div className="followup-header">
              <div>
                <span className="section-label">
                  FOLLOW-UP ANALYSIS
                </span>

                <h2>Ask about this analysis</h2>
              </div>

              <button
                type="button"
                className="close-button"
                onClick={() => setShowFollowUpModal(false)}
              >
                ×
              </button>
            </div>

            {/* THREAD */}

            <div className="followup-thread">
              {followUpThread.length === 0 && !followUpLoading && (
                <div className="followup-empty">
                  <strong>No follow-up questions yet</strong>
                  <span>
                    {mode === "vqa"
                      ? "Ask something else about this image — the model will answer using the same image."
                      : "Ask something about the same before/after pair — the model will answer using the current images."}
                  </span>
                </div>
              )}

              {followUpThread.map((entry, index) => (
                <div className="followup-exchange" key={index}>
                  <div className="followup-question">
                    <span>You</span>
                    <p>{entry.query}</p>
                  </div>

                  <div className="followup-answer">
                    <span>SatQuery AI</span>
                    <p>{entry.response.message}</p>
                  </div>
                </div>
              ))}

              {followUpLoading && (
                <div className="loading-message">
                  Analyzing follow-up...
                </div>
              )}

              {followUpError && (
                <div className="error-message">{followUpError}</div>
              )}
            </div>

            {/* COMPOSER */}

            <div className="followup-composer">
              <input
                type="text"
                placeholder="Ask a follow-up question..."
                value={followUpQuery}
                onChange={(event) =>
                  setFollowUpQuery(event.target.value)
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    handleFollowUpAsk();
                  }
                }}
                disabled={followUpLoading}
              />

              <button
                type="button"
                onClick={handleFollowUpAsk}
                disabled={followUpLoading}
              >
                {followUpLoading ? "Asking..." : "Ask →"}
              </button>
            </div>

          </div>
        </div>
      )}

            <footer>

        <span>
          SatQuery AI
        </span>

        <span>
          AI-Powered Earth Observation
        </span>

      </footer>

    </div>
  );
}

export default App;