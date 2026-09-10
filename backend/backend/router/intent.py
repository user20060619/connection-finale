#!/usr/bin/env python3
"""Query router: decide which analysis tool answers a user's question.

Owner: P1.  This is the project's original contribution (plan section 3).

Design: docs/router_design.md.  Three tiers -- deterministic rules, then
semantic similarity (added 4 Sep if time allows), then abstention.

Contract with P4:
    from router.intent import route
    decision = route(query: str, n_images: int) -> RouteDecision

route() is pure.  No I/O at call time, no global mutation, never raises.
Rules load once at import.
"""
from __future__ import annotations

import re
import string
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import yaml

try:                                     # package import
    from .semantic import classify as _semantic_classify
except ImportError:                      # direct script run
    from semantic import classify as _semantic_classify

RULES_PATH = Path(__file__).with_name("rules.yaml")

DESCRIBE = "describe"
VEGETATION = "vegetation"
CHANGE = "change"
LOCATE = "locate"
WATER = "water"
UNCLEAR = "unclear"

CLARIFY_DEFAULT = (
    "I can describe an image, measure vegetation or water change, detect "
    "changes between two images, or locate buildings. Which did you mean?"
)


@dataclass
class RouteDecision:
    """What the router decided, and why.

    `reason` is deliberately public: being able to show why a query routed
    where it did, live, is worth more than a slide claiming the router works.
    """
    intent: str
    confidence: float
    tool: str | None
    reason: str
    clarification: str | None = None
    scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_PUNCT = str.maketrans({c: " " for c in string.punctuation if c not in "-'"})


