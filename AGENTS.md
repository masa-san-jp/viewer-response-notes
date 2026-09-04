# Repository instructions

## Mission

`viewer-response-notes` is the source-of-truth repository for aggregate viewer
response records and conservative requirement assessments. It stores no raw
answers, names, contact details, psychological or medical inferences, raw
assets, or credentials.

## Authority and read order

Use repository-local evidence so a fresh agent does not depend on conversation
history. Read these sources in order:

1. GitHub Issue #2 and the one task Issue selected for this run.
2. The closest files in `schemas/` and their implementation in `tools/`.
3. `README.md`, including its contracts and local checks.
4. The closest files in `tests/` and their fixtures.
5. The current git status and diff, to confirm the starting commit and scope.

Issue acceptance and the versioned schemas are the domain authority. The
README and tests make the contract usable and observable; this file defines
the execution procedure and safety boundaries and must not weaken those
contracts.

## Task selection and work protocol

- Work on exactly one Issue/task at a time. If a task is supplied, use that
  Issue as the scope. Otherwise select the smallest open Issue for this
  repository whose acceptance is actionable; do not invent unrelated scope.
- Record the starting commit and target Issue before editing. If no actionable
  Issue exists, report that fact instead of making speculative changes.
- Use this sequence: `inspect -> decide -> edit -> test -> diff -> report`.
  Decide the smallest allowed change and its acceptance evidence before
  editing. Keep one task to one branch, commit, and draft PR when those actions
  are authorized.
- A dirty worktree, detached HEAD, unexpected branch, missing source commit,
  or unreviewed change in an overlapping path must not be silently changed.
  Preserve it and stop with the observed state.
- An agent may create a branch, commit, and PR when the task authorizes it.
  Record correction, export, external write, merge, and release remain
  policy-controlled human gates.

## Allowed writes and generated data

- Documentation and contract work may change `AGENTS.md`, `README.md`,
  `schemas/`, `tools/`, `tests/`, and `tests/fixtures/` only when the selected
  Issue explicitly includes those paths.
- `records/`, `assessments/`, and `exports/` are checked-in contract data and
  generated outputs, not scratch space. Generate them with the repository
  tools; do not hand-edit generated files.
- Records are append-only: a correction creates a new `record_id` with new
  provenance. Never rewrite, reorder, or delete an existing record.
- Assessments and exports are create-only artifacts. Write only to a new,
  explicitly selected output path; never overwrite or delete an existing
  artifact. Keep source commit, evidence references, consent scope, and any
  external artifact identifier/hash/provenance explicit and opaque.
- Do not add a top-level directory, modify `.git`, or write outside the
  repository except for an explicitly requested temporary test output.

## Privacy and external-side-effect boundary

- Preserve the aggregate-only boundary. `measured` records contain counts;
  `external` records contain opaque evidence references and no fabricated
  sample or outcome counts.
- Reject names, contact details, PII, free text, psychological or medical
  inferences, raw assets, private URLs, absolute paths, `PRIVATE_RAW`,
  `RESTRICTED`, secrets, credentials, and credential-bearing URLs.
- Do not send records or inferred feedback to GitHub, Drive, an API, another
  repository, or any other external destination from repository tools.
  External evidence may be referenced only by an allowed opaque reference.
- Keep explicit feedback distinct from inferred feedback. An aggregate or an
  assessment is not a user fact, consent expansion, acceptance, or permission
  to publish.

## Required checks

Run all declared checks from the repository root and preserve their observed
result:

```bash
python3 tools/validate.py --check
python3 -m unittest discover -s tests -v
git diff --check
```

When changing export, assessment, record, schema, or tool behavior, also run
the relevant README example with a fresh temporary output path. Never use an
existing artifact as a disposable output. A failed check is not a pass: do not
skip, delete, weaken, or reinterpret a failing check as completion.

## Stop conditions

Stop and report `BLOCKED` with the observed fact, options, recommendation,
impact, and解除条件 when any of these occurs:

- Issue acceptance, schema authority, provenance, or consent scope is
  ambiguous or contradictory and a conservative adapter cannot resolve it.
- A required check fails, the expected fixture is missing, or the changed
  behavior cannot be demonstrated by a regression test.
- The requested change needs raw response content, free text, PII, private
  data, `PRIVATE_RAW`, `RESTRICTED`, secrets, credentials, a consent expansion,
  or a public-scope change.
- The change would rewrite/delete existing records or artifacts, send data to
  an external service, require new credentials/permissions, merge, release,
  or perform another irreversible side effect.
- The worktree or branch state is dirty or unexpected in a way that cannot be
  isolated safely.

Do not leave only a question. Include the evidence and the exact human or
repository change needed to unblock the task.

## Completion report

Mark a task complete only when every acceptance item and every required check
has an observed passing result. The completion report is metadata-only and
must contain:

- task/Issue ID, target repository, starting/source commit, and changed paths;
- acceptance achieved count and evidence for each required check;
- repository commit/PR metadata and, if applicable, external artifact ID,
  hash, provenance, and access scope (opaque references only);
- explicit feedback versus inferred feedback, without storing conversation
  text or raw responses;
- sensitive-information/privacy review, unresolved items, and the next task
  with its first operation.

If any acceptance item or check is missing, report `BLOCKED` or `INCOMPLETE`
with the failing evidence; never claim completion from file presence alone.
