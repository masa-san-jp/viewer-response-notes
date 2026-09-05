# AAK-12 checkpoint

Issue #6, branch agent/aak-12-viewer-memory, base 78b6e9a87831eca5a5c20993374b61b8cc61bd0d.
AAK-SPEC/PLAN pin b0e7c7f8d0a1f756fa708deef4fb380a62e45e0d. Dependency AAK-04 qualified candidate 83f7e9e8d1c6e25b39351aebb6eb15cb12da4685 / instance-profile/v1 / orchestration PR201 has synthetic 14 focused and 580 full tests (one existing skip) PASS. Candidate is unmerged.

Selected scope: associate native aggregate-only records with opaque creator/project/work revision, collection period, presentation conditions and sample-set identities; append corrections; rebuild scoped assessments and exports; return NO_NEW_EVIDENCE/UNKNOWN without fabricating counts. Existing Wilson thresholds remain unchanged. Explicit synthetic temporary stores are the only data used in acceptance tests. Existing records/assessments/exports are preserved.

Status: CODE_VALIDATED; draft PR submission follows. AAK-12-AC1..5 PASS with synthetic aggregate inputs. No merge, release, public export or real record correction was performed. Live cross-owner integration remains NOT_RUN (AAK-02).

Qualified local code: `2359ac4eba64c4eaa2a8c231e39d06ef4bbf6231`; remote candidate: `ca2fbe2cb66ed771486e60159431a670721be3e7`. Both have exact tree `082dd546cefa93b2f7a2a5063810edd344facf73`; every uploaded blob hash was verified. Code and knowledge refs are distinct.

Acceptance evidence (`tests/test_viewer_memory.py`):

- AC1 PASS: same work, two presentation conditions, separate 20-person aggregates produce SUPPORTED and CONTRADICTED; Git reopen and native export CLI preserve the scoped result.
- AC2 PASS: duplicate source, shared/overlapping sample, external fabricated counts and wrong creator reject.
- AC3 PASS: missing correction approval rejects; synthetic approval appends a new ID, keeps original bytes and recalculates only the active correction. Dangling/self references reject.
- AC4 PASS: free response/name/raw fields, extra source metadata, secret/private references reject. Nested metadata contracts are closed.
- AC5 PASS: absent and zero-sized measured evidence produce NO_NEW_EVIDENCE / UNKNOWN; no knowledge commit is fabricated.
- Operation replay, stale parent and concurrent export writer checks PASS; create-only export preserves the competing artifact.

Required verification: `python3 -m unittest discover -s tests -v`: 19 PASS, 0.576s. Log SHA-256 `2ada871a3bdeea453c4f94279ec0a86e7f024332cd4775e675f57c04efe3f0ed`. `python3 tools/validate.py --check`: PASS. `git diff --check`: PASS. README export example ran at a fresh temporary path, returning EXPORTED then ALREADY_EXPORTED.

Retained synthetic proof uses the checked-in aggregate fixture with explicitly synthetic IDs: operation `one`, run `synthetic`, owner `viewer-response-notes`, collection `viewer-a`, schema/policy `viewer-memory/v1`. Receipt `knowledge-write-receipt/v1`: target_parent `a0b1bddffce23a23ddcadd81896a0d5959ccef0c`, target_commit `df0c1156b097ac08440dfef9c7d930b2a34d47f3`, accepted_ids `[VRR-A]`, rejected_ids `[]`, status COMMITTED; index_commit/index_hash null (assessment/export rebuilt on query). The reopened query returns knowledge_status COMMITTED and assessment SUPPORTED. Store: `/workspace/scratch/bf03ca10c92e/aak-12-evidence/synthetic-memory`; full temporary proof: `/tmp/aak-12-proof.json`. These are synthetic local artifacts, not published viewer data or real production acceptance.

Resume: inspect draft PR and candidate against Issue #6, preserving the default branch `feat/viewer-response-contracts`; final real-owner integration belongs to AAK-02. No user feedback, inferred preference or real respondent data was stored.
