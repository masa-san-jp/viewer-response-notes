#!/usr/bin/env python3
"""Create a deterministic conservative assessment from viewer records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from assessment import assess_and_validate  # noqa: E402
from viewer_contract import ContractError, load_jsonl, stable_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--work-id", required=True)
    parser.add_argument("--requirement-id", required=True)
    parser.add_argument("--presentation-mode", required=True)
    parser.add_argument("--tag", action="append", required=True, dest="tags")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        value = assess_and_validate(load_jsonl(args.records), work_id=args.work_id, requirement_id=args.requirement_id, presentation_mode=args.presentation_mode, requirement_tags=args.tags)
    except ContractError as exc:
        print(str(exc))
        return 2
    content = stable_json(value) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(args.output)
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

