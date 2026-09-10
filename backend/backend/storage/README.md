# Storage

**OWNER:** P4

Two artefacts live here, both gitignored because they are binaries:

| File | What |
|---|---|
| `metadata.db` | SQLite: image date, sensor, bounding box, resolution per tile |
| `index.faiss` | Optional retrieval index |

`metadata.db` is created by P4's code on first run. Document the schema here
when it exists — plan section P4 lists "a documented schema" as a deliverable.

Resolution matters beyond metadata: the geo service needs metres-per-pixel to
convert changed pixel counts into square kilometres, and those km² figures are
the computed numbers the fusion layer inserts into answers.
