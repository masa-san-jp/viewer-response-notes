from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from assessment import assess, assess_and_validate, wilson95  # noqa: E402
from export_signals import build_export, write_export  # noqa: E402
from viewer_contract import ContractError, dedup_key, validate_record, validate_records  # noqa: E402


COMMIT = "0123456789abcdef0123456789abcdef01234567"


def record(record_id: str, requirement_id: str, *, source_kind: str = "measured", sample_size: int = 0, passed: int = 0, failed: int = 0, unknown: int = 0, refs: list[str] | None = None, mode: str = "gallery", tags: list[str] | None = None) -> dict:
    value = {
        "record_id": record_id,
        "work_id": "work/demo",
        "requirement_id": requirement_id,
        "source_kind": source_kind,
        "presentation_mode": mode,
        "requirement_tags": tags or ["clarity"],
        "sample_size": sample_size,
        "outcome_counts": {"pass": passed, "fail": failed, "unknown": unknown},
        "evidence_refs": sorted(refs or [f"production-result:PR001#{record_id}"]),
        "certainty": "high" if source_kind == "measured" else "medium",
        "consent_scope": "aggregate-only",
        "source_commit": COMMIT,
        "observed_at": "2026-08-26T00:00:00+09:00",
    }
    value["dedup_key"] = dedup_key(value)
    return value


class ViewerContractTests(unittest.TestCase):
    def test_record_is_closed_and_dedup_is_canonical(self) -> None:
        value = record("VRR-001", "REQ-1", sample_size=4, passed=2, failed=1, unknown=1)
        self.assertIs(validate_record(value), value)
        changed = copy.deepcopy(value)
        changed["evidence_refs"] = ["production-result:PR001#different"]
        with self.assertRaisesRegex(ContractError, "VIEWER-RECORD-DEDUP"):
            validate_record(changed)

    def test_measured_counts_must_sum_to_sample(self) -> None:
        value = record("VRR-002", "REQ-1", sample_size=4, passed=2, failed=1, unknown=1)
        value["sample_size"] = 5
        with self.assertRaisesRegex(ContractError, "VIEWER-RECORD-COUNTS"):
            validate_record(value)

    def test_external_cannot_fabricate_sample(self) -> None:
        value = record("VRR-003", "REQ-1", source_kind="external", sample_size=1, passed=1, refs=["doi:10.1000/example"])
        value["dedup_key"] = dedup_key(value)
        with self.assertRaisesRegex(ContractError, "VIEWER-EXTERNAL-NO-FABRICATED-SAMPLE"):
            validate_record(value)

    def test_unknown_fields_and_private_data_fail_closed(self) -> None:
        value = record("VRR-004", "REQ-1", sample_size=1, passed=1)
        value["answer_text"] = "private"
        with self.assertRaisesRegex(ContractError, "VIEWER-RECORD-UNKNOWN-FIELD"):
            validate_record(value)
        value = record("VRR-005", "REQ-1", sample_size=1, passed=1, refs=["https://localhost/raw"])
        with self.assertRaisesRegex(ContractError, "VIEWER-PRIVACY"):
            validate_record(value)

    def test_duplicate_record_id_and_dedup_key_are_blocking(self) -> None:
        first = record("VRR-006", "REQ-1", sample_size=1, passed=1)
        second = copy.deepcopy(first)
        second["record_id"] = "VRR-007"
        with self.assertRaisesRegex(ContractError, "VIEWER-RECORD-DUPLICATE"):
            validate_records([first, second])

    def test_wilson_thresholds_are_deterministic(self) -> None:
        self.assertEqual(wilson95(19, 20), wilson95(19, 20))
        self.assertGreaterEqual(wilson95(19, 20)["lower"], 0.60)
        self.assertLess(wilson95(5, 20)["upper"], 0.60)

    def test_assessment_unknown_for_small_sample(self) -> None:
        value = assess([record("VRR-010", "REQ-1", sample_size=4, passed=4)], work_id="work/demo", requirement_id="REQ-1", presentation_mode="gallery", requirement_tags=["clarity"])
        self.assertEqual(value["status"], "UNKNOWN")
        self.assertTrue(value["review_required"])
        self.assertEqual(value["review_kind"], "BLIND_OR_FRAME")

    def test_assessment_supported_and_contradicted(self) -> None:
        supported = assess([record("VRR-011", "REQ-1", sample_size=20, passed=19, failed=1)], work_id="work/demo", requirement_id="REQ-1", presentation_mode="gallery", requirement_tags=["clarity"])
        contradicted = assess([record("VRR-012", "REQ-2", sample_size=20, passed=5, failed=15)], work_id="work/demo", requirement_id="REQ-2", presentation_mode="gallery", requirement_tags=["clarity"])
        self.assertEqual(supported["status"], "SUPPORTED")
        self.assertEqual(contradicted["status"], "CONTRADICTED")

    def test_external_support_and_measured_conflict(self) -> None:
        external = [record("VRR-020", "REQ-3", source_kind="external", refs=["doi:10.1000/a"]), record("VRR-021", "REQ-3", source_kind="external", refs=["doi:10.1000/b"])]
        value = assess(external, work_id="work/demo", requirement_id="REQ-3", presentation_mode="gallery", requirement_tags=["clarity"])
        self.assertEqual(value["status"], "EXTERNALLY_SUPPORTED")
        measured = record("VRR-022", "REQ-3", sample_size=20, passed=5, failed=15)
        value = assess(external + [measured], work_id="work/demo", requirement_id="REQ-3", presentation_mode="gallery", requirement_tags=["clarity"])
        self.assertEqual(value["status"], "CONTRADICTED")
        self.assertTrue(value["conflict"])

    def test_matching_requires_exact_mode_and_tag_intersection(self) -> None:
        value = record("VRR-030", "REQ-4", sample_size=20, passed=19, failed=1, mode="detail", tags=["motion"])
        result = assess([value], work_id="work/demo", requirement_id="REQ-4", presentation_mode="gallery", requirement_tags=["clarity"])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["source_record_ids"], [])

    def test_no_match_has_no_fabricated_source_commit(self) -> None:
        result = assess_and_validate([record("VRR-031", "REQ-4", sample_size=1, passed=1, mode="detail")], work_id="work/demo", requirement_id="REQ-4", presentation_mode="gallery", requirement_tags=["clarity"])
        self.assertEqual(result["source_commits"], [])

    def test_export_is_deterministic_atomic_and_idempotent(self) -> None:
        values = [record("VRR-040", "REQ-1", sample_size=1, passed=1), record("VRR-041", "REQ-1", sample_size=1, failed=1)]
        first = build_export(values, export_id="VRSE-fixture", source_commit=COMMIT)
        second = build_export(list(reversed(values)), export_id="VRSE-fixture", source_commit=COMMIT)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "export.json"
            self.assertEqual(write_export(first, output), "EXPORTED")
            self.assertEqual(write_export(first, output), "ALREADY_EXPORTED")
            changed = dict(first)
            changed["export_id"] = "VRSE-other"
            with self.assertRaisesRegex(ContractError, "VIEWER-EXPORT-CONFLICT"):
                write_export(changed, output)


if __name__ == "__main__":
    unittest.main()
