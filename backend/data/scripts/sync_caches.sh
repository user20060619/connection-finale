#!/usr/bin/env bash
# Move the heavy caches between machines by SSD instead of re-downloading.
# Owner: P1.  Written for P3's 5050 packaging (plan section P3, 6-8 Sep).
#
#   ./data/scripts/sync_caches.sh export /run/media/shivam/SDCARD/satquery-caches
#   ./data/scripts/sync_caches.sh import /run/media/shivam/SDCARD/satquery-caches
#
# Why: on 31 Aug the model download failed twice on this connection, once by
# stalling silently.  The SSD takes the network off the critical path.

set -euo pipefail

MODE="${1:-}"
DEST="${2:-}"
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UV_CACHE="${HOME}/.cache/uv"
HF_CACHE="${PROJECT}/.hf"

usage() { echo "usage: $0 {export|import} /path/on/ssd"; exit 2; }
[ -z "$MODE" ] || [ -z "$DEST" ] && usage
[ "$MODE" = "export" ] || [ "$MODE" = "import" ] || usage

# A filesystem without symlinks corrupts the HF cache silently.
check_symlinks() {
  local dir="$1"
  mkdir -p "$dir"
  if ! ln -sf /tmp "$dir/.symlink_probe" 2>/dev/null || [ ! -L "$dir/.symlink_probe" ]; then
    echo "ERROR: $dir does not support symlinks (FAT32?)."
    echo "The HuggingFace cache is symlinks from snapshots/ into blobs/."
    echo "Reformat as ext4/exFAT/NTFS, or the model will not load on the target."
    rm -f "$dir/.symlink_probe" 2>/dev/null || true
    exit 1
  fi
  rm -f "$dir/.symlink_probe"
}

human() { du -sh "$1" 2>/dev/null | cut -f1; }

# Guard: this SSD holds P1's other projects. Refuse to write to a mount root,
# so a mistyped path can never scatter cache dirs among existing folders.
if findmnt -no TARGET "$DEST" 2>/dev/null | grep -qx "$DEST"; then
  echo "ERROR: $DEST is a mount point, not a subdirectory."
  echo "Pass a dedicated folder, e.g. $DEST/satquery-caches"
  exit 1
fi

if [ "$MODE" = "export" ]; then
  check_symlinks "$DEST"
  # Show what already exists alongside, then confirm before writing.
  parent="$(dirname "$DEST")"
  if [ -d "$parent" ]; then
    echo "Writing into: $DEST"
    echo "Existing items in $parent (these are NOT touched):"
    ls -1 "$parent" 2>/dev/null | grep -v '^lost+found$' | sed 's/^/  /'
    echo
    read -rp "Proceed? [y/N] " ok
    [ "$ok" = "y" ] || [ "$ok" = "Y" ] || { echo "aborted"; exit 0; }
  fi
  need=0
  for c in "$UV_CACHE" "$HF_CACHE"; do
    [ -d "$c" ] && need=$(( need + $(du -sb "$c" | cut -f1) ))
  done
  avail=$(( $(df -B1 --output=avail "$DEST" | tail -1) ))
  echo "need  $(( need / 1073741824 )) GB"
  echo "avail $(( avail / 1073741824 )) GB on $DEST"
  [ "$avail" -lt "$need" ] && { echo "ERROR: not enough space"; exit 1; }

  for pair in "uv-cache:$UV_CACHE" "hf-cache:$HF_CACHE"; do
    name="${pair%%:*}"; src="${pair#*:}"
    [ -d "$src" ] || { echo "skip $name (not present)"; continue; }
    echo; echo "==> $name  ($(human "$src"))"
    rsync -a --info=progress2 --no-inc-recursive "$src/" "$DEST/$name/"
  done
  echo; echo "Done. Eject cleanly:  udisksctl unmount -b /dev/sda1"

else
  [ -d "$DEST" ] || { echo "ERROR: $DEST not found. Is the SSD mounted?"; exit 1; }
  for pair in "uv-cache:$UV_CACHE" "hf-cache:$HF_CACHE"; do
    name="${pair%%:*}"; dst="${pair#*:}"
    [ -d "$DEST/$name" ] || { echo "skip $name (not on SSD)"; continue; }
    echo; echo "==> $name -> $dst"
    mkdir -p "$dst"
    rsync -a --info=progress2 --no-inc-recursive "$DEST/$name/" "$dst/"
  done
  echo
  echo "Now verify WITH NETWORKING OFF:"
  echo "  export HF_HOME=$HF_CACHE HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1"
  echo "  .venv/bin/python models/vlm/load.py --smoke --image data/raw/rsicd_sample/park_62.jpg"
  echo
  echo "Plan section P3: watch it run. Do not accept a promise that it works."
fi
