# Repository instructions

## Mission

`viewer-response-notes` is the source-of-truth repository for aggregate viewer
response records and conservative requirement assessments. It stores no raw
answers, names, contact details, psychological or medical inferences, or
credentials.

## Work rules

- Keep records append-only. A correction is a new record with a new `record_id`
  and provenance; do not rewrite an existing record in place.
- Keep all identifiers, source commits, evidence references, and consent scope
  explicit. Never infer a user fact from a response aggregate.
- `measured` records contain aggregate counts only. `external` records contain
  no fabricated sample or outcome count.
- Export is local and create-only. Never send records to GitHub, Drive, an API,
  or another repository from this repository's tools.
- Reject unknown fields, free text, PII, private URLs, absolute paths,
  `PRIVATE_RAW`, `RESTRICTED`, secrets, and credentials before writing output.
- Assessments are estimates, not acceptance. `UNKNOWN`, `CONTRADICTED`, and
  `EXTERNALLY_SUPPORTED` require a blind/frame review test in the production
  plan.

## Required checks

```bash
python3 tools/validate.py --check
python3 -m unittest discover -s tests -v
```

