# Test cases

**OWNER:** P6
**STATUS:** placeholder created by P1 on 31 Aug. P6 owns this file.

Every intent tested, with the exact query that caused each failure. This log is
what tells P1 and P2 what to fix and in what order.

## Start here

P1 has asked for 50 queries written **blind** — before seeing the routing rules.
Full request in docs/test_query_request.md. Roughly 10 per intent plus 10
deliberately out of scope.

That blind set is the accuracy number for the deck. P1's own 34 passing tests
prove the router does what P1 intended; they prove nothing about queries P1
did not imagine.

## Suggested log format

| # | Query | Images | Expected | Got | Pass | Notes |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

Try queries against the router directly:

```bash
python backend/router/demo.py --images 2
```

It prints the intent, the confidence, and *why* it decided — which usually tells
you whether a failure is a missing keyword or a genuine design gap.
