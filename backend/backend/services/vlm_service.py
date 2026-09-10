"""VLM captioning service: wraps models/vlm/load.py for the backend.

OWNER: P1
STATUS: placeholder created by P1 on 31 Aug so the repo structure matches
        section 4 of the plan. P1 replaces this file.

Returns a caption string for one image. The only generative path in the
system -- every other intent is templated (docs/fusion_design.md).

Note for whoever touches this: images under 512px are silently refused by
Qwen2.5-VL. load.py upscales first; do not bypass that.
"""

raise NotImplementedError("P1 owns this file. See docstring above.")
