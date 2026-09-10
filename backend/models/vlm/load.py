#!/usr/bin/env python3
"""Load Qwen2.5-VL-3B in 4-bit and caption satellite images.

Owner: P1. Phase 0/1 deliverable (plan §P1, 31 Aug - 2 Sep).

Usage:
    python models/vlm/load.py --smoke                 # one image, prove it works
    python models/vlm/load.py --bench data/demo_pairs # measure VRAM + latency

The --bench numbers are needed for the 8 September go/no-go (plan §10, risk 1:
"inference takes over 30 seconds or the model fails to load" -> drop to a 1B
model or serve precomputed captions).
"""
import argparse
import json
import tempfile
import time
from pathlib import Path

MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"

# Qwen2.5-VL needs enough visual tokens to attend to.  RSICD chips are 224x224,
# which yields ~64 visual tokens -- at that size the model frequently replies
# "I cannot see an image" instead of describing it.  Upscaling to 512 fixes it,
# and 512 is what P3's real Sentinel-2 tiles will be anyway, so this only
# affects the small RSICD chips used for captioning data.
# Qwen2.5-VL refuses small chips: at 224x224 it replies "I can't assist with
# that", and the same image upscaled to 512 captions correctly.  The vision
# pipeline is fine either way (256 patches, 64 image tokens both times), so
# this is a model behaviour, not a plumbing bug.  Measured 31 Aug on the 3060.
#
# Matters for P3: RSICD ships 224x224 and Sentinel-2 tiles are specced at 512
# (plan section P3), so real demo tiles are already above this line.  The
# upscale exists so RSICD-sized chips do not silently produce refusals.
MIN_SIDE = 512

# Qwen is chat-tuned and defaults to markdown lists with bold headers, which
# look wrong in a chat bubble and cannot be read from the back of a room
# (plan section P5).  Constrain the FORM here; the content is still the
# model's own.  This is a presentation constraint, not a factual one -- we are
# not telling it what to see.
# A terse "Describe this satellite image." makes the model refuse on low-detail
# scenes -- it answers "I can't see any image" on bare land and meadow chips.
# Naming the medium and asking for specific observables fixes both.  Measured,
# not guessed: see the prompt comparison in docs/results_phase1.md.
DEFAULT_PROMPT = (
    "This is an aerial photograph. Describe the ground surface, colours "
    "and any structures you can see."
)

# Used once if the first attempt refuses.
RETRY_PROMPT = (
    "What land cover and terrain are visible in this aerial photograph?"
)

REFUSAL_MARKERS = ("i'm sorry", "i cannot", "i can't", "no image", "not visible")


def looks_like_refusal(text: str) -> bool:
    t = text.lower()
    return any(mk in t for mk in REFUSAL_MARKERS)


def _flatten(text):
    """Strip markdown the prompt did not suppress.

    Belt and braces: the prompt usually works, but a caption that slips through
    with bullets breaks the chat layout during a live demo.
    """
    import re
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)      # bold
    text = re.sub(r"^\s*[-*\u2022]\s+", "", text, flags=re.M)  # bullets
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.M)      # numbered
    text = re.sub(r"^#+\s*", "", text, flags=re.M)        # headers
    return re.sub(r"\s*\n+\s*", " ", text).strip()


def human_gb(n_bytes):
    return f"{n_bytes / 1024**3:.2f} GB"


def load_model(model_id=MODEL_ID, four_bit=True):
    import torch
    from transformers import AutoProcessor, BitsAndBytesConfig

    try:
        from transformers import Qwen2_5_VLForConditionalGeneration as VLModel
    except ImportError:
        raise SystemExit(
            "transformers is too old for Qwen2.5-VL.\n"
            "Fix: uv pip install -U 'transformers>=4.49' accelerate qwen-vl-utils"
        )

    if not torch.cuda.is_available():
        raise SystemExit("CUDA not available. Check the driver and the torch build.")

    kwargs = {"device_map": "cuda:0", "dtype": torch.bfloat16}
    if four_bit:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )

    t0 = time.perf_counter()
    model = VLModel.from_pretrained(model_id, **kwargs)
    processor = AutoProcessor.from_pretrained(model_id)
    load_s = time.perf_counter() - t0

    model.eval()
    return model, processor, load_s


def _prepare_image(image_path):
    """Upscale chips below MIN_SIDE; see the note on MIN_SIDE above."""
    from PIL import Image

    img = Image.open(image_path).convert("RGB")
    if min(img.size) >= MIN_SIDE:
        return img
    scale = MIN_SIDE / min(img.size)
    return img.resize(
        (round(img.width * scale), round(img.height * scale)), Image.LANCZOS
    )


