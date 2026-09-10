#!/usr/bin/env python3
"""Interactive router demo.  Owner: P1.

Shows the routing decision and the reason for it, live.  Being able to show
WHY a query routed where it did is worth more than a slide claiming the
router works (docs/router_design.md).

Usage:
    python backend/router/demo.py               # interactive
    python backend/router/demo.py --images 1    # simulate a single image
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from router.intent import route  # noqa: E402

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
GREEN, YELLOW, CYAN = "\033[32m", "\033[33m", "\033[36m"


def show(query: str, n_images: int) -> None:
    d = route(query, n_images)
    colour = YELLOW if d.intent == "unclear" else GREEN
    print(f"  {BOLD}{colour}{d.intent}{RESET}  confidence {d.confidence}")
    if d.tool:
        print(f"  {DIM}tool:{RESET}   {CYAN}{d.tool}{RESET}")
    print(f"  {DIM}reason:{RESET} {d.reason}")
    if d.clarification:
        print(f"  {DIM}asks:{RESET}   {d.clarification}")
    if d.scores:
        ranked = sorted(d.scores.items(), key=lambda kv: -kv[1])
        bars = "  ".join(
            f"{k}={v:.2f}" for k, v in ranked if v > 0
        ) or "no rules fired"
        print(f"  {DIM}scores:{RESET} {bars}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=int, default=2,
                    help="how many images the user supplied")
    ap.add_argument("query", nargs="*")
    args = ap.parse_args()

    if args.query:
        q = " ".join(args.query)
        print(f"\n{BOLD}{q}{RESET}  {DIM}({args.images} image(s)){RESET}")
        show(q, args.images)
        return

    print(f"{BOLD}SatQuery AI — query router{RESET}")
    print(f"{DIM}Simulating {args.images} uploaded image(s). "
          f"Ctrl-D or 'quit' to exit.{RESET}\n")
    while True:
        try:
            q = input(f"{BOLD}query>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if q.lower() in {"quit", "exit", "q"}:
            return
        if not q:
            continue
        show(q, args.images)
        print()


if __name__ == "__main__":
    main()
