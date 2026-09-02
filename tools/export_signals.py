#!/usr/bin/env python3
"""Export viewer records as a deterministic research-signal envelope."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from viewer_contract import ContractError, EXPORT_ID_RE, EXPORT_SCHEMA_ID, load_jsonl, stable_json, validate_records


def build_export(records: list[dict], *, export_id: str, source_commit: str) -> dict:
    validated = validate_records(records)
    if not isinstance(export_id, str) or not EXPORT_ID_RE.fullmatch(export_id):
        raise ContractError("VIEWER-EXPORT-CONTRACT", "export_id must start with VRSE-", "export_id")
    if not isinstance(source_commit, str) or len(source_commit) != 40 or any(char not in "0123456789abcdef" for char in source_commit):
        raise ContractError("VIEWER-EXPORT-PROVENANCE", "source_commit must be a 40-character commit", "source_commit")
    if any(record["source_commit"] != source_commit for record in validated):
        raise ContractError("VIEWER-EXPORT-PROVENANCE", "all signals must retain the envelope source commit", "source_commit")
    return {"schema_id": EXPORT_SCHEMA_ID, "export_id": export_id, "source_commit": source_commit, "signals": sorted(validated, key=lambda record: record["record_id"])}


def write_export(envelope: dict, output: Path) -> str:
    content = (stable_json(envelope) + "\n").encode("utf-8")
    if output.exists():
        if output.read_bytes() == content:
            return "ALREADY_EXPORTED"
        raise ContractError("VIEWER-EXPORT-CONFLICT", "existing output contains different bytes", str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=str(output.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, output)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return "EXPORTED"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--export-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = write_export(build_export(load_jsonl(args.records), export_id=args.export_id, source_commit=args.source_commit), args.output)
    except ContractError as exc:
        print(str(exc))
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
