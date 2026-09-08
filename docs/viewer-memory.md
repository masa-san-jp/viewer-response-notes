# Viewer memory

The wrapper closes nested source provenance to origin_instance_id, record_id,
revision, source_repository, code_commit, knowledge_commit, locator and
content_sha256. Locators are opaque references; response metadata is forbidden.
Lineage references use the common four-part artifact identity and must resolve
in the pinned owner history. Invalidations must match explicit native corrections.
Successful stored retrieval reports knowledge_status COMMITTED; operation or
parent collisions report CONFLICT. Assessment status remains a separate axis.

AAK-12 / Issue #6 implements the pinned AAK-SPEC/PLAN
`b0e7c7f8d0a1f756fa708deef4fb380a62e45e0d`. Existing record, assessment and export
v1 contracts and Wilson thresholds remain unchanged.

A memory candidate has `artifact` (the common artifact-record/v1 envelope) and
`payload`. The payload contains one native aggregate `record` and a closed
`context`: project, work revision, intended experience references, collection
method/period, presentation condition reference, source identity, sample-set
identities, declared overlapping sets, and corrected record IDs. Context fields
are opaque identifiers, enumerations and timestamps; names and free responses
are not permitted. Unexpected reception remains a native requirement/tag-scoped
aggregate or opaque external evidence, never a new free-text category.

`config/viewer-memory.json` and `schemas/viewer-memory.schema.json` define this
addition. The artifact kind is viewer-response and payload_schema viewer-memory/v1.
The artifact creator/collection must match the explicitly bound owner store.
Native source_commit remains source provenance; the artifact producer code_commit
identifies the executing code. No one adopts another creator implicitly.

An explicitly initialized AAK-04 owner store contains `store.json` and bare
`objects.git`, with `refs/heads/knowledge`. It may have no remote. Execute from a
clean pinned code checkout, specifying the independent knowledge commit. The
owner stores metadata in `records/memory`, payloads in `records/payloads`, and an
operation ledger in `records/operations`. Path keys are SHA-256 of canonical JSON
`[origin_instance_id, owner_repository, record_id, revision]`; payload hashes use
sorted UTF-8 JSON with separators `,` and `:`.

```bash
python3 tools/viewer_memory.py append \
  --store-root "$MEMORY_ROOT" --creator "$CREATOR" --collection "$COLLECTION" \
  --code-commit "$CODE_COMMIT" --knowledge-commit "$KNOWLEDGE_COMMIT" \
  --candidate "$CANDIDATE" --operation-id "$OPERATION" --run-id "$RUN"
python3 tools/viewer_memory.py query \
  --store-root "$MEMORY_ROOT" --creator "$CREATOR" --collection "$COLLECTION" \
  --code-commit "$CODE_COMMIT" --knowledge-commit "$COMMITTED_KNOWLEDGE_COMMIT" \
  --scope "$SCOPE" --at "$NOW"
python3 tools/export_signals.py --memory-query "$MEMORY_QUERY" --output "$NEW_OUTPUT"
```

`--scope` is a JSON object with exactly config.scope_fields. Every collection
dimension is compared exactly; tags must intersect. Different exhibition
conditions, work revisions, collection periods or methods are not pooled.
`--memory-query` is an external JSON object with exactly store_root, creator,
collection, code_commit, knowledge_commit, scope and at. Export preserves source
commits in separate native envelopes and returns the scoped native assessment.
It is a local create-only artifact, not an external transmission. Regeneration
reads the pinned Git records each time; no cache is authoritative.

Intake rejects duplicate sources, identical or explicitly overlapping sample
sets, source/record replay with changed content, stale parents, wrong creators,
fabricated external counts and privacy violations. Exact operation replay returns
the original receipt. Zero measured samples produce NO_NEW_EVIDENCE without a new
Git record; empty retrieval returns an UNKNOWN assessment. These statuses do not
prevent starting a production plan and are not negative viewer judgments.

Correction is append-only: use a new native record_id and new provenance,
context.corrects_record_ids, and exact artifact invalidates references. An
explicit `--correction-approval-ref` is also required by the existing human gate.
The implementation tests use an explicitly named synthetic fixture approval;
that is not approval for real corrections. Original bytes and old assessments
remain reproducible at old commits. Active query excludes corrected records and
recalculates using the unchanged native assessment function. Expired artifact
validity returns the affected record IDs for revalidation.

Output creation uses atomic no-overwrite publication. Identical replay is
ALREADY_EXPORTED; a competing different file is a conflict. Successful Git
receipts are retained when output creation fails; retry query/export from the
same knowledge commit to a new permitted output path.

Acceptance uses temporary synthetic owner stores only. No real viewer records,
Masa profile, external publication, or AAK-02 live agent integration is implied.
