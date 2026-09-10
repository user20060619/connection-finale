#!/usr/bin/env python3
"""Generate synthetic satellite-like images for smoke testing.

Owner: P1. Placeholder only. Replace with P3's real Sentinel-2 tiles as soon as
they exist -- this proves the pipeline runs, it does not prove the model is good
on real imagery. The Phase 1 go/no-go decision must use real satellite images.

Usage:
    python data/scripts/make_smoke_image.py                 # writes before+after pair
    python data/scripts/make_smoke_image.py --out-dir PATH
"""
import argparse
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image

SIZE = 512


def _fbm(rng, size, octaves=5):
    """Fractal noise, cheap stand-in for terrain texture."""
    out = np.zeros((size, size), dtype=np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        res = max(2, 2 ** (o + 2))
        coarse = rng.random((res, res)).astype(np.float32)
        layer = np.asarray(
            Image.fromarray((coarse * 255).astype(np.uint8)).resize(
                (size, size), Image.BICUBIC
            ),
            dtype=np.float32,
        ) / 255.0
        out += layer * amp
        total += amp
        amp *= 0.5
    return out / total


def make_scene(seed=0, urban_density=0.35, veg_amount=0.45):
    """Build an RGB scene with vegetation, water, bare soil and buildings."""
    rng = np.random.default_rng(seed)
    terrain = _fbm(rng, SIZE)
    moisture = _fbm(rng, SIZE)

    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.float32)

    veg_mask = moisture > (1.0 - veg_amount)
    soil_mask = ~veg_mask
    water_mask = terrain < 0.28

    # bare soil / dry ground
    rgb[soil_mask] = [0.55, 0.47, 0.35]
    # vegetation, varied by terrain so it is not flat
    veg_shade = terrain[veg_mask][:, None]
    rgb[veg_mask] = np.hstack([
        0.12 + 0.10 * veg_shade,
        0.34 + 0.22 * veg_shade,
        0.10 + 0.08 * veg_shade,
    ])
    # water bodies
    rgb[water_mask] = [0.08, 0.18, 0.32]

    # road grid
    spacing = 64
    for x in range(spacing, SIZE, spacing):
        rgb[:, x - 1:x + 1] = [0.42, 0.42, 0.44]
    for y in range(spacing, SIZE, spacing):
        rgb[y - 1:y + 1, :] = [0.42, 0.42, 0.44]

    # buildings, block-aligned so it reads as a settlement not confetti
    n_blocks = int(urban_density * 90)
    for _ in range(n_blocks):
        bx = rng.integers(0, SIZE // spacing) * spacing + 6
        by = rng.integers(0, SIZE // spacing) * spacing + 6
        w = int(rng.integers(10, 26))
        h = int(rng.integers(10, 26))
        if bx + w >= SIZE or by + h >= SIZE:
            continue
        if water_mask[by:by + h, bx:bx + w].mean() > 0.3:
            continue  # do not build on water
        tone = 0.62 + 0.22 * rng.random()
        rgb[by:by + h, bx:bx + w] = [tone, tone * 0.97, tone * 0.92]
        # shadow on one side, gives the tiles depth
        sh = min(3, SIZE - (by + h))
        if sh:
            rgb[by + h:by + h + sh, bx:bx + w] *= 0.55

    # sensor noise
    rgb += rng.normal(0, 0.012, rgb.shape).astype(np.float32)
    return np.clip(rgb, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="data/raw/smoke")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # before: green, low development.  after: built up, vegetation lost.
    before = make_scene(seed=args.seed, urban_density=0.20, veg_amount=0.55)
    after = make_scene(seed=args.seed, urban_density=0.70, veg_amount=0.30)

    for name, arr in (("smoke_before.png", before), ("smoke_after.png", after)):
        Image.fromarray((arr * 255).astype(np.uint8)).save(out / name)
        print(f"wrote {out / name}  {SIZE}x{SIZE}")

    print("\nPlaceholder imagery for pipeline smoke tests only.")
    print("Swap in P3's Sentinel-2 tiles before making any model-quality judgement.")


if __name__ == "__main__":
    main()
