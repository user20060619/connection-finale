#!/usr/bin/env python3
"""Router test harness.  Owner: P1.

These are MY queries, written by me, against rules I wrote.  They prove the
router does what I intended -- they are NOT the accuracy number for the deck.
That number comes from P6's 50 blind queries (docs/test_query_request.md),
because a test written by the author of the rules measures imagination, not
generalisation.

Usage:
    python backend/router/test_router.py           # run the suite
    python backend/router/test_router.py -v        # show every case
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from router.intent import route  # noqa: E402

# (query, n_images, expected_intent)
CASES = [
    # describe
    ("What is visible in this image?", 1, "describe"),
    ("Describe this satellite image.", 1, "describe"),
    ("What can you see in this aerial photograph?", 1, "describe"),
    ("Summarise what this scene shows", 1, "describe"),
    ("what type of area is this", 1, "describe"),

    # vegetation
    ("Has vegetation decreased here?", 2, "vegetation"),
    ("Show me the NDVI change", 2, "vegetation"),
    ("did the forest cover drop", 2, "vegetation"),
    ("How much green cover was lost?", 2, "vegetation"),
    ("deforestation in this area?", 2, "vegetation"),
    ("vegetation change pls", 2, "vegetation"),

    # change
    ("What changed between these two images?", 2, "change"),
    ("what is different between them", 2, "change"),
    ("Show me the urban expansion", 2, "change"),
    ("compare these two images", 2, "change"),
    ("has there been construction here", 2, "change"),

    # locate
    ("Where are the buildings?", 1, "locate"),
    ("How many buildings are there?", 1, "locate"),
    ("locate all the structures", 1, "locate"),
    ("find the roads in this image", 1, "locate"),
    ("count the vehicles", 1, "locate"),

    # abstention: out of scope
    ("What will this area look like in 2030?", 2, "unclear"),
    ("predict future development here", 2, "unclear"),
    ("show me the hyperspectral bands", 1, "unclear"),
    ("what is the population of this city", 1, "unclear"),
    ("compare all the images I uploaded", 2, "unclear"),

    # abstention: nonsense / empty / underspecified
    ("", 1, "unclear"),
    ("   ", 1, "unclear"),
    ("hello", 1, "unclear"),
    ("asdfgh", 1, "unclear"),

    # abstention: wrong image count
    ("What changed between these two images?", 1, "unclear"),
]


# --- tier 2 -----------------------------------------------------------------
# Queries no rule catches.  These exercise the semantic fallback.
# None of these strings appear in semantic.CANONICAL -- a canonical list
# containing its own test queries would score 1.00 and measure nothing.
TIER2_CASES = [
    ("any idea how many rooftops", 1, "locate"),
    ("what is the airspeed of a swallow", 1, "unclear"),
    ("qwerty asdf zxcv", 1, "unclear"),
]


def test_tier2():
    from router.intent import route as _route
    bad = []
    for query, n_images, expected in TIER2_CASES:
        d = _route(query, n_images)
        if d.intent != expected:
            bad.append(f"{query!r}: expected {expected}, got {d.intent} ({d.reason})")
    return bad


def main():
    verbose = "-v" in sys.argv
    passed = failed = 0
    failures = []

    for query, n_images, expected in CASES:
        d = route(query, n_images)
        ok = d.intent == expected
        passed += ok
        failed += not ok
        if verbose or not ok:
            mark = "ok  " if ok else "FAIL"
            print(f"{mark} {query!r} (n={n_images})")
            print(f"       expected {expected}, got {d.intent} "
                  f"({d.confidence}) -- {d.reason}")
            if d.clarification and verbose:
                print(f"       asks: {d.clarification[:70]}...")
        if not ok:
            failures.append((query, expected, d.intent))

    tier2_bad = test_tier2()
    for msg in tier2_bad:
        print(f"FAIL tier2 {msg}")
    passed += len(TIER2_CASES) - len(tier2_bad)
    failed += len(tier2_bad)
    failures.extend((m, "", "") for m in tier2_bad)

    total = passed + failed
    print(f"\n{passed}/{total} passed")
    if failures:
        print("\nfailures:")
        for q, exp, got in failures:
            print(f"  {q!r}: expected {exp}, got {got}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
