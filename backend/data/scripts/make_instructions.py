"""Convert RSICD captions into instruction pairs for the LoRA fine-tune.

OWNER: P3
STATUS: placeholder created by P1 on 31 Aug so the repo structure matches
        section 4 of the plan. P3 replaces this file.

Format spec: docs/instruction_format.md
Validate before bulk generation:

    python data/scripts/validate_instructions.py <file.jsonl>

Three things that cost a regeneration if wrong: rotate at least 10 question
phrasings, use one caption per image (not all five), hold out ~10 percent as val.
"""

raise NotImplementedError("P3 owns this file. See docstring above.")
