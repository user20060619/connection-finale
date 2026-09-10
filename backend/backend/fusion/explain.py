#!/usr/bin/env python3
"""Fusion layer: turn a tool's computed output into the final sentence.

Owner: P1.  Design and rationale: docs/fusion_design.md.

THE RULE THIS FILE EXISTS TO ENFORCE:
    Numbers are computed by tools.  Language is generated or templated.
    The two never mix.

Templates handle every intent whose answer contains a number.  The VLM is used
for exactly one intent -- `describe` -- where generation IS the product.

Why not let the VLM write prose around the computed number?  Because a model
handed "14.2" can still emit "roughly 15%", or round, or bolt on a causal claim
we never computed.  Then the number on screen is a generated token again and the
project's central claim (plan section 1) is quietly false.  Templates are less
elegant and completely auditable.  For a system whose pitch is "our numbers are
computed, not generated," that trade is not close.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Below this magnitude we report "no significant change" rather than a direction.
# Stated in the output, because an unqualified "no significant change" is not a
# claim anyone can check.
SIGNIFICANCE_PCT = 1.0


@dataclass
class Explanation:
    answer: str
    computed: dict[str, Any]
    template_used: str
    generated: bool  # True only when a language model produced the text


# --- templates -------------------------------------------------------------
# Every {placeholder} is filled verbatim from `computed`.  This layer does no
# arithmetic and no rounding beyond display formatting -- P4 rounds server-side
# to the precision intended for display and we do not second-guess it.

VEGETATION_DECREASE = (
    "Vegetation cover decreased by {pct_change_abs:.1f}% between the two dates. "
    "Mean NDVI fell from {mean_ndvi_before:.3f} to {mean_ndvi_after:.3f}, "
    "affecting approximately {area_changed_km2:.2f} square kilometres. "
    "The highlighted region shows where the decrease is concentrated."
)

VEGETATION_INCREASE = (
    "Vegetation cover increased by {pct_change_abs:.1f}% between the two dates. "
    "Mean NDVI rose from {mean_ndvi_before:.3f} to {mean_ndvi_after:.3f}, "
    "across approximately {area_changed_km2:.2f} square kilometres. "
    "The highlighted region shows where the increase is concentrated."
)

VEGETATION_STABLE = (
    "Vegetation cover is essentially unchanged, {pct_change:+.1f}%, which is "
    "below the {significance:.1f}% threshold we treat as significant. "
    "Mean NDVI moved from {mean_ndvi_before:.3f} to {mean_ndvi_after:.3f}."
)

WATER_DECREASE = (
    "Water extent decreased by {pct_change_abs:.1f}% between the two dates. "
    "Mean NDWI fell from {mean_ndwi_before:.3f} to {mean_ndwi_after:.3f}, "
    "a reduction of approximately {area_changed_km2:.2f} square kilometres."
)

WATER_INCREASE = (
    "Water extent increased by {pct_change_abs:.1f}% between the two dates. "
    "Mean NDWI rose from {mean_ndwi_before:.3f} to {mean_ndwi_after:.3f}, "
    "an increase of approximately {area_changed_km2:.2f} square kilometres."
)

WATER_STABLE = (
    "Water extent is essentially unchanged, {pct_change:+.1f}%, below the "
    "{significance:.1f}% threshold we treat as significant."
)

CHANGE = (
    "{pct_changed:.1f}% of the scene changed between the two images, "
    "about {area_changed_km2:.2f} square kilometres "
    "({changed_pixels:,} of {total_pixels:,} pixels). "
    "The overlay marks the changed regions."
)

CHANGE_NONE = (
    "No significant change was detected between the two images. "
    "{pct_changed:.1f}% of pixels differ, which is within the noise we expect "
    "from co-registration and illumination differences."
)

LOCATE = (
    "Detected {count} {label} in this image. "
    "Bounding boxes are drawn on the overlay."
)

LOCATE_NONE = (
    "No {label} were detected in this image above the confidence threshold."
)

LOCATE_MULTI = "Detected {total} objects in this image: {breakdown}."


def _plural(n: int, word: str) -> str:
    if n == 1:
        return word
    return word + ("es" if word.endswith(("s", "x", "ch", "sh")) else "s")


def _vegetation(c: dict) -> tuple[str, str]:
    pct = float(c["pct_change"])
    ctx = {**c, "pct_change_abs": abs(pct), "significance": SIGNIFICANCE_PCT}
    if pct < -SIGNIFICANCE_PCT:
        return VEGETATION_DECREASE.format(**ctx), "VEGETATION_DECREASE"
    if pct > SIGNIFICANCE_PCT:
        return VEGETATION_INCREASE.format(**ctx), "VEGETATION_INCREASE"
    return VEGETATION_STABLE.format(**ctx), "VEGETATION_STABLE"


def _water(c: dict) -> tuple[str, str]:
    pct = float(c["pct_change"])
    ctx = {**c, "pct_change_abs": abs(pct), "significance": SIGNIFICANCE_PCT}
    if pct < -SIGNIFICANCE_PCT:
        return WATER_DECREASE.format(**ctx), "WATER_DECREASE"
    if pct > SIGNIFICANCE_PCT:
        return WATER_INCREASE.format(**ctx), "WATER_INCREASE"
    return WATER_STABLE.format(**ctx), "WATER_STABLE"


def _change(c: dict) -> tuple[str, str]:
    if float(c["pct_changed"]) < SIGNIFICANCE_PCT:
        return CHANGE_NONE.format(**c), "CHANGE_NONE"
    return CHANGE.format(**c), "CHANGE"


def _locate(c: dict) -> tuple[str, str]:
    classes = c.get("classes") or []
    named = [k for k in classes if k.get("count", 0) > 0]

    if len(named) > 1:
        breakdown = ", ".join(
            f"{k['count']} {_plural(k['count'], k['class'])}" for k in named
        )
        return (
            LOCATE_MULTI.format(total=int(c["count"]), breakdown=breakdown),
            "LOCATE_MULTI",
        )

    label_word = named[0]["class"] if named else (
        classes[0]["class"] if classes else "objects"
    )
    count = int(c.get("count", 0))
    label = _plural(count if count else 2, label_word)
    if count == 0:
        return LOCATE_NONE.format(label=label), "LOCATE_NONE"
    return LOCATE.format(count=count, label=label), "LOCATE"


_HANDLERS = {
    "vegetation": _vegetation,
    "water": _water,
    "change": _change,
    "locate": _locate,
}


def explain(intent: str, computed: dict[str, Any] | None = None,
            caption: str | None = None,
            clarification: str | None = None) -> Explanation:
    """Produce the final answer for one query.

    `caption` is used only for intent 'describe' -- it is the VLM's output and
    is the one place generated text reaches the user.
    `clarification` is used only for intent 'unclear'.
    """
    computed = computed or {}

    if intent == "describe":
        # The only generative path.  No computed values exist for this intent,
        # and none are inserted -- so there is nothing here for a model to
        # get numerically wrong.
        return Explanation(
            answer=(caption or "").strip() or "No description could be produced for this image.",
            computed={},
            template_used="VLM_GENERATED",
            generated=True,
        )

    if intent == "unclear":
        return Explanation(
            answer=clarification or "I could not determine what you are asking about.",
            computed={},
            template_used="CLARIFICATION",
            generated=False,
        )

    handler = _HANDLERS.get(intent)
    if handler is None:
        return Explanation(
            answer=f"No explanation is defined for intent '{intent}'.",
            computed=computed,
            template_used="UNKNOWN_INTENT",
            generated=False,
        )

    try:
        answer, template = handler(computed)
    except (KeyError, TypeError, ValueError) as e:
        # A missing computed field is a contract violation, not a user error.
        # Fail visibly to the team, gracefully to the screen (plan section P5:
        # a blank screen reads as a crash).
        return Explanation(
            answer=f"The {intent} analysis completed but its output could not be "
                   f"formatted into an answer.",
            computed=computed,
            template_used=f"ERROR: {type(e).__name__}: {e}",
            generated=False,
        )

    return Explanation(answer, computed, template, generated=False)


if __name__ == "__main__":
    samples = [
        ("vegetation", {"pct_change": -14.2, "mean_ndvi_before": 0.612,
                        "mean_ndvi_after": 0.525, "area_changed_km2": 3.47}),
        ("vegetation", {"pct_change": 0.4, "mean_ndvi_before": 0.601,
                        "mean_ndvi_after": 0.603, "area_changed_km2": 0.02}),
        ("water", {"pct_change": -22.8, "mean_ndwi_before": 0.310,
                   "mean_ndwi_after": 0.239, "area_changed_km2": 1.88}),
        ("change", {"pct_changed": 8.3, "area_changed_km2": 2.11,
                    "changed_pixels": 21740, "total_pixels": 262144}),
        ("change", {"pct_changed": 0.3, "area_changed_km2": 0.08,
                    "changed_pixels": 786, "total_pixels": 262144}),
        ("locate", {"count": 47, "classes": [{"class": "building", "count": 47}]}),
        ("locate", {"count": 0, "classes": [{"class": "building", "count": 0}]}),
        ("locate", {"count": 12, "classes": [{"class": "building", "count": 9},
                                             {"class": "vehicle", "count": 3}]}),
    ]
    for intent, computed in samples:
        e = explain(intent, computed)
        flag = "GENERATED" if e.generated else "computed"
        print(f"[{intent}/{flag}] {e.template_used}")
        print(f"  {e.answer}\n")

    e = explain("describe", caption="An airport with several parked aircraft beside a runway.")
    print(f"[describe/{'GENERATED' if e.generated else 'computed'}] {e.template_used}")
    print(f"  {e.answer}\n")

    e = explain("vegetation", {"pct_change": -14.2})  # deliberately missing fields
    print(f"[contract violation] {e.template_used}")
    print(f"  {e.answer}")
