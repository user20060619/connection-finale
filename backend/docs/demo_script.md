# Demo script

**OWNER:** P6
**STATUS:** placeholder created by P1 on 31 Aug. P6 owns this file.

The exact sequence of queries to run on stage, in order, with the expected
answer for each. The team rehearses against this rather than improvising.

## Suggested spine (P6 decides the final order)

| # | Query | Images | Expected | Why it is in the demo |
|---|---|---|---|---|
| 1 | What is visible in this image? | 1 | Caption | Shows the VLM path |
| 2 | Has vegetation decreased here? | 2 | % + mask | **The core claim.** Number is computed, not generated |
| 3 | What changed between these? | 2 | Mask + km² | Siamese U-Net |
| 4 | Where are the buildings? | 1 | Boxes + count | Detection |
| 5 | What will this look like in 2030? | 2 | *"I can't predict"* | **Abstention.** Shows the system knows its limits |
| 6 | What changed here? | **1** | *"needs two images"* | Asks for what is missing instead of guessing |

Queries 5 and 6 matter as much as 1–4. Most demos answer everything
confidently; a system that declines is more trustworthy, and it is the honest
face of the out-of-scope list in section 9.

Working today, try them:

```bash
python backend/pipeline.py
python backend/router/demo.py --images 2
```