def caption(model, processor, image_path, prompt=DEFAULT_PROMPT,
            max_new_tokens=128, _allow_retry=True):
    import torch
    from qwen_vl_utils import process_vision_info

    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": _prepare_image(image_path)},
            {"type": "text", "text": prompt},
        ],
    }]

    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text], images=image_inputs, videos=video_inputs,
        padding=True, return_tensors="pt",
    ).to("cuda:0")

    t0 = time.perf_counter()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - t0

    trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, out)]
    answer = processor.batch_decode(
        trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0].strip()
    answer = _flatten(answer)

    n_new = int(sum(len(t) for t in trimmed))

    # One retry with a more explicit prompt.  A refusal is a prompt-format
    # failure on low-detail scenes, not a statement about the image.
    if looks_like_refusal(answer) and prompt != RETRY_PROMPT and _allow_retry:
        return caption(model, processor, image_path, RETRY_PROMPT,
                       max_new_tokens, _allow_retry=False)

    return answer, elapsed, n_new


def find_images(path):
    p = Path(path)
    if p.is_file():
        return [p]
    exts = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    return sorted(f for f in p.rglob("*") if f.suffix.lower() in exts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="caption one image and exit")
    ap.add_argument("--bench", metavar="PATH", help="caption every image under PATH")
    ap.add_argument("--image", help="specific image for --smoke")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--fp16", action="store_true", help="skip 4-bit, load in bf16")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--max-new-tokens", type=int, default=128)
    ap.add_argument("--out", default="docs/vlm_bench.json")
    args = ap.parse_args()

    import torch

    print(f"model:  {args.model}")
    print(f"mode:   {'bf16' if args.fp16 else '4-bit nf4'}")
    print(f"gpu:    {torch.cuda.get_device_name(0)}")
    print(f"total:  {human_gb(torch.cuda.get_device_properties(0).total_memory)}")
    print("loading...")

    torch.cuda.reset_peak_memory_stats()
    model, processor, load_s = load_model(args.model, four_bit=not args.fp16)
    weights_vram = torch.cuda.memory_allocated()
    print(f"loaded in {load_s:.1f}s, weights resident {human_gb(weights_vram)}\n")

    if args.smoke:
        img = args.image
        if not img:
            found = find_images("data")
            if not found:
                raise SystemExit(
                    "No image found under data/. Pass --image PATH, or wait for "
                    "P3's tiles. Any satellite JPG works for the smoke test."
                )
            img = found[0]
        print(f"image:  {img}")
        answer, elapsed, n_new = caption(
            model, processor, img, args.prompt, args.max_new_tokens
        )
        print(f"\n--- caption ({elapsed:.2f}s, {n_new} tokens) ---\n{answer}\n")
        print(f"peak VRAM: {human_gb(torch.cuda.max_memory_allocated())}")
        return

    if args.bench:
        images = find_images(args.bench)
        if not images:
            raise SystemExit(f"no images under {args.bench}")
        print(f"benchmarking {len(images)} image(s)\n")

        results, times = [], []
        for i, img in enumerate(images, 1):
            answer, elapsed, n_new = caption(
                model, processor, img, args.prompt, args.max_new_tokens
            )
            times.append(elapsed)
            results.append({
                "image": str(img), "seconds": round(elapsed, 2),
                "new_tokens": n_new, "caption": answer,
            })
            print(f"[{i}/{len(images)}] {elapsed:5.2f}s  {img.name}")
            print(f"          {answer[:100]}{'...' if len(answer) > 100 else ''}")

        times.sort()
        peak = torch.cuda.max_memory_allocated()
        summary = {
            "model": args.model,
            "quantisation": "bf16" if args.fp16 else "4bit-nf4",
            "gpu": torch.cuda.get_device_name(0),
            "load_seconds": round(load_s, 1),
            "weights_vram_gb": round(weights_vram / 1024**3, 2),
            "peak_vram_gb": round(peak / 1024**3, 2),
            "n_images": len(times),
            "median_seconds": round(times[len(times) // 2], 2),
            "max_seconds": round(times[-1], 2),
            "results": results,
        }

        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2))

        print(f"\n{'='*54}")
        print(f"median {summary['median_seconds']}s   max {summary['max_seconds']}s"
              f"   peak VRAM {summary['peak_vram_gb']} GB")
        # Plan §10: >30s per inference triggers the fallback decision on 8 Sep.
        verdict = "PASS" if summary["max_seconds"] < 30 else "FAIL - trigger risk-1 fallback"
        print(f"30s budget (plan risk 1): {verdict}")
        print(f"written to {args.out}")


if __name__ == "__main__":
    main()
