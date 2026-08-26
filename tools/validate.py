#!/usr/bin/env python3
"""Validate checked-in viewer response records, assessments, and exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from viewer_contract import ContractError, EXPORT_SCHEMA_ID, load_jsonl, validate_assessment, validate_records  # noqa: E402


def _json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("VIEWER-INPUT", str(exc), str(path)) from exc


def validate_export(value: object, path: str) -> None:
    if not isinstance(value, dict) or set(value) != {"schema_id", "export_id", "source_commit", "signals"}:
        raise ContractError("VIEWER-EXPORT-CONTRACT", "export envelope fields are not closed", path)
    if value["schema_id"] != EXPORT_SCHEMA_ID or not isinstance(value["signals"], list):
        raise ContractError("VIEWER-EXPORT-CONTRACT", "invalid research-signal export envelope", path)
    records = validate_records(value["signals"], path=f"{path}.signals")
    if any(record["source_commit"] != value["source_commit"] for record in records):
        raise ContractError("VIEWER-EXPORT-PROVENANCE", "all signals must retain the envelope source commit", path)


def validate_repository(root: Path) -> list[str]:
    findings: list[str] = []
    records_dir = root / "records"
    for path in sorted(records_dir.glob("*.jsonl")) if records_dir.is_dir() else []:
        try:
            validate_records(load_jsonl(path), path=str(path))
        except ContractError as exc:
            findings.append(str(exc))
    exports_dir = root / "exports"
    for path in sorted(exports_dir.glob("*.json")) if exports_dir.is_dir() else []:
        try:
            validate_export(_json(path), str(path))
        except ContractError as exc:
            findings.append(str(exc))
    assessments_dir = root / "assessments"
    for path in sorted(assessments_dir.glob("*.json")) if assessments_dir.is_dir() else []:
        try:
            validate_assessment(_json(path), path=str(path))
        except ContractError as exc:
            findings.append(str(exc))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if not args.check:
        parser.error("--check is required")
    findings = validate_repository(args.root.resolve())
    if findings:
        print("\n".join(findings))
        return 1
    print("OK: viewer-response-notes validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
