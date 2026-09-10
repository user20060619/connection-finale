#!/usr/bin/env python3
"""Tier 2 of the router: similarity fallback when no rule fires confidently.

Owner: P1.  See docs/router_design.md.

Deliberately dependency-free.  sentence-transformers would mean another model
download competing for the same link, another ~100 MB on P3's offline package,
and more VRAM on a laptop that already has to hold the VLM.  Character n-gram
similarity over canonical phrasings costs nothing and handles the case that
actually matters -- a user phrasing the same question in words the rules do not
list.

If it proves too weak on P6's blind set, `score_all` is the only function that
has to change; swapping in real embeddings later is a local edit.

KNOWN LIMITATION, state this rather than hide it:
    This tier matches spelling, not meaning.  "is the woodland thinner" abstains
    because no canonical phrasing contains "woodland" -- character n-grams
    cannot know it is a synonym for forest.  Real sentence embeddings would
    catch it.  The tier therefore widens coverage over pure keyword matching
    but does not achieve semantic understanding, and the deck should say so.

    Note also that vocabulary added here must not be copied from the test
    queries.  A canonical list containing the test phrasings scores 1.00 on
    them and measures nothing.
"""
from __future__ import annotations

from functools import lru_cache

# Canonical phrasings per intent.  These are what an unmatched query is
# compared against.  Add to them freely -- unlike rules, more examples here
# cannot cause a false positive on another intent, they only sharpen this one.
CANONICAL: dict[str, list[str]] = {
    "describe": [
        "what is visible in this image",
        "describe this satellite image",
        "what can you see here",
        "what does this image show",
        "tell me about this scene",
        "what kind of place is this",
        "summarise this aerial photograph",
        "give an overview of this area",
        "what land use is shown",
        "what is this a picture of",
        "explain what this picture contains",
        "walk me through this image",
    ],
    "vegetation": [
        "has vegetation decreased",
        "how much forest was lost",
        "is there less greenery now",
        "did the tree cover change",
        "measure the ndvi change",
        "how much farmland was cleared",
        "did the crops grow",
        "is the area greener than before",
        "quantify vegetation loss",
        "was there deforestation here",
        "have the woods been cut down",
        "less green than before",
        "how much canopy remains",
    ],
    "water": [
        "did the lake shrink",
        "has the reservoir dried up",
        "how much water was lost",
        "did the river change course",
        "is the flooding worse now",
        "measure the water extent",
        "did the shoreline move",
        "how much of this is underwater",
        "has the pond disappeared",
        "compare water levels",
    ],
    "change": [
        "what changed between these images",
        "what is different now",
        "compare the before and after",
        "show me what was built",
        "how has this area developed",
        "what construction happened here",
        "did the city expand",
        "highlight the differences",
        "what is new in the second image",
        "how much of the scene changed",
        "anything new built here",
        "what has been added since",
    ],
    "locate": [
        "where are the buildings",
        "find all the houses",
        "how many structures are there",
        "locate the roads",
        "count the vehicles",
        "show me where the airport is",
        "detect the objects in this image",
        "mark the buildings",
        "point out the structures",
        "identify what is in this scene",
        "how many rooftops are there",
    ],
}


def _ngrams(text: str, n: int = 3) -> set[str]:
    t = f"  {text.strip()} "
    return {t[i:i + n] for i in range(len(t) - n + 1)}


@lru_cache(maxsize=None)
def _canonical_ngrams(intent: str) -> tuple[frozenset[str], ...]:
    return tuple(frozenset(_ngrams(p)) for p in CANONICAL[intent])


def _dice(a: set[str], b: frozenset[str]) -> float:
    """Sørensen–Dice: robust to length differences, unlike raw overlap."""
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


# Function words carry no intent signal.  "what is the airspeed of a swallow"
# scores 0.44 against 'describe' almost entirely on "what is the" -- so a match
# must also share at least one CONTENT word with the phrasing it matched.
_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "of", "in", "on", "at", "to",
    "and", "or", "with", "this", "that", "there", "it", "its", "here", "now",
    "me", "my", "i", "you", "we", "how", "what", "where", "which", "any",
    "has", "have", "had", "do", "does", "did", "be", "been", "than", "then",
    "for", "from", "by", "some", "all", "about", "please", "can", "could",
}


def _content(text: str) -> set[str]:
    import re
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOP}


def _shares_content(query: str, intent: str) -> bool:
    q = _content(query)
    if not q:
        return False
    return any(q & _content(p) for p in CANONICAL[intent])


def score_all(query: str) -> dict[str, float]:
    """Similarity of `query` to each intent, 0..1.

    An intent scores as its single best-matching canonical phrasing, not the
    mean -- a query matching one phrasing well is a hit, even if it looks
    nothing like the other nine.
    """
    q = _ngrams(query.lower())
    if not q:
        return {k: 0.0 for k in CANONICAL}
    return {
        intent: round(max((_dice(q, c) for c in _canonical_ngrams(intent)), default=0.0), 3)
        for intent in CANONICAL
    }


# Tier-2 acceptance.  Character n-grams match spelling, not meaning, so a
# lone high score proves little -- "what is the airspeed of a swallow" scores
# 0.44 against 'describe' purely on shared letters.  Requiring the winner to
# clearly beat the runner-up is what separates a real match from noise.
MIN_SCORE = 0.34    # below this, nothing is close enough to act on
MIN_MARGIN = 0.06   # winner must lead the runner-up by this much


def best(query: str) -> tuple[str, float]:
    """Best-matching intent and its score, ignoring confidence."""
    scores = score_all(query)
    intent = max(scores, key=scores.get)
    return intent, scores[intent]


def classify(query: str) -> tuple[str | None, float, str]:
    """Tier-2 verdict: (intent, score, reason).

    Returns intent=None when the match is not decisive, which sends the query
    on to tier 3 (abstention) rather than guessing.
    """
    scores = score_all(query)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    (top, top_s), (second, second_s) = ranked[0], ranked[1]

    if top_s < MIN_SCORE:
        return None, top_s, f"no phrasing close enough (best {top} {top_s:.2f})"
    if (top_s - second_s) < MIN_MARGIN:
        return None, top_s, f"{top} and {second} too close ({top_s:.2f} vs {second_s:.2f})"
    if not _shares_content(query, top):
        return None, top_s, f"matched {top} on function words only, no shared content word"
    return top, top_s, f"similar to canonical {top} phrasing ({top_s:.2f})"


if __name__ == "__main__":
    import sys
    probes = sys.argv[1:] or [
        "is the woodland thinner than it used to be",
        "any idea how many rooftops",
        "whats up with the water here",
        "what is the airspeed of a swallow",
    ]
    for p in probes:
        intent, score, reason = classify(p)
        ranked = sorted(score_all(p).items(), key=lambda kv: -kv[1])[:3]
        bar = "  ".join(f"{k}={v:.2f}" for k, v in ranked)
        verdict = intent if intent else "ABSTAIN"
        print(f"{p!r}\n  -> {verdict}\n     {reason}\n     {bar}\n")
