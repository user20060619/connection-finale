#!/usr/bin/env python3
"""Compare model captions against RSICD ground truth.

Owner: P1.  Two uses:

  Phase 1 (2 Sep)  -- is the base model good enough on satellite imagery?
                      This is the go/no-go from plan section P1.
  Phase 3 (8 Sep)  -- did the LoRA adapter actually beat the base model?
                      Plan section 10 risk 2 says decide this by 8 Sep.

Deciding the metric BEFORE training matters.  If "measurably better" is only
defined after seeing the output, it is not a measurement.

Usage:
    python models/vlm/compare_captions.py --manifest data/raw/rsicd_sample/manifest.json
    python models/vlm/compare_captions.py --manifest ... --adapter models/weights/vlm_lora_v1
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

STOP = {
    "a", "an", "the", "is", "are", "was", "were", "of", "in", "on", "at", "to",
    "and", "or", "with", "this", "that", "there", "it", "its", "some", "many",
    "very", "next", "near", "by", "be", "been", "has", "have", "image", "picture",
    "photo", "shows", "showing", "can", "seen", "here",
}


def tokens(text):
    return [w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP]


REFUSAL_MARKERS = (
    "i'm sorry", "i cannot", "i can't", "no image", "not visible",
    "no satellite image", "cannot provide an accurate description",
)


def is_refusal(pred):
    """The model saying it cannot see an image is a harness failure, not a bad
    caption. Counting it as quality-zero hides the real cause -- which is
    exactly what happened on the first run (images below the model's minimum
    resolution)."""
    low = pred.lower()
    return any(m in low for m in REFUSAL_MARKERS)


def content_overlap(pred, refs):
    """Fraction of reference content words the prediction recovers.

    Deliberately crude.  It is a screening metric to catch a model that is
    describing the wrong thing entirely -- not a claim about caption quality.
    Report it as such; do not put it on a slide as if it were BLEU or CIDEr.
    """
    p = set(tokens(pred))
    if not p:
        return 0.0
    best = 0.0
    for ref in refs:
        r = set(tokens(ref))
        if not r:
            continue
        best = max(best, len(p & r) / len(r))
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/raw/rsicd_sample/manifest.json")
    ap.add_argument("--adapter", default=None, help="LoRA adapter dir; omit for base model")
    ap.add_argument("--prompt", default="Describe this satellite image.")
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-new-tokens", type=int, default=96)
    args = ap.parse_args()

    records = json.loads(Path(args.manifest).read_text())
    print(f"{len(records)} images from {args.manifest}")
    print(f"model: {'base + ' + args.adapter if args.adapter else 'base, no adapter'}\n")

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from load import load_model, caption  # noqa: E402

    model, processor, load_s = load_model()
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)
        model.eval()
    print(f"loaded in {load_s:.1f}s\n")

    rows, scores, times = [], [], []
    for i, rec in enumerate(records, 1):
        pred, elapsed, _ = caption(
            model, processor, rec["image"], args.prompt, args.max_new_tokens
        )
        refused = is_refusal(pred)
        score = content_overlap(pred, rec["captions"])
        if not refused:
            scores.append(score)
        times.append(elapsed)
        cls = Path(rec["filename"]).name.rsplit("_", 1)[0]
        rows.append({
            "image": rec["image"], "class": cls, "prediction": pred,
            "references": rec["captions"], "overlap": round(score, 3),
            "seconds": round(elapsed, 2), "refused": refused,
        })
        tag = "REFUSED" if refused else f"overlap {score:.2f}"
        print(f"[{i}/{len(records)}] {cls:18s} {tag:14s} {elapsed:5.2f}s")
        print(f"    pred: {pred[:95]}{'...' if len(pred) > 95 else ''}")
        print(f"    ref:  {rec['captions'][0][:95]}")

    n_refused = sum(1 for r in rows if r["refused"])
    mean = sum(scores) / len(scores) if scores else 0.0
    times.sort()
    print(f"\n{'='*58}")
    print(f"captioned:            {len(scores)}/{len(rows)}")
    if n_refused:
        print(f"REFUSED:              {n_refused}  <- harness problem, not quality")
    print(f"mean content overlap: {mean:.3f}  (over captioned only)")
    print(f"median latency:       {times[len(times)//2]:.2f}s")
    print(f"worst latency:        {times[-1]:.2f}s")

    # Screening thresholds for the Phase 1 go/no-go.  A model scoring near zero
    # is describing something other than what is in the image.
    if n_refused > len(rows) * 0.2:
        print(f"\nVERDICT: {n_refused} refusals -- fix the harness before judging the")
        print("model. Most common cause: images below the model's minimum")
        print("resolution (see MIN_SIDE in load.py).")
    elif mean < 0.15:
        print("\nVERDICT: base model is not tracking image content. Revisit the")
        print("model choice now (plan section P1: day two, not day nine).")
    elif mean < 0.30:
        print("\nVERDICT: weak but usable. Fine-tuning has room to help.")
    else:
        print("\nVERDICT: base model already tracks content well.")
        print("Note: this raises the bar for proving the LoRA adds anything.")

    out = args.out or (
        "docs/captions_lora.json" if args.adapter else "docs/captions_base.json"
    )
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(
        {"adapter": args.adapter, "mean_overlap": round(mean, 4),
         "median_seconds": round(times[len(times)//2], 2), "rows": rows},
        indent=2,
    ))
    print(f"\nwritten to {out}")
    print("Compare base vs adapter with: diff the two mean_overlap values.")


if __name__ == "__main__":
    main()
