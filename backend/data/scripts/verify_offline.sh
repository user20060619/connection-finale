#!/usr/bin/env bash
# Prove the stack runs with no network.  Owner: P1, for P3's 6-8 Sep offline test.
#
#   ./data/scripts/verify_offline.sh
#
# Plan section P3: "Whole system runs on the laptop with networking switched
# off."  This script forces the offline flags so a missing cache entry fails
# loudly here instead of hanging on stage.

set -uo pipefail
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT"

export HF_HOME="$PROJECT/.hf"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

pass=0; fail=0
check() {
  local name="$1"; shift
  printf '%-34s' "$name"
  if out=$("$@" 2>&1); then echo "ok"; pass=$((pass+1))
  else echo "FAIL"; echo "$out" | tail -5 | sed 's/^/    /'; fail=$((fail+1)); fi
}

echo "Offline verification"
echo "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1"
echo

check "router rules load"      .venv/bin/python backend/router/intent.py "what changed"
check "router test suite"      .venv/bin/python backend/router/test_router.py
check "fusion templates"       .venv/bin/python backend/fusion/explain.py
check "pipeline end to end"    .venv/bin/python backend/pipeline.py "has vegetation decreased"
check "pipeline contract tests" .venv/bin/python backend/test_pipeline.py
check "VLM loads from cache"   .venv/bin/python models/vlm/load.py --smoke \
                                 --image data/raw/rsicd_sample/park_62.jpg

echo
echo "passed $pass, failed $fail"
if [ "$fail" -gt 0 ]; then
  echo
  echo "A failure here with networking ON but flags SET means the cache is"
  echo "incomplete -- pre-warm it, or copy it from P1's SSD:"
  echo "  ./data/scripts/sync_caches.sh import /run/media/shivam/SDCARD/satquery-caches"
  exit 1
fi
echo "Now repeat with the wifi physically off. Watch it run."
