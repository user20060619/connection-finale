"""Object detection service: YOLO trained on a DOTA subset.

OWNER: P2
STATUS: placeholder created by P1 on 31 Aug so the repo structure matches
        section 4 of the plan. P2 replaces this file.

Return shape:

    detect(image_id) -> {
        "count": int,
        "classes": [{"class": str, "count": int}, ...],
        "boxes": [[x1, y1, x2, y2, class, score], ...],
    }

Box coordinates in source-image pixels. The fusion layer pluralises class names,
so send singular ("building", not "buildings").
"""

raise NotImplementedError("P2 owns this file. See docstring above.")
