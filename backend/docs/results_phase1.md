# Phase 1 results — VLM go/no-go

**Owner:** P1. Measured 31 August 2026 on the RTX 3060.
**Decision required by:** 2 September (plan §P1).

## Verdict: GO. Keep Qwen2.5-VL-3B.

---

## Measured numbers

| Metric | Value | Budget | Verdict |
|---|---|---|---|
| Peak VRAM, 4-bit nf4 | **2.29 GB** | 8 GB on the 5050 | Large margin |
| Weights resident | 2.25 GB | — | — |
| Model load time | 1.9 s | — | Can load on stage |
| Median caption latency | **1.19 s** | 30 s (§10 risk 1) | 25× margin |
| Worst caption latency | 2.21 s | 30 s | Pass |
| Images captioned | **14/14** | — | No failures |
| Mean content overlap vs RSICD | **0.359** | — | See below |

Hardware: RTX 3060 12 GB, torch 2.13.0+cu126, transformers 5.16.1,
bitsandbytes 0.50.2. Test set: 14 RSICD images, one per scene class, with
reference captions. Raw output in `docs/captions_base.json`.

**The VRAM number is the important one for P3.** At 2.29 GB the model leaves
roughly 5.7 GB free on the 5050 for the change and detection models. The plan
assumed this would be tight; it is not.

---

## Two bugs found and fixed, worth knowing about

### 1. Small images made the model refuse

RSICD chips are 224×224, which Qwen2.5-VL reduces to ~64 visual tokens. At that
size the model frequently answered *"I cannot see any image attached"* rather
than describing it. Ten of fourteen images failed this way.

**This looked exactly like a model quality failure and was not.** The first
evaluation run scored 0.091 mean overlap and printed "base model is not
tracking image content — revisit the model choice." Acting on that number would
have thrown away a working model on day two.

Fix: upscale to 512 px minimum before inference (`MIN_SIDE` in `load.py`).
P3's real Sentinel-2 tiles are 512×512, so this only affects RSICD chips used
for captioning data.

### 2. A terse prompt made it refuse on low-detail scenes

Even at 512 px, bare land and meadow still refused with `"Describe this
satellite image."` — both are near-uniform texture with no structure.

Naming the medium and asking for specific observables fixes both:

> "This is an aerial photograph. Describe the ground surface, colours and any
> structures you can see."

| Prompt | bareland | meadow |
|---|---|---|
| "Describe this satellite image." | refused | refused |
| "What land cover and terrain are visible...?" | ok | ok |
| "This is an aerial photograph. Describe the ground surface..." (adopted) | ok | ok |

A single retry with an alternate prompt now runs automatically on any refusal.

**Lesson for the team:** when a model looks broken, check the harness before
the model. Both of these presented as quality failures and neither was.

---

## On the overlap metric, stated honestly

Content overlap is a **screening metric**: fraction of reference content words
the prediction recovers, best over the five RSICD captions. It catches a model
describing the wrong thing entirely. It is not BLEU, CIDEr or SPICE, and it
should not appear on a slide as if it were.

Its known weakness is visible in the results: `bridge` scores 0.00 while the
caption is arguably correct, because the model said "waterway" where RSICD said
"river". Vocabulary mismatch, not error.

**What it is good for:** a before-and-after comparison against the same
references. Base is 0.359 today. If the LoRA adapter cannot beat that on 8
September, plan §10 risk 2 applies — present the base model and the router.

---

## Consequence for the LoRA fine-tune

The base model already tracks image content well, which **raises the bar for
proving the adapter adds anything**. This is worth saying out loud at standup
rather than discovering it on the 8th.

Two honest outcomes, both acceptable:

1. The adapter measurably beats 0.359 on held-out captions → report the gain.
2. It does not → present the base model, and present the router as the
   contribution. The router is the novel part regardless (§10 risk 2).

What is *not* acceptable is claiming an improvement we did not measure. The
metric and the baseline are both fixed now, before training, which is the only
way "measurably better" means anything.
