# Environment setup — measured, not guessed

**Owner:** P1. Written 31 August 2026 from the actual install on the 3060 box.
**Audience:** P3 especially, who packages this for the RTX 5050 on 6–8 September.

---

## Fedora 44 gotcha, hit on day one

Fedora 44 ships **Python 3.14**. PyTorch does not support it. Do not try to
`pip install torch` against the system interpreter — it will fail or resolve to
something unusable.

Fix, no root and no touching the system Python:

```bash
uv venv --python 3.12 .venv
VIRTUAL_ENV=.venv uv pip install torch torchvision --torch-backend=cu126
VIRTUAL_ENV=.venv uv pip install -r requirements.txt
```

`uv` downloads its own CPython 3.12. There is no `nvcc` on this machine and none
is needed — the wheels bundle their CUDA runtime. The NVIDIA driver is what
matters (610.57.04 here, CUDA 13.3 UMD, backwards compatible with cu126 wheels).

---

## Numbers P3 needs before packaging

Measured on the 3060 box, 31 August:

| Item | Measured |
|---|---|
| `~/.cache/uv` after torch + CUDA deps | **~24 GB** |
| Download rate on this connection | ~4 MB/s |
| Wall-clock for the torch install | **~1.5–2 hours** |
| Qwen2.5-VL-3B weights (`.hf/`) | **~7.4 GB** |
| Download rate observed | 1–4 MB/s, and it stalled twice |
| `.venv` once linked | ~8–10 GB expected |

**Two implications for the 5050:**

1. **Disk.** Budget ~35 GB for the environment alone, before model weights and
   before any data. Check free space on that laptop now, not on 6 September.
2. **Time.** If the 5050 is on the same connection, this is a two-hour job. Start
   it in the background on day one and do other work — do not schedule it as a
   task on the morning of the 8th.

## Transfer by SSD, not by network — this is the primary path

P1 has a second SSD. **Use it.** Both caches copy cleanly between machines, and
copying them is faster and far more reliable than re-downloading.

Use the script, which checks space and verifies the copy:

```bash
# on P1's 3060 box, SSD mounted at /run/media/shivam/SDCARD (234 GB ext4, ext4 matters)
./data/scripts/sync_caches.sh export /run/media/shivam/SDCARD/satquery-caches

# on P3's 5050
./data/scripts/sync_caches.sh import /run/media/shivam/SDCARD/satquery-caches
```

**The drive must be ext4, exFAT, or NTFS — not FAT32.** The HuggingFace cache is
a tree of symlinks from `snapshots/` into `blobs/`; a filesystem without symlink
support silently flattens or drops them and the model fails to load on the other
machine. `rsync -a` preserves them, `cp -r` may not.

Then the 5050 install resolves entirely from cache: no 24 GB torch download, no
7 GB model download, no dependency on the venue's network at all.

**Why this matters more than convenience.** On 31 August the model download
failed twice on this connection. Once from a timeout, and once by stalling
silently — zero bytes for minutes, process alive, no error, no connection. A
silent hang is the worst failure mode there is, because it is indistinguishable
from slow progress until you measure the byte count yourself. Discovering that
on the evening of 10 September is exactly the scenario plan section P3 warns
about.

The SSD removes the network from the critical path completely.

---

## Offline requirement

Plan §P3: the stack must run on the 5050 **with networking switched off**.

HuggingFace models download on first use, so a fresh machine will try to reach
the network mid-demo unless the cache is pre-warmed. Pre-warm it, then lock it:

If the cache came from the SSD, this step is already done — just verify by
running with networking off. Otherwise, pre-warm it:

```bash
# once, with network, on the 5050
export HF_HOME=/path/to/project/.hf
.venv/bin/python -c "
from transformers import AutoProcessor
from transformers import Qwen2_5_VLForConditionalGeneration as M
M.from_pretrained('Qwen/Qwen2.5-VL-3B-Instruct')
AutoProcessor.from_pretrained('Qwen/Qwen2.5-VL-3B-Instruct')
"

# then for the demo, force offline
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

**Test the offline path by actually turning off the wifi**, not by assuming. §P3
says "watch it run, do not accept a promise that something will run" — that
applies here more than anywhere, because a network call on stage looks like a
hang.

---

## Verify the install

```bash
.venv/bin/python -c "
import torch
print('torch', torch.__version__)
print('cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0))
print('vram', torch.cuda.get_device_properties(0).total_memory // 1024**3, 'GB')
"
```

Expected: 3060 → 12 GB, 5050 → 8 GB.

**The 5050 has less VRAM than the training box.** Qwen2.5-VL-3B in 4-bit should
fit in ~3 GB, so there is headroom — but that is a prediction until someone
measures it on the actual laptop. `models/vlm/load.py --bench` prints peak VRAM
and per-image latency; run it there on 6 September and compare against the 30 s
budget in plan §10 risk 1.
