# viewer-response-notes

Private, append-only source of truth for privacy-safe viewer response records
and conservative production-requirement assessments.

The repository stores measured responses as aggregate counts and external
evidence as opaque references. It never stores free-form answers, names,
contact details, psychological or medical diagnoses, or raw assets.

## Contracts

- `schemas/viewer-memory.schema.json`: `viewer-memory/v1`, the AAK-12 condition/lineage wrapper around the existing record. See [viewer memory](docs/viewer-memory.md) for owner Git, corrections and scoped retrieval.

- `schemas/viewer-response-record.schema.json`: `viewer-response-record/v1`
- `schemas/viewer-response-assessment.schema.json`: `viewer-response-assessment/v1`
- `schemas/research-signal-export.schema.json`: `research-signal-export/v1`

The record validator enforces the aggregate-only boundary, source commit and
evidence provenance, deterministic deduplication, and append-only uniqueness.
The assessment uses a two-sided Wilson 95% interval: fewer than five measured
observations is `UNKNOWN`; otherwise lower bound `>= 0.60` is `SUPPORTED`, upper
bound `< 0.60` is `CONTRADICTED`, and the remaining cases are `UNKNOWN`.
With no measured sample, two independent external evidence references produce
`EXTERNALLY_SUPPORTED`, which is intentionally not `SUPPORTED`.

## Local commands

```bash
python3 tools/validate.py --check
python3 -m unittest discover -s tests -v
python3 tools/export_signals.py tests/fixtures/viewer-response-records.jsonl --export-id VRSE-fixture --source-commit 0123456789abcdef0123456789abcdef01234567 --output /tmp/viewer-response-export.json
```

Export is deterministic and atomic. Re-running with identical bytes returns
`ALREADY_EXPORTED`; a different existing file returns
`VIEWER-EXPORT-CONFLICT` without overwriting it.

