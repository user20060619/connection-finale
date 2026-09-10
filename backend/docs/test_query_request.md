# Request: 50 blind test queries

**From:** P1 (router)
**To:** P6 (documentation and QA)
**Date:** 31 August 2026
**Needed by:** 3 September, morning

## What I am asking for

50 questions a user might type at this system, written by you, in a plain text
file, one per line. Send to `docs/test_queries.txt`.

## The one rule that makes this worth doing

**Write them before you see my routing rules, and do not ask me what phrasings
the router handles.**

I build the router on 3–5 September. If I write my own test queries, I will
unconsciously write the ones my rules already catch, and "20/20 queries routed
correctly" becomes a statement about my imagination rather than about the
system. Queries written blind by someone else are the only honest measure I can
put on a slide.

If the router scores badly on your set, that is the test working. I would much
rather find out on 4 September than in the question round on the 11th.

## What to include

Aim for roughly this spread across the four supported intents:

| Intent | Roughly | Example of the kind of thing |
|---|---|---|
| Describe | 10 | "What is visible in this image?" |
| Vegetation | 10 | "Has the forest cover dropped?" |
| Change | 10 | "What is different between these two?" |
| Locate | 10 | "Where are the buildings?" |
| Water | a few | "Did the reservoir shrink?" |
| **Out of scope** | **10** | "What will this area look like in 2030?" |

That last row is the important one. Include questions the system **should not**
be able to answer — predictions, questions about sensors we do not support,
requests for multi-turn reasoning, things listed as out of scope in §9. The
router is supposed to say "I cannot answer that" rather than guess. I need to
test that path, and it is worth a slide: a system that knows its own limits
scores better than one that confidently answers everything.

## How to write them

- **Vary the phrasing hard.** Formal, casual, terse, misspelled, ungrammatical.
  "vegetation change pls", "did the trees go away", "Quantify NDVI delta".
  A judge will not type in our house style.
- Include a few that are genuinely ambiguous between two intents. Real users
  write those, and I want to know what the router does with them.
- Do not label them. Send the questions only.

## Also send, separately

A second file, `docs/test_queries_answers.txt`, with the intent **you** think
each query should map to, in the same order. Keep it to yourself until I have
run my router against the questions — then we compare. That comparison is the
number that goes on the results slide.

Where you and I disagree about the correct intent, that is a genuine finding
about the design, not an error by either of us. Those cases are worth
discussing at standup.

## Why this is worth your time on day one

Per plan §P6 your 3–5 September task is "test the four intents, log every
failure." This is that task, moved earlier and made more rigorous. The output
feeds straight into `docs/test_cases.md`, which is one of your deliverables, and
gives you a real measured number for the results section instead of a claim.
