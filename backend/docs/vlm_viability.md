# Qwen2.5-VL-3B viability — go/no-go evidence

**Owner:** P1. Measured 31 August 2026 on the RTX 3060.
**Decision required by:** 2 September (plan §P1).

## Verdict: GO

The base model captions satellite imagery accurately, runs in 2.3 GB of VRAM,
and answers in under 4 seconds. No reason to revisit the model choice.

---

## Measured numbers

| Metric | Value | Budget | |
|---|---|---|---|
| Peak VRAM, 4-bit nf4 | **2.29 GB** | 5050 has 8 GB | 3.5x headroom |
| Median latency | **1.71 s** | 30 s (§10 risk 1) | 17x margin |
| Worst latency | 3.83 s | 30 s | fine |
| Model load | 2.8 s | — | |
| Weights on disk | 7.4 GB | — | |

Measured on the 3060. **P2 and P3 must repeat this on the 5050 by 8 September**
— §P3 is explicit that a promise is not a measurement.

## Caption quality

14 RSICD images, 14 distinct scene classes, scored against RSICD's own
reference captions.

- **14/14 captioned**, mean content overlap **0.440**
- Best: industrial 0.75, park 0.62, denseresidential 0.56
- 0 refusals once the two low-texture scenes get a direct prompt (below)

Example — `park_62.jpg`:

> model: "an urban area... a large green space in the center, which appears to be
> a park... buildings and structures surrounding it... a road running
> horizontally across the top"
>
> RSICD: "the park with a rectangular bareland is surrounded by roads"

Park, buildings, roads. Correct.

---

## Two failures found, both worth knowing

### 1. Images below ~512px are silently refused — FIXED

RSICD ships 224x224 tiles. Qwen2.5-VL replies *"there is no image attached"*
rather than raising, so it looks exactly like a model quality problem.

On the first run this scored the model at 0.100 overlap and printed
"revisit the model choice". That verdict was a harness bug. Upscaling to 672px
took the same model to 0.440.

**Cost if undetected: the team switches models on 2 September for no reason.**

Fixed in `models/vlm/load.py` (`MIN_SIDE = 512`, upscale before inference) and in
`models/vlm/compare_captions.py`, which now counts refusals separately and says
"fix the harness" instead of blaming the model.

**P3:** Sentinel-2 tiles are 512x512 and should clear this, but confirm rather
than assume — the failure is silent.

**Everyone: the same trap is waiting on 8 September** when we compare base
against LoRA. A harness fault that looks like a quality result would send the
fine-tune decision the wrong way.

### 2. Near-featureless scenes get refused — a real limitation

`bareland_48` and `meadow_72` still refuse at full resolution. Both are
genuinely low-texture: pixel standard deviation 8.9 and 7.2, against 40-60 for
normal scenes.

Not a bug. The model sees a near-uniform image and declines to describe it.

A direct prompt recovers both:

> "What land cover type is shown? Answer even if the image is uniform."
> -> *"a uniform green color, which typically represents grassland or vegetation"*

**For P6's limitations slide:** the captioning model declines on very uniform
scenes such as bare land and open meadow. We mitigate with prompt phrasing. This
is honest, specific, and the kind of limit §9 says to state out loud.

---

## What this means for the LoRA fine-tune

The base model already scores 0.440. **That raises the bar for proving the
adapter adds anything**, and plan §10 risk 2 says decide by 8 September.

The metric is defined now, before training, so "measurably better" means a
number rather than an impression:

```bash
python models/vlm/compare_captions.py                      # base    -> 0.440
python models/vlm/compare_captions.py --adapter <path>     # adapter -> ?
```

If the adapter does not clear 0.440 on the same 14 images, take the §10 fallback
and present the router as the contribution. That is a fine outcome — the router
is the novel part either way.

Caveat on the metric: content-word overlap is a screening measure, not BLEU or
CIDEr. It catches a model describing the wrong thing. Do not present it as a
caption-quality benchmark.
