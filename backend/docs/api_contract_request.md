# API Contract — P1's requirements for P4

**From:** P1 (router, VLM, fusion)
**To:** P4 (backend)
**Date:** 31 August 2026
**Status:** Proposal. Must be agreed and frozen by 2 September per plan §5b.

I consume all four services, so this document states what the router and fusion
layer need from each one. Treat it as my input to the freeze, not as a decision
made without you — push back on anything that is awkward to produce.

---

## 1. Where the router lives and how you call it

`backend/router/intent.py` sits inside your folder but is owned by me (§4).

**Proposal: direct Python import, not an HTTP hop.**

```python
from router.intent import route

decision = route(query: str, n_images: int) -> RouteDecision
```

Reasons: the router is pure text processing with no model of its own, so an
HTTP boundary buys us nothing and costs latency and one more thing that can
fail on stage. If you would rather have it behind HTTP for testing, say so
today and I will build it that way — but I need the answer before I write it.

**My contract to you:** `route()` is a pure function. No global state, no disk
reads at call time, no network. Rules load once at import. It never raises on
bad input; it returns an `unclear` intent instead (see §3).

---

## 2. The one request shape

```
POST /query
```

```json
{
  "query": "Has vegetation decreased here?",
  "image_ids": ["demo_pair_03_before", "demo_pair_03_after"],
  "options": {"force_intent": null}
}
```

- `image_ids` — 1 or 2 entries. Order is [before, after] when there are two.
- `force_intent` — demo escape hatch. When set, the router is bypassed and the
  named tool runs. Lets P3 recover on stage if routing misfires. Null in normal use.

---

## 3. The one response shape

Every response, all four intents, same envelope. This matters for P5 more than
for me — one renderer, four payloads.

```json
{
  "intent": "vegetation",
  "confidence": 0.91,
  "tool": "geo_service.ndvi_change",
  "answer": "Vegetation cover decreased by 14.2% between the two dates...",
  "computed": {},
  "overlay": {},
  "meta": {}
}
```

### `intent`
One of exactly: `describe` | `vegetation` | `water` | `change` | `locate` | `unclear`

**Note on `water`:** the plan's §1 table lists four intents, but §4 already
assigns you NDWI alongside NDVI, and §8 asks for two water-body pairs among
the ten demo images. So the tool is being built regardless — I have given it
its own intent rather than forcing "did the reservoir shrink" into the
vegetation path, where it would return the wrong index. Say if you would
rather fold it into `vegetation` and I will collapse it.

`unclear` is a real, expected outcome, not an error. When no rule fires with
enough confidence the system says so and asks a clarifying question rather than
silently guessing. Please render it as a normal answer, not an error state.

### `computed` — the numbers, per intent

These come from tools, never from the language model. This split is the
project's central claim (§1), so keep the two fields structurally separate in
the response — I want to be able to show them side by side on screen.

| intent | `computed` fields |
|---|---|
| `describe` | `{}` — empty. Nothing is computed for this intent. |
| `vegetation` | `mean_ndvi_before`, `mean_ndvi_after`, `pct_change`, `area_changed_km2`, `threshold_used` |
| `water` | `mean_ndwi_before`, `mean_ndwi_after`, `pct_change`, `area_changed_km2`, `threshold_used` |
| `change` | `changed_pixels`, `total_pixels`, `pct_changed`, `area_changed_km2` |
| `locate` | `count`, `classes` (array of `{class, count}`), `boxes` (array of `[x1,y1,x2,y2,class,score]`) |

All floats rounded server-side to the precision you intend to display. I insert
these values into sentences verbatim — I will not reformat or re-round them.

### `overlay` — what P5 draws

```json
{"type": "mask", "url": "/static/overlays/abc123.png", "width": 512, "height": 512}
```

`type` is one of `mask` | `boxes` | `none`. For `boxes`, coordinates come from
`computed.boxes` and `url` may be null. Overlay pixel dimensions must match the
displayed source image so P5's canvas aligns without rescaling.

### `meta`

```json
{"source": "live", "elapsed_ms": 1840, "model_version": "vlm_lora_v3"}
```

`source` is `live` or `precomputed`. P3's fallback folder (§5) sets
`precomputed`. I would like this visible in the UI during rehearsal so we always
know which path produced an answer — we can hide it for the actual demo.

---

## 4. Error handling

No HTTP 500s to the frontend during a demo. If a service fails, return 200 with:

```json
{"intent": "vegetation", "confidence": 0.91, "tool": "...",
 "answer": "The vegetation analysis could not complete on this image pair.",
 "computed": {}, "overlay": {"type": "none"},
 "meta": {"source": "error", "detail": "rasterio: band 8 missing"}}
```

A blank screen reads as a crash even when the system is fine (§P5). Same
reasoning applies at the API layer.

---

## 5. What I need from you, and when

| # | Item | Needed by |
|---|---|---|
| 1 | Import vs HTTP decision for the router | **Today, 31 Aug** |
| 2 | Confirm or amend every field above | 1 Sep |
| 3 | Mock `/query` returning all four intents in this shape | 31 Aug, per plan |
| 4 | Frozen contract document | 2 Sep |

I will build the router against your mock from 3 September, so the mock's shape
matters as much as the real one. If you change a field name after the freeze,
tell the channel — it breaks me and P5 simultaneously.
