"""Strict, privacy-safe contracts for viewer response records."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


RECORD_SCHEMA_ID = "viewer-response-record/v1"
EXPORT_SCHEMA_ID = "research-signal-export/v1"
RECORD_REQUIRED = {
    "record_id", "work_id", "requirement_id", "source_kind", "presentation_mode",
    "requirement_tags", "sample_size", "outcome_counts", "evidence_refs",
    "certainty", "consent_scope", "source_commit", "observed_at", "dedup_key",
}
RECORD_ID_RE = re.compile(r"^VRR-[A-Z0-9][A-Z0-9._-]*$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
MODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPORT_ID_RE = re.compile(r"^VRSE-[A-Za-z0-9._-]+$")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<![A-Za-z0-9])\+?[0-9][0-9 ()-]{7,}[0-9](?![A-Za-z0-9])")
PRIVATE_URL_RE = re.compile(
    r"https?://(?:localhost|127(?:\.[0-9]{1,3}){3}|10(?:\.[0-9]{1,3}){3}|192\.168(?:\.[0-9]{1,3}){2}|172\.(?:1[6-9]|2[0-9]|3[0-1])(?:\.[0-9]{1,3}){2})(?:[/?:#]|$)",
    re.I,
)
FORBIDDEN_RE = re.compile(r"PRIVATE_RAW|RESTRICTED|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|password\s*=|token\s*=|secret\s*=", re.I)


class ContractError(ValueError):
    """A named fail-closed contract error."""

    def __init__(self, rule: str, message: str, path: str = "record") -> None:
        self.rule = rule
        self.path = path
        super().__init__(f"{path}: [{rule}] {message}")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def dedup_key(record: dict[str, Any]) -> str:
    payload = [
        record.get("work_id"),
        record.get("requirement_id"),
        record.get("presentation_mode"),
        sorted(record.get("evidence_refs", [])),
    ]
    return f"sha256:{hashlib.sha256(stable_json(payload).encode('utf-8')).hexdigest()}"


def _walk_strings(value: Any, path: str = "record") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def _privacy_scan(value: Any) -> None:
    for path, text in _walk_strings(value):
        if any(marker in text for marker in ("\n", "\r", "\x00")):
            raise ContractError("VIEWER-PRIVACY", "control characters are not permitted", path)
        if EMAIL_RE.search(text) or PHONE_RE.search(text) or FORBIDDEN_RE.search(text):
            raise ContractError("VIEWER-PRIVACY", "PII, credential, or restricted marker is not permitted", path)
        if PRIVATE_URL_RE.search(text) or re.search(r"https?://[^\s]+@", text, re.I):
            raise ContractError("VIEWER-PRIVACY", "private or credential-bearing URL is not permitted", path)
        if text.startswith(("/", "~/", "file://")) or re.match(r"^[A-Za-z]:[\\/]", text):
            raise ContractError("VIEWER-PRIVACY", "absolute path is not permitted", path)


def _require_int(value: Any, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError("VIEWER-RECORD-CONTRACT", "expected a non-negative integer", path)


def _require_identifier(value: Any, pattern: re.Pattern[str], path: str) -> None:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ContractError("VIEWER-RECORD-CONTRACT", "invalid identifier", path)


def validate_record(record: Any, *, path: str = "record") -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ContractError("VIEWER-RECORD-CONTRACT", "record must be an object", path)
    unknown = sorted(set(record) - RECORD_REQUIRED)
    missing = sorted(RECORD_REQUIRED - set(record))
    if unknown:
        raise ContractError("VIEWER-RECORD-UNKNOWN-FIELD", f"unknown field(s): {', '.join(unknown)}", path)
    if missing:
        raise ContractError("VIEWER-RECORD-CONTRACT", f"missing field(s): {', '.join(missing)}", path)
    _privacy_scan(record)
    _require_identifier(record["record_id"], RECORD_ID_RE, f"{path}.record_id")
    _require_identifier(record["work_id"], IDENTIFIER_RE, f"{path}.work_id")
    _require_identifier(record["requirement_id"], IDENTIFIER_RE, f"{path}.requirement_id")
    _require_identifier(record["presentation_mode"], MODE_RE, f"{path}.presentation_mode")
    if record["source_kind"] not in {"measured", "external"}:
        raise ContractError("VIEWER-RECORD-CONTRACT", "source_kind must be measured or external", f"{path}.source_kind")
    tags = record["requirement_tags"]
    if not isinstance(tags, list) or not tags or any(not isinstance(tag, str) or not TAG_RE.fullmatch(tag) for tag in tags):
        raise ContractError("VIEWER-RECORD-CONTRACT", "requirement_tags must contain one or more safe tags", f"{path}.requirement_tags")
    if len(set(tags)) != len(tags) or tags != sorted(tags):
        raise ContractError("VIEWER-RECORD-DETERMINISM", "requirement_tags must be unique and sorted", f"{path}.requirement_tags")
    _require_int(record["sample_size"], f"{path}.sample_size")
    counts = record["outcome_counts"]
    if not isinstance(counts, dict) or set(counts) != {"pass", "fail", "unknown"}:
        raise ContractError("VIEWER-RECORD-CONTRACT", "outcome_counts must contain exactly pass/fail/unknown", f"{path}.outcome_counts")
    for key, value in counts.items():
        _require_int(value, f"{path}.outcome_counts.{key}")
    if sum(counts.values()) != record["sample_size"]:
        raise ContractError("VIEWER-RECORD-COUNTS", "outcome counts must sum to sample_size", f"{path}.outcome_counts")
    refs = record["evidence_refs"]
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
        raise ContractError("VIEWER-RECORD-CONTRACT", "evidence_refs must contain opaque references", f"{path}.evidence_refs")
    if len(set(refs)) != len(refs) or refs != sorted(refs):
        raise ContractError("VIEWER-RECORD-DETERMINISM", "evidence_refs must be unique and sorted", f"{path}.evidence_refs")
    for ref in refs:
        if not (ref.startswith("https://") or ref.startswith("doi:") or ref.startswith("production-result:") or ref.startswith("viewer-response:")):
            raise ContractError("VIEWER-RECORD-EVIDENCE", "evidence reference must be an opaque https/doi/project reference", f"{path}.evidence_refs")
    if record["certainty"] not in {"high", "medium", "low", "unknown"}:
        raise ContractError("VIEWER-RECORD-CONTRACT", "invalid certainty", f"{path}.certainty")
    if record["consent_scope"] != "aggregate-only":
        raise ContractError("VIEWER-PRIVACY", "consent_scope must be aggregate-only", f"{path}.consent_scope")
    if not isinstance(record["source_commit"], str) or not COMMIT_RE.fullmatch(record["source_commit"]):
        raise ContractError("VIEWER-RECORD-PROVENANCE", "source_commit must be a 40-character commit", f"{path}.source_commit")
    if not isinstance(record["observed_at"], str):
        raise ContractError("VIEWER-RECORD-CONTRACT", "observed_at must be RFC3339", f"{path}.observed_at")
    try:
        parsed = datetime.fromisoformat(record["observed_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("VIEWER-RECORD-CONTRACT", "observed_at must be RFC3339", f"{path}.observed_at") from exc
    if parsed.tzinfo is None:
        raise ContractError("VIEWER-RECORD-CONTRACT", "observed_at must include a timezone", f"{path}.observed_at")
    if record["source_kind"] == "external":
        if record["sample_size"] != 0 or any(counts.values()):
            raise ContractError("VIEWER-EXTERNAL-NO-FABRICATED-SAMPLE", "external records cannot contain sample or outcome counts", path)
    expected_key = dedup_key(record)
    if not isinstance(record["dedup_key"], str) or not SHA256_RE.fullmatch(record["dedup_key"]):
        raise ContractError("VIEWER-RECORD-DEDUP", "dedup_key must be a sha256 digest", f"{path}.dedup_key")
    if record["dedup_key"] != expected_key:
        raise ContractError("VIEWER-RECORD-DEDUP", "dedup_key does not match the canonical record inputs", f"{path}.dedup_key")
    return record


def validate_records(records: Iterable[Any], *, path: str = "records") -> list[dict[str, Any]]:
    validated = [validate_record(record, path=f"{path}[{index}]") for index, record in enumerate(records)]
    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    for record in validated:
        if record["record_id"] in seen_ids:
            raise ContractError("VIEWER-RECORD-DUPLICATE", "record_id must be unique", path)
        if record["dedup_key"] in seen_keys:
            raise ContractError("VIEWER-RECORD-DUPLICATE", "dedup_key must be unique; append a corrected record instead", path)
        seen_ids.add(record["record_id"])
        seen_keys.add(record["dedup_key"])
    return validated


def validate_assessment(value: Any, *, path: str = "assessment") -> dict[str, Any]:
    required = {
        "schema_id", "assessment_id", "work_id", "requirement_id", "presentation_mode",
        "matching_tags", "status", "measured_sample_size", "outcome_counts",
        "confidence_interval", "source_record_ids", "external_evidence_refs", "conflict",
        "review_required", "review_kind", "source_commits",
    }
    if not isinstance(value, dict):
        raise ContractError("VIEWER-ASSESSMENT-CONTRACT", "assessment must be an object", path)
    unknown = sorted(set(value) - required)
    missing = sorted(required - set(value))
    if unknown:
        raise ContractError("VIEWER-ASSESSMENT-UNKNOWN-FIELD", f"unknown field(s): {', '.join(unknown)}", path)
    if missing:
        raise ContractError("VIEWER-ASSESSMENT-CONTRACT", f"missing field(s): {', '.join(missing)}", path)
    if value["schema_id"] != "viewer-response-assessment/v1":
        raise ContractError("VIEWER-ASSESSMENT-CONTRACT", "invalid schema_id", f"{path}.schema_id")
    if not isinstance(value["assessment_id"], str) or not value["assessment_id"].startswith("VRA-"):
        raise ContractError("VIEWER-ASSESSMENT-CONTRACT", "invalid assessment_id", f"{path}.assessment_id")
    if value["status"] not in {"UNKNOWN", "SUPPORTED", "CONTRADICTED", "EXTERNALLY_SUPPORTED"}:
        raise ContractError("VIEWER-ASSESSMENT-CONTRACT", "invalid status", f"{path}.status")
    _require_int(value["measured_sample_size"], f"{path}.measured_sample_size")
    counts = value["outcome_counts"]
    if not isinstance(counts, dict) or set(counts) != {"pass", "fail", "unknown"}:
        raise ContractError("VIEWER-ASSESSMENT-CONTRACT", "outcome_counts must contain exactly pass/fail/unknown", f"{path}.outcome_counts")
    for key, count in counts.items():
        _require_int(count, f"{path}.outcome_counts.{key}")
    if sum(counts.values()) != value["measured_sample_size"]:
        raise ContractError("VIEWER-ASSESSMENT-COUNTS", "outcome counts must sum to measured_sample_size", f"{path}.outcome_counts")
    interval = value["confidence_interval"]
    if interval is not None and (not isinstance(interval, dict) or interval.get("level") != 0.95 or not isinstance(interval.get("lower"), (int, float)) or not isinstance(interval.get("upper"), (int, float))):
        raise ContractError("VIEWER-ASSESSMENT-CONTRACT", "confidence_interval must be null or a Wilson 95% interval", f"{path}.confidence_interval")
    if value["review_required"] != (value["status"] in {"UNKNOWN", "CONTRADICTED", "EXTERNALLY_SUPPORTED"}):
        raise ContractError("VIEWER-ASSESSMENT-REVIEW", "review_required must follow the conservative status rule", f"{path}.review_required")
    expected_review_kind = "BLIND_OR_FRAME" if value["review_required"] else "NONE"
    if value["review_kind"] != expected_review_kind:
        raise ContractError("VIEWER-ASSESSMENT-REVIEW", "review_kind must follow review_required", f"{path}.review_kind")
    _privacy_scan(value)
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.is_file():
        raise ContractError("VIEWER-INPUT", f"input file does not exist: {path}", str(path))
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ContractError("VIEWER-INPUT", f"invalid JSON: {exc.msg}", f"{path}:{line_number}") from exc
        records.append(value)
    return records
