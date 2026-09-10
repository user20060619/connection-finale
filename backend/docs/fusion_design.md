# Fusion Layer — design note

**Owner:** P1
**Status:** Draft, 31 August 2026. Implementation 6–8 September.
**File:** `backend/fusion/explain.py`

The plan specifies this layer in one line: "final sentence with computed values
inserted" (§3). That is not enough to build from, and the choice made here is
what decides whether the project's central claim is literally true or merely
rhetorical. So it gets written down before it gets written.

---

## The decision

**Templates for the three computed intents. The language model touches only
`describe`.**

| Intent | Sentence produced by | Numbers come from |
|---|---|---|
| `describe` | Qwen2.5-VL (generation) | none — nothing is computed |
| `vegetation` | Python template | NDVI arrays, pixel area |
| `change` | Python template | Siamese U-Net mask, pixel area |
| `locate` | Python template | YOLO boxes and counts |
| `unclear` | Fixed string | none |

### Why not have the VLM write the sentence around the number

The tempting design is: compute the number, hand it to the model, ask it to
write nice prose. It reads better. It is also the design that reintroduces
exactly the failure mode we claim to have removed.

A model given "14.2" in a prompt can still emit "approximately 15%", or round,
or add a confident causal claim we never computed ("likely due to seasonal
drought"). Then the number on screen is a generated token again and §1's claim
is false. The whole differentiator from GeoChat evaporates, quietly, in a way no
one on the team would notice until a judge checked.

Templates are less elegant and completely auditable. For a system whose pitch is
"our numbers are computed, not generated," that trade is not close.

**This is a defensible answer to a judge, not an admission of laziness:** we
constrained the generative component to the one task where generation is the
product.

---

## Template sketches

```python
VEGETATION_DECREASE = (
    "Vegetation cover decreased by {pct_change:.1f}% between the two dates. "
    "Mean NDVI fell from {mean_ndvi_before:.3f} to {mean_ndvi_after:.3f}, "
    "affecting approximately {area_changed_km2:.2f} square kilometres. "
    "The highlighted region shows where the decrease is concentrated."
)

CHANGE = (
    "{pct_changed:.1f}% of the scene changed between the two images, "
    "about {area_changed_km2:.2f} square kilometres. "
    "The overlay marks the changed regions."
)

LOCATE = (
    "Detected {count} {class_label} in this image. "
    "Bounding boxes are drawn on the overlay."
)
```

Every value in braces arrives from `computed` in the API response and is
inserted verbatim. The fusion layer does no arithmetic and no rounding beyond
display formatting — P4 rounds server-side to the precision intended for
display, and I do not second-guess it.

### Branching, not arithmetic

Templates are selected by sign and magnitude, which is a presentation choice
rather than a computation:

- `pct_change < -1.0` → decrease template
- `pct_change > 1.0` → increase template
- otherwise → "no significant change" template, and say what the threshold was

The threshold is stated in the output, because "no significant change" without a
threshold is not a claim anyone can check.

---

## Showing the split on screen

§1 says the two paths "can be shown separately on screen." That needs to be real
in the data model, not just narration, so the response keeps `computed` and
`answer` as separate fields (see `docs/api_contract_request.md` §3).

Ask P5 for a small "show computed values" toggle that reveals the raw
`computed` dict beside the sentence. Thirty minutes of frontend work, and it
turns the project's main claim into something a judge can watch happen instead
of something we assert.

---

## What could still go wrong

Worth stating on the limitations slide rather than being caught out on:

- **Templates are rigid.** Unusual results produce stilted sentences. Acceptable.
- **Correct numbers, wrong tool.** If the router misclassifies, the number is
  computed correctly and answers the wrong question. Router accuracy is
  therefore part of answer correctness, and abstention limits the blast radius.
- **`describe` remains fully generative.** Captions can be wrong. We reduce
  exposure to hallucination on quantitative claims; we do not eliminate
  hallucination (§9 says exactly this). Do not overclaim it in the Q&A.
