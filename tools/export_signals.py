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
    if output.is_symlink():
        raise ContractError("VIEWER-EXPORT-CONFLICT", "symlink output is not permitted", str(output))
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
        # Atomic create-only publication: a concurrent writer is never overwritten.
        try:
            os.link(temporary_name, output)
        except FileExistsError:
            if not output.is_symlink() and output.read_bytes() == content:
                os.unlink(temporary_name)
                return "ALREADY_EXPORTED"
            raise ContractError("VIEWER-EXPORT-CONFLICT", "concurrent output differs", str(output))
        os.unlink(temporary_name)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return "EXPORTED"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, nargs="?")
    parser.add_argument("--export-id")
    parser.add_argument("--source-commit")
    parser.add_argument("--memory-query", type=Path, help="explicit external pinned viewer memory query JSON")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.memory_query:
            from viewer_memory import ViewerMemory
            query = json.loads(args.memory_query.read_text())
            if set(query) != {"store_root", "creator", "collection", "code_commit", "knowledge_commit", "scope", "at"}:
                raise ValueError("closed memory query required")
            memory = ViewerMemory(query["store_root"], query["creator"], query["collection"], query["code_commit"])
            envelope = memory.query(query["knowledge_commit"], query["scope"], at=query["at"])
        else:
            if args.records is None or not args.export_id or not args.source_commit:
                parser.error("records, --export-id and --source-commit are required without --memory-query")
            envelope = build_export(load_jsonl(args.records), export_id=args.export_id, source_commit=args.source_commit)
        result = write_export(envelope, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(str(exc))
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
