# Main reconciliation and portable synthetic qualification

Task: `main-reconcile-and-macos-tmp` in `viewer-response-notes`, maintaining
Issue #2 contracts and AAK-12 / Issue #6 behavior. Starting main commit:
`0c198ec38629fb032f778071e35f265286f6566f`.
Inspected default-branch tip:
`1158286151632482e5a3f910adefc229de2bea7e`.

## Content provenance and decisions

- Copy the eight-repository map from PR #10 (source
  `90c62ad5dc4153ef6166355c910ea350069cb834`) and the underlying question from
  PR #11 (source `2c1167c7ce95f0bfa3a2e9f0896bec5836009a87`) into main's README.
  Preserve main's introduction, contract descriptions, AAK-12 wrapper link and
  local commands. Main remains the intended canonical branch; changing the
  GitHub default branch belongs to the orchestrator.
- Copy the AP-04 historical verification from PR #12 (source
  `c886f6b40ff9ca3a85075e5eaa02af64cba9c22e`). Its 13-test result describes
  its qualified source only, not the AAK-12 main tree.
- Copy the additional `test_agent_instructions_are_self_contained` from the
  default-branch contract tests. It originated in PR #5's autonomous work
  contract, before AP-04, and was missing from main's test file.
- No `docs/` files exist in the inspected default-branch tree. Its AP-04
  documentation is the README section above; do not fabricate a missing report.
  Keep main's existing viewer-memory documentation and historical checkpoint.
- Do not copy the default branch's removal of AAK-12 policy, schema, tools,
  tests or documentation, or its older export CLI without memory-query support.
  Those differences conflict with main's accepted AAK-12 behavior.
- Transfer file content without merging the unrelated histories. Do not copy
  record, assessment or export artifacts.

## Portable tests and preserved boundaries

Resolve only the test fixture's temporary root before constructing store paths.
This handles macOS temporary-directory aliases without changing the product's
strict canonical external-store check. Store-root and `objects.git` symlinks
remain rejected; new regression cases also cover relative/internal stores.

The synthetic fixture copies the current tools, configuration and schemas into
a temporary Git checkout and commits it locally. Both in-process memory tests
and the real export CLI use this same code fixture and its independent code
commit. This removes reliance on the source distribution's `.git`, so archive
tests run without changing the production clean-and-pinned checkout gate.
New regression cases verify rejection of a mismatched code pin and a dirty
code fixture. Temporary owner Git stores have no remote and contain synthetic
aggregate inputs only.

## Observed verification

All three maintenance requirements are achieved: canonical macOS test paths
with symlink rejection preserved; compatible default-branch content transferred
with AAK-12 retained; and local plus archive validation passing.

| Command | Environment | Exit | Observed result |
| --- | --- | --- | --- |
| `python3 tools/validate.py --check` | Local Python 3.14.6 | 0 | Validation passed |
| `python3 -m unittest discover -s tests -v` | Local Python 3.14.6 | 0 | 21 tests, OK |
| `python tools/validate.py --check` | Requested macOS Python 3.12.13 | 0 | Validation passed |
| `python -m unittest discover -s tests -v` | Requested macOS Python 3.12.13 | 0 | 21 tests, OK |
| `python tools/validate.py --check` | Git archive, Python 3.12.13 | 0 | Validation passed |
| `python -m unittest discover -s tests -v` | Git archive, Python 3.12.13 | 0 | 21 tests, OK |
| README export command, fresh temporary output and identical replay | Local and archive, Python 3.12.13 | 0 | EXPORTED then ALREADY_EXPORTED; both fixture signals preserved |
| `git diff --check` and `git diff --cached --check` | Source checkout | 0 | No whitespace errors |

Archive verification used staged tree
`bbb6c47cbe2c8b5a9d809f1c45b717c7ba5b1545` via `git archive`, without adding
`.git` to the extracted source. Only this verification section was added after
that snapshot; the tested code, configuration, schemas and tests are unchanged.
Content comparison also passed: transferred README sections and contract tests
match their source, main's contract text remains present, and main's product
code, schemas, configuration, existing data and AAK-12 documents have no diff.

Initial local test runs on both interpreters exited 1 (21 tests, one CLI failure)
because the synthetic code checkout lacked the existing `.gitignore` and Python
bytecode made it dirty. Copying that file fixed the fixture; the complete reruns
above passed. An initial export helper exited 1 after successful exports because
it incorrectly assumed one fixture signal. The corrected helper compares all
signals to the checked-in fixture and passed with two signals. No failing check
was skipped or treated as passing. Unresolved acceptance items: none.

## Privacy and review handoff

No real viewer records, consent changes, raw responses, credentials or external
artifacts are added. Explicit feedback remains distinct from inferred feedback;
neither is created by this maintenance task. No push, PR creation, GitHub write,
merge, release or default-branch change is performed by the implementation agent.
The next operation is orchestrator review of this local commit, followed by its
authorized publication and default-branch/pin reconciliation.
