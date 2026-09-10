# SatQuery AI — Connected Version

This repository is the **frontend + real backend, wired together and demo-tested**, for SIH26167 (PoC: 11 Sep 2026).

It merges:
- **`frontend/`** — P5's React interface (unchanged from her repo).
- **`backend/`** — P4's FastAPI backend, pulled in from [satquery-ai-backend](https://github.com/akanksha1209/satquery-ai-backend) with its own `.git` history dropped so it lives here as regular tracked files (simplest for a one-`git clone` demo — no submodule step to forget).

The mock backend that used to live at the project root (`main.py`) has been removed. The frontend now talks to the real backend on `http://localhost:8000`.

---

## How to run it

Two terminals, both from the repo root:

**Backend**
```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```
(`.venv` at the repo root already has every dependency installed — fastapi, opencv, numpy, rasterio, pyyaml, etc.)

**Frontend**
```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. If that port is already taken, Vite will pick another one (e.g. 5174) — the backend's CORS allowlist only includes `5173`, so if you get "Unable to connect to the analysis server," check the port in the address bar first.

---

## What's actually live right now

| Frontend tab | Calls | Backed by |
|---|---|---|
| **Change** (two images) | `POST /analyze` | `geo_service.py`: OpenCV grayscale diff + threshold + contours, with SIFT feature-matching + homography alignment before comparing |
| **VQA** (one image) | `POST /vqa` | `geo_service.py`: pixel-statistic proxies (vegetation via excess-green index, water via an NDWI-style index, structure via Canny edge density) |

Both endpoints return JSON + a set of generated visualization images served from `/outputs/<job_id>/...`.

The Change results view's "Visualization Layers" panel has two frontend-only additions on top of the backend's images:
- **Map View** — a Leaflet map showing an approximate reference location for the scene (the JPGs carry no GPS/GeoTIFF metadata, so this is explicitly labeled illustrative, not a geocoded fix).
- **Change Regions** — now a real client-side `<canvas>` (`OverlayCanvas.jsx`) that composites the backend's change mask under the bounding boxes, drawn from the JSON region coordinates, with a "Show change mask" toggle — instead of only showing the backend's flat pre-rendered JPG.

These close out P5's remaining named deliverables from the plan (`MapView.jsx`, `OverlayCanvas.jsx`).

---

## Fixes made while connecting frontend ↔ backend

The real backend hadn't been tested against the real frontend before this pass. Issues found and fixed, all in `backend/backend/`:

1. **`/vqa` didn't exist at all.** The frontend's whole single-image tab called an endpoint the real backend never implemented (only `/analyze` and a legacy `/query` existed). Added `/vqa` to `main.py` + `analyze_single_image()` to `services/geo_service.py`.
2. **"Alignment" wasn't alignment.** `generate_visualizations()` produced the alignment view via `np.hstack([before, after])` — a plain side-by-side, no registration. Replaced with real SIFT feature-matching + homography (`align_images()`), with a safe fallback to the old behavior if a pair doesn't have enough matchable features. This also improved change-detection accuracy, since the diff is now computed on correctly-registered pixels instead of raw ones.
3. **Heatmap/raw-difference were dominated by a warp artifact.** Once alignment warps `before` onto `after`'s frame, the uncovered border pixels are pure black, which read as a huge fake "difference" and skewed the heatmap's color normalization toward flat blue. Fixed by zeroing invalid border pixels in the diff array before it's saved or normalized.
4. **Change-region IDs were wrong.** Regions were numbered by their index among *all* raw contours (including tiny noise blobs filtered out by `area > 100`), so a 54-region result could show IDs missing "1" and running past 140. Fixed to number by position in the filtered list, so IDs are always `1..N` with no gaps.
5. **VQA water % was near-zero for real water.** The original heuristic checked for "blue-dominant" pixels, which misses turbid/muddy water (common in Indian coastal/estuary imagery — it reads brown-green, not blue). Switched to the same NDWI-style index the rest of the codebase already uses.
6. **Frontend stat cards.** `.result-summary` was a hardcoded 3-column grid with only 3 color themes; VQA's 4th stat (brightness) had nowhere to go but a bare, unstyled row by itself. Made the grid `auto-fit` and added a 4th color theme.

---

## Known gaps vs. the prototype plan — for the team lead

This section exists so nobody discovers these during Q&A. Checked directly against the code, not assumptions:

| Plan item | Status | What's actually there |
|---|---|---|
| **Query router** (`router/intent.py`, `rules.yaml`) | Built, **not live** | Real 3-tier rule/semantic/abstain router exists and looks solid, but `/analyze` and `/vqa` — the endpoints the frontend actually calls — never invoke it. They call `geo_service.py` functions directly and pick an answer template with their own local keyword `if` chains. The router is only reachable through the unused legacy `/query` endpoint. |
| **Fusion layer** (`fusion/explain.py`) | Built, **not live** | Same reachability problem — only used inside `pipeline.py`, behind the same unreachable path. |
| **Change intent** (Siamese U-Net) | **Not built** | `services/change_service.py` and `models/change/siamese_unet.py` are both literal `raise NotImplementedError` stubs, unchanged since day one. What actually runs is the OpenCV diff/threshold approach described above. |
| **Locate intent** (YOLO/DOTA) | **Not built** | `services/detect_service.py` is a stub. No endpoint, no frontend UI for it. |
| **Describe intent** (VLM caption) | Code exists, **not reachable** | `models/vlm/load.py` is real and works standalone (needs GPU + the actual Qwen2.5-VL-3B model), but no live endpoint ever calls it — `/query`'s signature doesn't even expose the `use_vlm` flag needed to trigger it. `services/vlm_service.py` is a stub. |
| **LoRA fine-tune adapter** | **Unverified** | No `.safetensors` or adapter files found anywhere in the repo. |
| **Metadata store** (`storage/metadata.db`) | Built, **not wired** | `storage/database.py`/`create_db.py` exist but `main.py` never imports them. |
| **GeoTIFF / rasterio** | **Not actually used** | `rasterio` is a listed dependency but isn't imported anywhere in `backend/`. Everything runs on plain JPGs via `cv2.imread`. |
| **Optical–SAR paired analysis** | **Not built** | No Sentinel-1/SAR handling anywhere in the code (the plan lists this as a stretch goal, but note the separate official-requirements audit flags it as mandatory). |
| **Input compatibility checking** | **Not built** | No validation of image count/modality/format before processing. |
| **Auditable execution trace** | **Not built** | API responses don't expose which tool/model ran or why. |
| **Confidence values** | Displayed, **not computed** | Every detected region's `"confidence"` is a hardcoded literal `0.85` in `geo_service.py`, not a model output. |
| **Downloadable report** | **Done** | Client-side print-to-PDF, `frontend/src/utils/report.js`. |
| **Vegetation change % (NDVI)** | Computed, **barely surfaced** | Computed on every `/analyze` call, but only ever mentioned in the answer *sentence*, and only if the query text contains a vegetation keyword — there's no persistent stat card for it like Regions/Area/Largest have. The NDVI itself is also a proxy (Blue channel standing in for a real NIR band, since these are plain RGB JPGs), not scientifically real NDVI. |
| **Query-specific display ("one clear answer area")** | **Not built** | The plan's design (Section 1: router picks *one* tool per query) implies the UI should show only the metric relevant to what was asked. Right now `/analyze` always returns and displays the same fixed bundle (regions/area/largest + NDVI + NDWI, every visualization tab) regardless of the query — only the answer sentence changes. Root cause is the same router disconnect above: nothing in the live system ever actually decides "run/show only this one tool." |

**Bottom line:** the two-image Change flow and the single-image VQA tab work end-to-end and are demo-ready — verified live with real test images. But two of the four originally-planned intents (Change via a trained model, Locate) never got built beyond stub files, and the router/fusion architecture — meant to be this project's core original contribution — is fully coded but currently disconnected from every endpoint the frontend uses.

---

## Repo layout

```
SQFINALE/
├── frontend/          React app (P5) — unchanged
├── backend/           FastAPI backend (P4), merged in from her repo
│   ├── backend/
│   │   ├── main.py            FastAPI entry point — /analyze, /vqa, legacy /query
│   │   ├── router/            Query router (built, not wired to live endpoints)
│   │   ├── fusion/            Fusion layer (built, not wired to live endpoints)
│   │   ├── services/
│   │   │   ├── geo_service.py     NDVI/NDWI/change-detection — what actually runs
│   │   │   ├── change_service.py  Stub, NotImplementedError
│   │   │   ├── detect_service.py  Stub, NotImplementedError
│   │   │   └── vlm_service.py     Stub, NotImplementedError
│   │   └── storage/           SQLite schema, not wired into main.py
│   ├── models/         VLM loading + LoRA training scripts, change/detection model stubs
│   └── data/           Dataset download/tiling scripts
├── test-images/        Sample before/after pairs used to verify the connection
└── .venv/              Shared Python environment for the backend
```
