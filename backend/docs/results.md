# Results

**OWNER:** P6
**STATUS:** placeholder created by P1 on 31 Aug. P6 collects and owns this.

Measured numbers, not claims. P2 supplies model metrics, P5 supplies
screenshots, P1 supplies router and VLM numbers.

## Already measured (P1, 31 Aug — full evidence in docs/vlm_viability.md)

| Metric | Value | Note |
|---|---|---|
| VLM peak VRAM (4-bit) | **2.29 GB** | 5050 has 8 GB |
| VLM median latency | **1.71 s** | budget is 30 s |
| Caption content overlap vs RSICD | **0.440** | 14/14 images captioned |
| Router test suite | **34/34** | P1's own cases |
| Pipeline contract tests | **6/6** | |

**Router accuracy on P6's blind queries: _pending_** — this is the number that
belongs on the slide, because P1 did not write those queries. See
docs/test_query_request.md.

## Still needed

- [ ] P2: IoU or F1 for change detection
- [ ] P2: mAP for detection
- [ ] P2: both models' latency **on the 5050**, not the 4060
- [ ] P5: screenshots
- [ ] P1: base vs LoRA comparison (decide by 8 Sep, plan section 10 risk 2)