def normalise(query: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return re.sub(r"\s+", " ", query.lower().translate(_PUNCT)).strip()


def _load_rules(path: Path = RULES_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


RULES = _load_rules()
_INTENTS = RULES["intents"]
_SCORING = RULES["scoring"]
_THRESHOLDS = RULES["thresholds"]
_COMPARATIVE = RULES["comparative_terms"]
_OUT_OF_SCOPE = RULES.get("out_of_scope", {})
_PRIORITY = RULES["priority"]


def _contains_term(text: str, term: str) -> bool:
    """Whole-word/phrase match, so 'change' does not fire inside 'unchanged'."""
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def _check_out_of_scope(text: str) -> tuple[str, str] | None:
    for name, spec in _OUT_OF_SCOPE.items():
        for pat in spec.get("patterns", []):
            if _contains_term(text, pat):
                return name, " ".join(spec["message"].split())
    return None


def _score_intent(name: str, spec: dict, text: str, n_images: int,
                  has_comparative: bool) -> tuple[float, list[str]]:
    score = 0.0
    why: list[str] = []

    strong = [t for t in spec.get("strong", []) if _contains_term(text, t)]
    weak = [t for t in spec.get("weak", []) if _contains_term(text, t)]

    if strong:
        score += _SCORING["strong_hit"]
        why.append(f"strong: {', '.join(strong[:3])}")
    if weak:
        # Weak terms alone should not carry an intent; they accumulate slowly.
        score += min(len(weak), 2) * _SCORING["weak_hit"]
        why.append(f"weak: {', '.join(weak[:3])}")

    if not strong and not weak:
        return 0.0, []

    if spec.get("requires_two_images") and n_images < 2:
        score -= _SCORING["image_count_penalty"]
        why.append("needs 2 images, got 1")
    elif spec.get("prefers_two_images") and n_images >= 2:
        score += _SCORING["two_image_bonus"]
        why.append("2 images supplied")
    elif spec.get("prefers_single_image") and n_images == 1:
        score += _SCORING["single_image_bonus"]
        why.append("single image")

    if has_comparative and name in (CHANGE, VEGETATION, WATER):
        score += _SCORING["comparative_bonus"]
        why.append("comparative language")

    return max(0.0, min(score, _SCORING["max_confidence"])), why


def route(query: str, n_images: int = 1) -> RouteDecision:
    """Classify a query and pick the tool that should answer it."""
    if query is None or not query.strip():
        return RouteDecision(
            UNCLEAR, 0.0, None, "empty query",
            clarification="Ask a question about the image, for example "
                          "'what is visible here?'",
        )

    if n_images < 1:
        return RouteDecision(
            UNCLEAR, 0.0, None, "no images supplied",
            clarification="Upload a satellite image first, then ask a question about it.",
        )

    text = normalise(query)

    oos = _check_out_of_scope(text)
    if oos is not None:
        name, message = oos
        return RouteDecision(
            UNCLEAR, 0.0, None, f"out of scope: {name}", clarification=message
        )

    has_comparative = any(_contains_term(text, t) for t in _COMPARATIVE)

    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}
    for name, spec in _INTENTS.items():
        s, why = _score_intent(name, spec, text, n_images, has_comparative)
        scores[name] = round(s, 3)
        reasons[name] = why

    ranked = sorted(
        scores.items(),
        key=lambda kv: (-kv[1], _PRIORITY.index(kv[0]) if kv[0] in _PRIORITY else 99),
    )
    top_name, top_score = ranked[0]
    runner_name, runner_score = ranked[1] if len(ranked) > 1 else (None, 0.0)

    # Tier 2: no rule fired confidently, so compare against canonical phrasings.
    if top_score < _THRESHOLDS["accept"]:
        sem_intent, sem_score, sem_reason = _semantic_classify(text)
        if sem_intent is not None:
            # A change question still needs two images, whichever tier found it.
            if sem_intent == CHANGE and n_images < 2:
                return RouteDecision(
                    UNCLEAR, round(sem_score, 3), None,
                    f"tier2: {sem_reason}, but change needs two images",
                    clarification="Change detection needs two images. Upload a "
                                  "second image taken at a different date.",
                    scores=scores,
                )
            return RouteDecision(
                intent=sem_intent,
                confidence=round(min(sem_score + 0.10, _SCORING["max_confidence"]), 3),
                tool=_INTENTS[sem_intent]["tool"],
                reason=f"tier2: {sem_reason}",
                scores={**scores, f"tier2_{sem_intent}": round(sem_score, 3)},
            )

        # Tier 3: abstain rather than guess.
        return RouteDecision(
            UNCLEAR, round(top_score, 3), None,
            f"no rule matched; {sem_reason}",
            clarification=CLARIFY_DEFAULT, scores=scores,
        )

    # Two intents too close to separate: ask, do not coin-flip.
    if runner_name and (top_score - runner_score) < _THRESHOLDS["ambiguous"]:
        return RouteDecision(
            UNCLEAR, round(top_score, 3), None,
            f"ambiguous between {top_name} and {runner_name}",
            clarification=(
                f"Did you want me to {_ASK[top_name]} or {_ASK[runner_name]}?"
            ),
            scores=scores,
        )

    # A change question that needs two images but only got one.
    if top_name == CHANGE and n_images < 2:
        return RouteDecision(
            UNCLEAR, round(top_score, 3), None, "change needs two images",
            clarification="Change detection needs two images. Upload a second "
                          "image taken at a different date.",
            scores=scores,
        )

    return RouteDecision(
        intent=top_name,
        confidence=round(top_score, 3),
        tool=_INTENTS[top_name]["tool"],
        reason="; ".join(reasons[top_name]) or "matched rules",
        scores=scores,
    )


_ASK = {
    DESCRIBE: "describe what is in the image",
    VEGETATION: "measure vegetation change",
    WATER: "measure water extent change",
    CHANGE: "detect what changed between the images",
    LOCATE: "locate objects in the image",
}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        d = route(q, n_images=2)
        print(f"{q!r}\n  -> {d.intent} ({d.confidence}) via {d.tool}\n"
              f"     reason: {d.reason}")
        if d.clarification:
            print(f"     asks: {d.clarification}")
    else:
        print(__doc__)
