# Query Router — design note

**Owner:** P1
**Status:** Draft, 31 August 2026. Implementation 3–5 September.
**Files:** `backend/router/intent.py`, `backend/router/rules.yaml`

This is the piece of SatQuery AI that does not exist in GeoChat or TEOChat
(plan §3). Everything else in the project is a pretrained model with a wrapper
around it. This is the part that answers "what did your team actually build."

---

## The claim, stated precisely

GeoChat answers every question by generating text, including questions whose
answer is a number. A generated number is a plausible-looking token sequence; it
can be wrong in ways that are invisible without ground truth.

SatQuery AI classifies the question first, runs a deterministic tool, and uses
the language model only to write a sentence around a value the tool computed.
When we say vegetation fell 14.2%, that figure came from NDVI arrays and pixel
area, not from a decoder.

The router is what makes that split possible. It is small. It is honest. It is
defensible in ninety seconds.

---

## Three tiers, in order

Each tier runs only if the previous one did not produce a confident answer.

### Tier 1 — rules (`rules.yaml`)

Keyword and pattern matching over a normalised query. Fast, deterministic, and
fully inspectable — I can show a judge exactly why a query routed where it did.

```yaml
vegetation:
  strong: [ndvi, vegetation, forest, green cover, deforestation, crop]
  weak:   [trees, plants, growth, foliage]
  requires_two_images: false
```

`strong` hits alone are enough. `weak` hits need a supporting signal, such as a
change verb or a second image being present.

### Tier 2 — semantic similarity

If no rule fires confidently, embed the query with a small sentence-transformer
and compare against ~40 canonical phrasings per intent. Cosine above threshold
wins.

This is what turns "keyword matching" into something defensible. A judge will
ask "what if I phrase it differently?" — this tier is the answer, and it costs
half a day.

Runs on CPU, a few milliseconds, no VRAM contention with the VLM. If it is not
working by 4 September, it gets cut and the router ships with tiers 1 and 3 only.
That is an acceptable outcome, not a failure.

### Tier 3 — abstention

If neither tier is confident, return `intent: unclear` with a clarifying
question:

> "I can describe this image, measure vegetation change, detect changes between
> two images, or locate buildings. Which of those did you mean?"

**Abstention is a feature and it gets its own demo moment.** A system that says
"I don't know" is more trustworthy than one that always answers, and it is the
honest response to the out-of-scope list in §9. P6's blind test set includes 10
out-of-scope queries specifically to exercise this path.

---

## Signals beyond keywords

The query text is not the only input.

| Signal | Use |
|---|---|
| `n_images` | 2 images makes `change` and `vegetation` far more likely; 1 image rules out `change` entirely |
| Comparative language | "changed", "before", "after", "since", "still", "increase", "decrease", "compared to" |
| Question form | "where" leans `locate`, "what is" leans `describe`, "how much" leans a computed intent |
| Negation | "has it *not* changed" must not route to `describe` on a keyword miss |

The `n_images` signal is worth stating on a slide. A query the text alone cannot
disambiguate often becomes unambiguous once you know how many images arrived.

---

## Undefined combinations, decided now

Enumerated before P6 finds them on 3 September.

| Input | Behaviour |
|---|---|
| 2 images + `describe` | Caption both, return two captions. Do not silently drop one. |
| 1 image + `change` | Abstain. "Change detection needs two images — upload a second." |
| 1 image + `vegetation` | Run NDVI on the single image, report absolute cover, not change. State that it is absolute. |
| 2 images + `locate` | Detect on the *after* image, say which one was used. |
| 0 images | Abstain before routing. |
| Empty or whitespace query | Abstain. Never crash. |

---

## Confidence, and what it means

`confidence` in the response is the router's certainty about **intent
classification only**. It is not a claim about whether the answer is correct.

I will say exactly that if a judge asks, because conflating the two is the sort
of overclaim §9 warns about.

---

## How this gets tested

- P6 writes 50 queries blind (see `docs/test_query_request.md`), including 10
  out-of-scope
- I run the router, we compare against P6's independent labels
- The disagreements are more interesting than the score, and go in `results.md`

The number on the slide is "routing accuracy on 50 queries the router's author
never saw," which is a meaningfully different claim from "20 test queries pass."

---

## Interface

```python
@dataclass
class RouteDecision:
    intent: str        # describe | vegetation | change | locate | unclear
    confidence: float  # 0.0–1.0
    tool: str | None   # service entry point, None when unclear
    reason: str        # which rule or tier fired, for the UI and for debugging
    clarification: str | None  # question to ask when unclear

def route(query: str, n_images: int) -> RouteDecision
```

`reason` is deliberately part of the public return. Being able to show *why* a
query routed where it did, live on stage, is worth more than a slide claiming
the router works.

Pure function. No I/O at call time, no global state, never raises.
