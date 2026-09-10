#!/usr/bin/env python3
"""Pull a small RSICD sample from the HuggingFace datasets server.

Owner: P1.  Purpose: give me real satellite imagery for the Phase 1 go/no-go
without waiting on P3's full pipeline.  P3 still owns the real download and the
2000 instruction pairs -- this is a sample for model testing, not the dataset.

Usage:
    python data/scripts/fetch_rsicd_sample.py --n 12
"""
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://datasets-server.huggingface.co/rows"
DATASET = "arampacha/rsicd"


def fetch_rows(split, offset, length):
    q = urllib.parse.urlencode({
        "dataset": DATASET, "config": "default",
        "split": split, "offset": offset, "length": length,
    })
    with urllib.request.urlopen(f"{API}?{q}", timeout=60) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--split", default="test")
    ap.add_argument("--out-dir", default="data/raw/rsicd_sample")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    data = fetch_rows(args.split, 0, args.n)
    manifest = []

    for row in data["rows"]:
        r = row["row"]
        name = Path(r["filename"]).name
        url = r["image"]["src"]
        dest = out / name
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                dest.write_bytes(resp.read())
        except Exception as e:                       # noqa: BLE001
            print(f"  skip {name}: {e}")
            continue
        manifest.append({
            "image": str(dest),
            "filename": r["filename"],
            "captions": r["captions"],
        })
        print(f"  {name}  ({dest.stat().st_size // 1024} KB)")

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(manifest)} images -> {out}")
    print(f"manifest: {out / 'manifest.json'}")
    print("\nReal RSICD imagery with reference captions. Use these to judge")
    print("whether the base model is good enough (Phase 1 go/no-go, 2 Sep).")


if __name__ == "__main__":
    main()
