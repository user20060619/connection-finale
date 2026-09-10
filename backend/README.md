# SatQuery AI

Interactive vision-language assistant for remote sensing imagery.
SIH26167 · ISRO · Smart India Hackathon 2026, internal round.
Prototype demonstration: **11 September 2026**.

A user loads one or two satellite images, asks a question in plain English, and
gets an answer grounded in the image — text plus a visual overlay.

**The design decision that matters:** a query router picks the right analysis
tool, the tool computes the numbers, and the language model only writes the
sentence around them. When we report vegetation fell 14.2%, that came from NDVI
arrays and pixel area, not from a decoder.

---

## Setup

Fedora 44 / KDE Plasma. System Python is 3.14, which PyTorch does not support,
so the project pins its own 3.12 via `uv`.

```bash
uv venv --python 3.12 .venv
VIRTUAL_ENV=.venv uv pip install torch torchvision --torch-backend=cu126
VIRTUAL_ENV=.venv uv pip install -r requirements.txt
```

No system CUDA toolkit needed — the wheels bundle their own runtime.

---

## What runs today

```bash
# Full pipeline: router -> service stub -> fusion.  No GPU needed.
.venv/bin/python backend/pipeline.py
.venv/bin/python backend/pipeline.py "did the reservoir shrink" --images 2
.venv/bin/python backend/test_pipeline.py

# Router on its own, with scores and reasoning shown
.venv/bin/python backend/router/demo.py --images 2
.venv/bin/python backend/router/test_router.py -v

# Fusion templates
.venv/bin/python backend/fusion/explain.py

# Real RSICD satellite images for model testing
.venv/bin/python data/scripts/fetch_rsicd_sample.py --n 14

# End-to-end with the REAL model (needs GPU)
HF_HOME=$PWD/.hf .venv/bin/python backend/pipeline.py \
  "what is visible here" --vlm --image data/raw/rsicd_sample/park_62.jpg

# VLM smoke test and benchmark
.venv/bin/python models/vlm/load.py --smoke --image data/raw/rsicd_sample/park_62.jpg
.venv/bin/python models/vlm/load.py --bench data/raw/rsicd_sample

# Caption quality vs RSICD ground truth (the Phase 1 go/no-go)
.venv/bin/python models/vlm/compare_captions.py

# Validate P3's instruction pairs before bulk generation
.venv/bin/python data/scripts/validate_instructions.py data/instructions/sample20.jsonl
```

---

## Ownership

One owner per folder. Do not edit someone else's without saying so first —
this single rule prevents most merge conflicts in a two-week project.

| Path | Owner |
|---|---|
| `backend/router/`, `backend/fusion/`, `models/vlm/` | P1 |
| `backend/services/change_service.py`, `detect_service.py`, `models/change/` | P2 |
| `data/` | P3 |
| `backend/main.py`, `backend/services/geo_service.py`, `backend/storage/` | P4 |
| `frontend/` | P5 |
| `docs/` | P6 |

`backend/router/` sits inside P4's tree but is owned by P1.

Model weights are never committed. They go on Drive with a version in the
filename (`vlm_lora_v3.safetensors`), announced in the team channel.

---

## Documents

| File | For | What |
|---|---|---|
| `docs/api_contract_request.md` | P4 | Response shape. **Frozen 2 Sep.** |
| `docs/instruction_format.md` | P3 | JSONL spec for instruction pairs |
| `docs/test_query_request.md` | P6 | 50 blind test queries |
| `docs/router_design.md` | — | Three-tier routing, abstention |
| `docs/fusion_design.md` | — | Templates vs generation, and why |
| `docs/standup_31aug.md` | all | Day-one messages |

---

## Scope

Four intents, locked. Anything else is out of scope and is stated as such.

| Intent | Example | Tool | Output |
|---|---|---|---|
| `describe` | "What is visible here?" | Qwen2.5-VL-3B | Caption |
| `vegetation` | "Has vegetation decreased?" | NDVI, computed | % change + mask |
| `water` | "Did the reservoir shrink?" | NDWI, computed | % change + mask |
| `change` | "What changed?" | Siamese U-Net | Mask, area, explanation |
| `locate` | "Where are the buildings?" | YOLO / DOTA | Boxes + count |

`water` is not in the plan's §1 table, but §4 assigns NDWI to P4 and §8 asks
for two water-body demo pairs, so the tool is being built regardless. Routing
water questions through NDVI would have returned a confidently wrong number.

Plus `unclear` — the router abstains and asks a clarifying question rather than
guessing. That path is deliberate and gets demonstrated.

---

## Key dates

| Date | Gate |
|---|---|
| 31 Aug | Mock API live |
| 2 Sep | Interface freeze; VLM go/no-go |
| 8 Sep | Every model runs on the RTX 5050 |
| 10 Sep | Code freeze, two rehearsals done |
| 11 Sep | Present |
