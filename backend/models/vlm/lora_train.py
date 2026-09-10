"""LoRA fine-tune of Qwen2.5-VL-3B on P3's instruction pairs.

OWNER: P1
STATUS: placeholder created by P1 on 31 Aug so the repo structure matches
        section 4 of the plan. P1 replaces this file.

Runs on the 3060 only, never the demo laptop (plan section P1).

Base model scores 0.440 mean content overlap (docs/vlm_viability.md), so that
is the number to beat. Evaluate with:

    python models/vlm/compare_captions.py --adapter <path>

If it does not clear 0.440, take the section 10 risk 2 fallback and present the
router as the contribution.
"""

raise NotImplementedError("P1 owns this file. See docstring above.")
