"""Deterministic conservative viewer-response assessment."""

from __future__ import annotations

import math
from typing import Any, Iterable

from viewer_contract import validate_assessment, validate_records


Z95 = 1.959963984540054


def wilson95(successes: int, trials: int) -> dict[str, float] | None:
    if trials <= 0:
        return None
    z2 = Z95 * Z95
    proportion = successes / trials
    denominator = 1 + z2 / trials
    centre = (proportion + z2 / (2 * trials)) / denominator
    margin = Z95 * math.sqrt((proportion * (1 - proportion) / trials) + (z2 / (4 * trials * trials))) / denominator
    return {
        "level": 0.95,
        "lower": round(max(0.0, centre - margin), 6),
        "upper": round(min(1.0, centre + margin), 6),
    }


def assess(
    records: Iterable[dict[str, Any]],
    *,
    work_id: str,
    requirement_id: str,
    presentation_mode: str,
    requirement_tags: Iterable[str],
) -> dict[str, Any]:
    validated = validate_records(list(records))
    requested_tags = set(requirement_tags)
    matching = [
        record for record in validated
        if record["work_id"] == work_id
        and record["requirement_id"] == requirement_id
        and record["presentation_mode"] == presentation_mode
        and requested_tags.intersection(record["requirement_tags"])
    ]
    matching.sort(key=lambda record: record["record_id"])
    measured = [record for record in matching if record["source_kind"] == "measured"]
    external = [record for record in matching if record["source_kind"] == "external"]
    counts = {"pass": sum(record["outcome_counts"]["pass"] for record in measured), "fail": sum(record["outcome_counts"]["fail"] for record in measured), "unknown": sum(record["outcome_counts"]["unknown"] for record in measured)}
    measured_sample = sum(record["sample_size"] for record in measured)
    external_refs = sorted({ref for record in external for ref in record["evidence_refs"]})
    interval = wilson95(counts["pass"], counts["pass"] + counts["fail"])
    if measured_sample == 0 and len(external_refs) >= 2:
        status = "EXTERNALLY_SUPPORTED"
    elif measured_sample < 5:
        status = "UNKNOWN"
    elif interval is not None and interval["lower"] >= 0.60:
        status = "SUPPORTED"
    elif interval is not None and interval["upper"] < 0.60:
        status = "CONTRADICTED"
    else:
        status = "UNKNOWN"
    source_commits = sorted({record["source_commit"] for record in matching})
    source_ids = [record["record_id"] for record in matching]
    tags = sorted({tag for record in matching for tag in requested_tags.intersection(record["requirement_tags"])})
    review_required = status in {"UNKNOWN", "CONTRADICTED", "EXTERNALLY_SUPPORTED"}
    return {
        "schema_id": "viewer-response-assessment/v1",
        "assessment_id": f"VRA-{work_id.replace('/', '-')}-{requirement_id.replace('/', '-')}-{presentation_mode}",
        "work_id": work_id,
        "requirement_id": requirement_id,
        "presentation_mode": presentation_mode,
        "matching_tags": tags or sorted(requested_tags),
        "status": status,
        "measured_sample_size": measured_sample,
        "outcome_counts": counts,
        "confidence_interval": interval,
        "source_record_ids": source_ids,
        "external_evidence_refs": external_refs,
        "conflict": bool(measured and external),
        "review_required": review_required,
        "review_kind": "BLIND_OR_FRAME" if review_required else "NONE",
        "source_commits": source_commits,
    }


def assess_and_validate(
    records: Iterable[dict[str, Any]],
    *,
    work_id: str,
    requirement_id: str,
    presentation_mode: str,
    requirement_tags: Iterable[str],
) -> dict[str, Any]:
    return validate_assessment(assess(records, work_id=work_id, requirement_id=requirement_id, presentation_mode=presentation_mode, requirement_tags=requirement_tags))
