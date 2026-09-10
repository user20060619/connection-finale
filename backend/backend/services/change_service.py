"""Change detection service: Siamese U-Net over an aligned image pair.

OWNER: P2
STATUS: placeholder created by P1 on 31 Aug so the repo structure matches
        section 4 of the plan. P2 replaces this file.

Return shape:

    detect(before_id, after_id) -> {
        "changed_pixels": int, "total_pixels": int,
        "pct_changed": float, "area_changed_km2": float,
    }

Plus a mask PNG written somewhere P5 can fetch, same pixel dimensions as the
displayed source image so the overlay aligns without rescaling.
"""

raise NotImplementedError("P2 owns this file. See docstring above.")
