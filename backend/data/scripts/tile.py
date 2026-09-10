"""Tile raw scenes into 512x512 chips.

OWNER: P3
STATUS: placeholder created by P1 on 31 Aug so the repo structure matches
        section 4 of the plan. P3 replaces this file.

Keep tiles at 512px or larger. Qwen2.5-VL silently refuses images below
roughly 512px on a side -- it replies 'there is no image attached' rather than
erroring, which looks exactly like a model quality failure.
Found the hard way on 31 Aug, see docs/vlm_viability.md.
"""

raise NotImplementedError("P3 owns this file. See docstring above.")
