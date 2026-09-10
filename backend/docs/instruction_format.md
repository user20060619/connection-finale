# Instruction Pair Format — spec for P3

**From:** P1 (fine-tuning)
**To:** P3 (data)
**Date:** 31 August 2026
**Applies to:** `data/instructions/*.jsonl`, generated from RSICD, target ~2000 pairs

Per plan §P3, I validate a sample of 20 before you generate in bulk. This
document is the format to validate against. Generate 20, send them, I confirm,
then you run the full 2000. Please do not skip the sample step — regenerating
2000 pairs on 4 September costs a day we do not have.

---

## File format

One JSON object per line, UTF-8, `.jsonl`. No wrapping array, no trailing commas.

```json
{"id": "rsicd_00042", "image": "data/tiles/rsicd/airport_12.jpg", "conversations": [{"from": "human", "value": "<image>\nDescribe this satellite image."}, {"from": "gpt", "value": "An airport with several parked aircraft beside a long runway, surrounded by open grassland."}], "meta": {"source": "RSICD", "class": "airport", "split": "train"}}
```

Formatted for reading (the actual file is one line per record):

```json
{
  "id": "rsicd_00042",
  "image": "data/tiles/rsicd/airport_12.jpg",
  "conversations": [
    {"from": "human", "value": "<image>\nDescribe this satellite image."},
    {"from": "gpt",   "value": "An airport with several parked aircraft..."}
  ],
  "meta": {"source": "RSICD", "class": "airport", "split": "train"}
}
```

---

## Field rules

| Field | Rule |
|---|---|
| `id` | Unique across the whole file. `rsicd_00001` … `rsicd_02000`. |
| `image` | Path **relative to repo root**, forward slashes, no `~` and no absolute paths. The file must exist — a broken path is a crash mid-training, not a warning. |
| `conversations` | Exactly two turns, human then gpt, in that order. Single turn only — multi-turn is out of scope (§9). |
| `from` | Lowercase, exactly `human` and `gpt`. |
| `value` (human) | **Must** contain the literal token `<image>` followed by `\n` then the question. One `<image>` token per record, no more. |
| `value` (gpt) | The answer. Plain prose, no markdown, no bullet points, no leading/trailing whitespace. |
| `meta.split` | `train` or `val`. Hold out 10%, roughly 200 records, as `val`. I need a held-out set to prove the adapter beat the base model (§P1, 6–8 Sep). |
| `meta.class` | RSICD's scene class if available. Not used in training, but lets me report per-class accuracy if the numbers are interesting. |

---

## Question variety — the part that matters most

RSICD gives you captions, not questions. If all 2000 human turns read
"Describe this satellite image.", the model learns one phrasing and the fine-tune
is worthless for anything else.

**Rotate across at least 10 templates, roughly evenly.** Suggested set:

```
Describe this satellite image.
What is visible in this image?
What can you see in this aerial photograph?
Summarise what this satellite image shows.
What type of area is shown here?
Describe the main features in this scene.
What land use is visible in this image?
Give a short description of this satellite image.
What does this remote sensing image depict?
Describe the terrain and structures in this image.
```

Assign the template by hashing the `id` rather than choosing randomly, so the
file is reproducible if you regenerate it.

**Do not paraphrase the captions.** RSICD captions are the ground truth. Vary
the question, keep the answer exactly as RSICD wrote it.

---

## RSICD has five captions per image

Use **one** caption per record, the first one. Do not emit five records for the
same image — that teaches the model to memorise images rather than describe them,
and it inflates 2000 records down to 400 real images of signal.

If you want more data, prefer more images over more captions per image.

---

## Validation before you send

Run this. It must print `OK` with zero errors on your 20-record sample:

```bash
python data/scripts/validate_instructions.py data/instructions/sample20.jsonl
```

I have written that script and committed it — it checks every rule in this
document, including that each image path actually exists on disk. If it passes
for you locally it will pass for me.

---

## Delivery

| What | When |
|---|---|
| 20-record sample, validated | **3 September, morning** |
| My confirmation | Same day, within a few hours |
| Full ~2000 pairs | 5 September |

The fine-tune starts 6 September and cannot start without this file. It is the
one hard dependency in my whole schedule.
