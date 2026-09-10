# Team channel — 31 August

Paste-ready. One message per person, plus one for the channel.

---

## To the channel

> Repo is up with the folder structure from §4 of the plan. Every folder has one
> owner — please don't edit someone else's without saying so first.
>
> Four documents in `docs/` that need a response today or tomorrow:
>
> - `api_contract_request.md` — P4
> - `instruction_format.md` — P3
> - `test_query_request.md` — P6
> - `router_design.md`, `fusion_design.md` — FYI, that's what I'm building
>
> Two things from the plan I want to flag now:
>
> **1. P2 and I are not blocked by anything.** §11 says "nothing else starts
> until the mock endpoint exists." That's true for P5, not for us. LEVIR-CD and
> the base model both download today. Start now.
>
> **2. Interface freeze is 2 September.** After that, changing a response field
> breaks me and P5 at the same time. If you want something changed, say so in
> the next 48 hours.
>
> Standup daily, 15 minutes, voice. Four-hour rule is live from today: blocked
> more than four hours, switch to your backup task and post here saying what
> blocked you.

---

## To P4 — needs an answer today

> Two questions before either of us writes code:
>
> **1. `backend/router/intent.py` is in your folder but I own it. Direct Python
> import, or HTTP call?** My proposal is a direct import — the router is pure
> text processing, no model of its own, so an HTTP hop only adds latency and one
> more thing that can fail on stage. Happy to build it either way, but I need to
> know today.
>
> **2. Full response shape is in `docs/api_contract_request.md`.** Please read
> and push back on anything awkward to produce. The one part I care most about:
> `computed` and `answer` stay separate fields. That separation is the project's
> whole differentiator from GeoChat, and I want to show it on screen.
>
> One addition beyond the plan: an `unclear` intent. When the router isn't
> confident it asks a clarifying question instead of guessing. Please render it
> as a normal answer, not an error.

---

## To P3 — format spec, before you generate 2000 of anything

> `docs/instruction_format.md` has the JSONL schema for the instruction pairs,
> plus `data/scripts/validate_instructions.py` which checks every rule in it,
> including that image paths actually resolve.
>
> Process, per §P3 of the plan: generate **20** records, run the validator, send
> them. I confirm same day. Then you generate the full 2000.
>
> Three things people usually get wrong, all of which cost a regeneration:
>
> - **Rotate the question phrasing.** At least 10 templates, roughly even. If
>   all 2000 say "Describe this satellite image," the fine-tune learns one
>   phrasing and is useless for anything else.
> - **One caption per image, not five.** RSICD gives five per image. Using all
>   five turns 2000 records into 400 images of real signal and teaches
>   memorisation.
> - **Hold out ~10% as `val`.** Without it I can't prove the adapter beat the
>   base model, and that's a slide.
>
> Separately: any real satellite image you already have, send it today. I'm
> smoke-testing on synthetic imagery right now, which proves the pipeline runs
> but proves nothing about model quality. The 2 September go/no-go needs real
> Sentinel-2 data.

---

## To P6 — 50 test queries, and please don't look at my rules first

> Ask is in `docs/test_query_request.md`. 50 questions someone might type at
> this system, one per line, by 3 September.
>
> **The one rule: write them before you see my routing rules, and don't ask me
> what phrasings I handle.** If I write my own tests I'll unconsciously write
> the ones that already pass, and the number becomes meaningless. Queries
> written blind are the only honest measure we can put on a slide.
>
> Roughly 10 per intent, **plus 10 that are deliberately out of scope** —
> predictions, sensors we don't support, anything from the §9 out-of-scope list.
> The router is supposed to say "I can't answer that." I need to test that path
> and it's worth a slide of its own.
>
> Send the intent labels you'd expect in a *separate* file and keep it until
> I've run mine. Where we disagree is a real finding about the design, not a
> mistake by either of us.
>
> This is your 3–5 September task from the plan, just moved earlier and made
> stricter. Output feeds straight into `docs/test_cases.md`.

---

## To P2 — one line

> You have zero upstream dependencies, same as me. LEVIR-CD downloads today.
> §P2 of the plan is right that week one is where to push hardest — nothing is
> waiting on you yet, and on 6 September everything is.
