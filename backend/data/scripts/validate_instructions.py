#!/usr/bin/env python3
"""Validate instruction pair JSONL against the format in docs/instruction_format.md.

Usage:
    python data/scripts/validate_instructions.py data/instructions/sample20.jsonl

Owner: P1. P3 runs this before sending pairs. Exit code 0 means the file is
safe to fine-tune on.
"""
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALID_SPLITS = {"train", "val"}


def check_record(rec, lineno, seen_ids, errors, warnings):
    def err(msg):
        errors.append(f"line {lineno}: {msg}")

    for field in ("id", "image", "conversations"):
        if field not in rec:
            err(f"missing required field '{field}'")
            return

    rid = rec["id"]
    if rid in seen_ids:
        err(f"duplicate id '{rid}' (first seen line {seen_ids[rid]})")
    else:
        seen_ids[rid] = lineno

    img = rec["image"]
    if img.startswith("/") or img.startswith("~"):
        err(f"image path must be relative to repo root, got '{img}'")
    elif "\\" in img:
        err(f"image path must use forward slashes, got '{img}'")
    elif not (REPO_ROOT / img).exists():
        err(f"image file does not exist: {img}")

    conv = rec["conversations"]
    if not isinstance(conv, list) or len(conv) != 2:
        err(f"conversations must have exactly 2 turns, got {len(conv) if isinstance(conv, list) else type(conv).__name__}")
        return

    human, gpt = conv
    if human.get("from") != "human":
        err(f"turn 0 'from' must be 'human', got {human.get('from')!r}")
    if gpt.get("from") != "gpt":
        err(f"turn 1 'from' must be 'gpt', got {gpt.get('from')!r}")

    hv = human.get("value", "")
    if "<image>" not in hv:
        err("human turn missing required '<image>' token")
    elif hv.count("<image>") > 1:
        err(f"human turn has {hv.count('<image>')} '<image>' tokens, must be exactly 1")
    elif not hv.startswith("<image>\n"):
        err("human turn must start with '<image>\\n' then the question")

    gv = gpt.get("value", "")
    if not gv.strip():
        err("gpt turn is empty")
    elif gv != gv.strip():
        err("gpt turn has leading or trailing whitespace")
    elif any(m in gv for m in ("**", "- ", "* ", "#")):
        warnings.append(f"line {lineno}: gpt turn looks like markdown, spec says plain prose")

    split = rec.get("meta", {}).get("split")
    if split is None:
        warnings.append(f"line {lineno}: no meta.split, needed to build the held-out set")
    elif split not in VALID_SPLITS:
        err(f"meta.split must be one of {sorted(VALID_SPLITS)}, got {split!r}")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"FAIL  file not found: {path}")
        return 1

    errors, warnings = [], []
    seen_ids, questions, splits, images = {}, Counter(), Counter(), Counter()
    n = 0

    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            n += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"line {lineno}: invalid JSON: {e}")
                continue
            check_record(rec, lineno, seen_ids, errors, warnings)
            try:
                questions[rec["conversations"][0]["value"].split("\n", 1)[1]] += 1
            except (KeyError, IndexError, TypeError):
                pass
            splits[rec.get("meta", {}).get("split")] += 1
            images[rec.get("image")] += 1

    print(f"records:          {n}")
    print(f"unique questions: {len(questions)}")
    print(f"unique images:    {len(images)}")
    print(f"splits:           {dict(splits)}")

    if n:
        val_frac = splits.get("val", 0) / n
        if len(questions) < 5:
            warnings.append(
                f"only {len(questions)} distinct question phrasings across {n} records; "
                "spec asks for at least 10 rotated evenly"
            )
        if val_frac < 0.05:
            warnings.append(f"val split is {val_frac:.1%} of records, spec asks for ~10%")
        dupes = [img for img, c in images.items() if c > 1]
        if dupes:
            warnings.append(
                f"{len(dupes)} image(s) appear more than once; spec says one caption per image"
            )

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    if errors:
        print(f"\nFAIL  {len(errors)} error(s). Do not generate in bulk until these are fixed.")
        return 1
    print(f"\nOK    {n} records valid" + (f", {len(warnings)} warning(s)" if warnings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
