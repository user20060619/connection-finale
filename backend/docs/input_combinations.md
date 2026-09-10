# Input combinations — decided, not discovered

**Owner:** P1. 31 August 2026.
**Why this exists:** four intents times one-or-two images gives combinations the
plan never specifies. Deciding them now means P6 does not find them on 3
September and P4 does not have to guess while wiring services.

Routing verified against the actual implementation, not assumed.

---

## The matrix

| Query intent | 1 image | 2 images |
|---|---|---|
| `describe` | Caption it. | **Caption both, return two captions.** Do not silently drop one. |
| `vegetation` | Absolute NDVI cover, **stated as absolute**, not change. | NDVI change between the pair. Normal case. |
| `water` | Absolute NDWI extent, stated as absolute. | NDWI change. Normal case. |
| `change` | **Abstain.** "Change detection needs two images." | Normal case. |
| `locate` | Normal case. | **Detect on the *after* image, say which one was used.** |
| any | 0 images → abstain before routing | — |
| empty/whitespace query | abstain, never crash | abstain |

Routing for all 12 verified. Three cases still need service-side work below.

---

## Three that need P4 and P2 to act

Routing is right; the tool behaviour underneath is not yet defined.

### 1. `describe` with 2 images → P1 (me)

Router sends both. The VLM service must caption each and the fusion layer must
return both sentences. Currently the stub captions once. **My fix, before 5 Sep.**

### 2. `vegetation` / `water` with 1 image → P4

There is no "change" to compute from one image. The service should return
absolute cover — mean NDVI and the vegetated fraction — and the answer must say
so explicitly: *"Vegetation covers 34% of this image"*, never *"vegetation
decreased"*.

**P4: this needs a separate code path from the two-image case.** If it is easier,
return `{"error": "needs_two_images"}` and I will abstain instead. Tell me which.

### 3. `locate` with 2 images → P2

Detection runs on one image. Convention: **use the second (after) image**, and
the answer states which. Silently picking one is the bug; saying which one is
the fix.

---

## Why abstention is the right default

Every "abstain" above could instead be a guess. A guess produces an answer that
looks identical to a correct one — the failure is invisible until someone checks.

Asking for the missing second image costs one sentence on screen and is
defensible in the Q&A. Answering a change question from one image is the exact
failure mode plan §1 says we are avoiding.

---

## Test coverage

`backend/test_pipeline.py::test_image_count_guards` and `::test_no_images` cover
the abstention paths. The three service-side cases above are **not yet covered**
because their behaviour is not built. Add tests when they are.
