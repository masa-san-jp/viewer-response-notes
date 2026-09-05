"""Versioned condition/lineage wrapper around unchanged aggregate viewer contracts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime

from viewer_contract import (ContractError, validate_record, validate_records, stable_json,
    _privacy_scan, IDENTIFIER_RE, COMMIT_RE, RECORD_ID_RE)
from assessment import assess_and_validate
from export_signals import build_export

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "config/viewer-memory.json").read_text())
FIELDS = set("contract_version record_id revision origin_instance_id creator_id owner_repository collection_id kind payload_schema payload_ref content_sha256 sources derived_from epistemic_status lifecycle applicability rights access_scope consent_ref created_at reviewed_at valid_until producer supersedes invalidates".split())


def encoded(value):
    return stable_json(value).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def key(record):
    return digest(encoded([record[k] for k in ("origin_instance_id", "owner_repository", "record_id", "revision")]))


def moment(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("explicit timezone required")
    return parsed


def validate_payload(payload):
    if not isinstance(payload, dict) or set(payload) != {"record", "context"}:
        raise ValueError("closed aggregate record/context payload required")
    r = validate_record(payload["record"])
    c = payload["context"]
    if not isinstance(c, dict) or set(c) != set(POLICY["context_fields"]):
        raise ValueError("closed lineage/collection context required; no free responses")
    _privacy_scan(c)
    for field in ("project_id", "presentation_conditions_ref", "source_identity"):
        if not isinstance(c[field], str) or not IDENTIFIER_RE.fullmatch(c[field]):
            raise ValueError("opaque context identifier required")
    if type(c["work_revision"]) is not int or c["work_revision"] < 1 or c["collection_method"] not in POLICY["collection_methods"]:
        raise ValueError("explicit work revision and collection method required")
    if moment(c["period_start"]) > moment(c["period_end"]):
        raise ValueError("invalid collection period")
    if moment(r["observed_at"]) < moment(c["period_start"]) or moment(r["observed_at"]) > moment(c["period_end"]):
        raise ValueError("observation outside collection period")
    for field in ("intended_experience_refs", "sample_set_ids", "overlaps_sample_sets", "corrects_record_ids"):
        values = c[field]
        if not isinstance(values, list) or values != sorted(set(values)) or any(not isinstance(v, str) or not IDENTIFIER_RE.fullmatch(v) for v in values):
            raise ValueError("sorted unique opaque reference list required")
    if not c["intended_experience_refs"]:
        raise ValueError("intended experience reference required")
    if r["source_kind"] == "external" and (c["sample_set_ids"] or c["overlaps_sample_sets"]):
        raise ValueError("external evidence cannot invent a sample set")
    if r["sample_size"] and not c["sample_set_ids"]:
        raise ValueError("measured sample-set identity required")
    return payload


def active_payloads(candidates):
    corrected = {identifier for c in candidates for identifier in c["payload"]["context"]["corrects_record_ids"]}
    return [c for c in candidates if c["payload"]["record"]["record_id"] not in corrected and c["artifact"]["lifecycle"] == "accepted"]


class ViewerMemory:
    ref = "refs/heads/knowledge"

    def __init__(self, root, creator, collection, code_commit):
        self.root = Path(root)
        if not self.root.is_absolute() or self.root.resolve() != self.root or self.root == ROOT or ROOT in self.root.parents:
            raise ValueError("explicit nonsymlink external owner Git store required")
        self.creator, self.collection, self.code_commit = creator, collection, code_commit
        if json.loads((self.root / "store.json").read_text()) != {"owner": POLICY["owner"], "creator": creator, "collection": collection}:
            raise ValueError("creator/owner/collection mismatch")
        if (self.root / "objects.git").is_symlink():
            raise ValueError("symlink Git store forbidden")
        if subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip() != code_commit or subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"]):
            raise ValueError("clean qualified code checkout required")

    def git(self, *args, body=None, index=None):
        env = os.environ.copy()
        if index: env["GIT_INDEX_FILE"] = str(index)
        result = subprocess.run(["git", "--git-dir", str(self.root / "objects.git"), "-c", "user.name=Viewer owner", "-c", "user.email=viewer@example.invalid", *args], input=body, capture_output=True, env=env)
        if result.returncode: raise ValueError("owner Git operation failed: " + result.stderr.decode().strip())
        return result.stdout

    def head(self):
        return self.git("rev-parse", self.ref).decode().strip()

    def read(self, commit, path):
        if not COMMIT_RE.fullmatch(commit): raise ValueError("immutable knowledge commit required")
        paths = self.git("ls-tree", "-r", "--name-only", commit, "--", path).decode().splitlines()
        return self.git("show", commit + ":" + path) if path in paths else None

    def candidates(self, commit):
        if not COMMIT_RE.fullmatch(commit): raise ValueError("immutable knowledge commit required")
        result = []
        for path in self.git("ls-tree", "-r", "--name-only", commit, "--", "records/memory/").decode().splitlines():
            artifact = json.loads(self.read(commit, path))
            if (artifact["owner_repository"], artifact["creator_id"], artifact["collection_id"]) != (POLICY["owner"], self.creator, self.collection):
                raise ValueError("stored creator/owner/collection mismatch")
            raw = self.read(commit, artifact["payload_ref"])
            if raw is None or digest(raw) != artifact["content_sha256"]:
                raise ValueError("stored payload hash mismatch")
            result.append({"artifact": artifact, "payload": validate_payload(json.loads(raw))})
        return result

    def validate(self, candidate):
        if set(candidate) != {"artifact", "payload"} or set(candidate["artifact"]) != FIELDS:
            raise ValueError("closed artifact-record/v1 required")
        a, p = candidate["artifact"], validate_payload(candidate["payload"])
        if (a["contract_version"], a["owner_repository"], a["creator_id"], a["collection_id"], a["kind"], a["payload_schema"]) != ("artifact-record/v1", POLICY["owner"], self.creator, self.collection, "viewer-response", POLICY["contract_version"]):
            raise ValueError("owner artifact identity mismatch")
        if a["record_id"] != p["record"]["record_id"] or a["revision"] != 1 or type(a["revision"]) is not int:
            raise ValueError("viewer correction requires a new record ID, not rewriting a revision")
        for field in ("creator_id", "origin_instance_id", "collection_id"):
            if not isinstance(a[field], str) or not IDENTIFIER_RE.fullmatch(a[field]): raise ValueError("opaque identity required")
        if a["payload_ref"] != "records/payloads/" + key(a) + ".json" or a["content_sha256"] != digest(encoded(p)):
            raise ValueError("payload path/hash mismatch")
        if a["rights"] != {"knowledge_write": True, "redistribute": False} or a["rights"]["knowledge_write"] is not True or a["access_scope"] != "creator-private" or not a["consent_ref"]:
            raise ValueError("explicit private aggregate-only owner permission required")
        expected = "observed" if p["record"]["source_kind"] == "measured" else "externally-supported"
        if a["epistemic_status"] != expected or a["lifecycle"] != "accepted":
            raise ValueError("native measured/external distinction required")
        if a["applicability"] != {"work_id": p["record"]["work_id"], "presentation_conditions_ref": p["context"]["presentation_conditions_ref"]}:
            raise ValueError("artifact applicability differs from payload")
        for field in ("created_at", "reviewed_at", "valid_until"):
            if a[field] is not None: moment(a[field])
        if a["created_at"] is None: raise ValueError("created_at required")
        producer = a["producer"]
        if set(producer) != {"kind", "generator_version", "code_commit", "run_id"} or producer["code_commit"] != self.code_commit or producer["kind"] not in {"agent", "human", "tool"} or not producer["run_id"]:
            raise ValueError("producer code/run provenance required")
        for field in ("sources", "derived_from", "supersedes", "invalidates"):
            if not isinstance(a[field], list): raise ValueError("reference list required")
        for source in a["sources"]:
            required = {"origin_instance_id", "record_id", "revision", "source_repository", "code_commit", "knowledge_commit", "locator", "content_sha256"}
            if not isinstance(source, dict) or set(source) != required:
                raise ValueError("closed source provenance required; no response metadata")
            if type(source["revision"]) is not int or source["revision"] < 1:
                raise ValueError("positive source revision required")
            for field in required - {"revision", "content_sha256"}:
                if not isinstance(source[field], str) or not IDENTIFIER_RE.fullmatch(source[field]):
                    raise ValueError("opaque source provenance required")
            if any(not COMMIT_RE.fullmatch(source[field]) for field in ("code_commit", "knowledge_commit")) or len(source["content_sha256"]) != 64 or any(c not in "0123456789abcdef" for c in source["content_sha256"]):
                raise ValueError("immutable source commits and SHA-256 required")
        for field in ("generator_version", "run_id"):
            if not isinstance(producer[field], str) or not IDENTIFIER_RE.fullmatch(producer[field]):
                raise ValueError("opaque producer metadata required")
        for field in ("derived_from", "supersedes", "invalidates"):
            for ref in a[field]:
                if not isinstance(ref, dict) or set(ref) != {"origin_instance_id", "owner_repository", "record_id", "revision"}:
                    raise ValueError("closed artifact identity reference required")
                if type(ref["revision"]) is not int or ref["revision"] < 1 or any(not isinstance(ref[k], str) or not IDENTIFIER_RE.fullmatch(ref[k]) for k in ("origin_instance_id", "owner_repository", "record_id")):
                    raise ValueError("invalid artifact identity reference")
        _privacy_scan({field:a[field] for field in ("creator_id", "origin_instance_id", "collection_id", "consent_ref", "sources", "derived_from", "supersedes", "invalidates")})
        return a

    def append(self, candidate, parent, operation, run, *, correction_approval_ref=None):
        head = self.head(); fingerprint = digest(encoded(candidate))
        op_path = "records/operations/" + digest(operation.encode()) + ".json"
        saved = self.read(head, op_path)
        if saved:
            if json.loads(saved) != {"candidate_hash": fingerprint, "parent": parent, "correction_approval_ref": correction_approval_ref}:
                raise ValueError("OPERATION_CONFLICT")
            commit = self.git("log", "-1", "--format=%H", head, "--", op_path).decode().strip()
            return self.receipt(candidate["artifact"], parent, commit, operation, run, "ALREADY_APPLIED")
        a = self.validate(candidate)
        if head != parent: raise ValueError("PARENT_CONFLICT")
        all_candidates = self.candidates(parent)
        known = {key(item["artifact"]) for item in all_candidates}
        for field in ("derived_from", "supersedes", "invalidates"):
            if any(key(ref) == key(a) or key(ref) not in known for ref in a[field]):
                raise ValueError("unresolved or self-referential artifact reference")
        p, c = candidate["payload"], candidate["payload"]["context"]
        validate_records([r["payload"]["record"] for r in all_candidates] + [p["record"]])
        if c["corrects_record_ids"] and not correction_approval_ref:
            raise ValueError("CORRECTION_HUMAN_GATE: explicit approval reference required")
        old = {x["payload"]["record"]["record_id"]:x for x in active_payloads(all_candidates)}
        for identifier in c["corrects_record_ids"]:
            if identifier not in old or old[identifier]["payload"]["record"]["work_id"] != p["record"]["work_id"]:
                raise ValueError("correction must reference an active record for the same work")
            old_a = old[identifier]["artifact"]
            ref = {k:old_a[k] for k in ("origin_instance_id", "owner_repository", "record_id", "revision")}
            if ref not in a["invalidates"]: raise ValueError("correction must invalidate its exact prior artifact")
        if {ref["record_id"] for ref in a["invalidates"]} != set(c["corrects_record_ids"]):
            raise ValueError("invalidations must match explicit native corrections")
        for existing in active_payloads(all_candidates):
            if existing["payload"]["record"]["record_id"] in c["corrects_record_ids"]: continue
            previous = existing["payload"]["context"]
            if previous["source_identity"] == c["source_identity"]:
                raise ValueError("DUPLICATE_SOURCE")
            current_sets = set(c["sample_set_ids"])
            previous_sets = set(previous["sample_set_ids"])
            if current_sets & previous_sets or current_sets & set(previous["overlaps_sample_sets"]) or previous_sets & set(c["overlaps_sample_sets"]):
                raise ValueError("OVERLAPPING_SAMPLES")
        if p["record"]["source_kind"] == "measured" and p["record"]["sample_size"] == 0:
            return self.receipt(a, parent, parent, operation, run, "NO_NEW_EVIDENCE")
        writes = {"records/memory/" + key(a) + ".json": encoded(a), a["payload_ref"]: encoded(p),
                  op_path: encoded({"candidate_hash": fingerprint, "parent": parent, "correction_approval_ref": correction_approval_ref})}
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            index = Path(directory) / "index"; self.git("read-tree", parent, index=index)
            for path, data in writes.items():
                blob = self.git("hash-object", "-w", "--stdin", body=data).decode().strip()
                self.git("update-index", "--add", "--cacheinfo", "100644," + blob + "," + path, index=index)
            tree = self.git("write-tree", index=index).decode().strip()
            commit = self.git("commit-tree", tree, "-p", parent, body=encoded({"operation": operation, "run": run})).decode().strip()
            self.git("update-ref", self.ref, commit, parent)
        return self.receipt(a, parent, commit, operation, run, "COMMITTED")

    def receipt(self, artifact, parent, commit, operation, run, status):
        return {"contract_version": "knowledge-write-receipt/v1", "operation_id": operation, "run_id": run, "owner": POLICY["owner"],
            "collection": self.collection, "target_parent": parent, "target_commit": commit, "accepted_ids": [] if status == "NO_NEW_EVIDENCE" else [artifact["record_id"]],
            "rejected_ids": [], "schema_version": POLICY["contract_version"], "policy_version": POLICY["contract_version"],
            "index_commit": None, "index_hash": None, "status": status, "reason": "Aggregate-only owner Git; assessment/export are separate create-only steps"}

    def query(self, commit, scope, *, at):
        if set(scope) != set(POLICY["scope_fields"]): raise ValueError("exact collection/work scope required")
        _privacy_scan(scope)
        now = moment(at)
        for field in ("project_id", "presentation_conditions_ref", "work_id", "requirement_id", "presentation_mode"):
            if not isinstance(scope[field], str) or not IDENTIFIER_RE.fullmatch(scope[field]): raise ValueError("opaque scope identity required")
        if type(scope["work_revision"]) is not int or scope["work_revision"] < 1 or scope["collection_method"] not in POLICY["collection_methods"] or moment(scope["period_start"]) > moment(scope["period_end"]):
            raise ValueError("invalid collection scope")
        if not isinstance(scope["requirement_tags"], list) or not scope["requirement_tags"] or scope["requirement_tags"] != sorted(set(scope["requirement_tags"])):
            raise ValueError("nonempty unique scope tags required")
        matches = []
        revalidation = []
        for item in active_payloads(self.candidates(commit)):
            p = item["payload"]
            if all(p["context"].get(k, p["record"].get(k)) == value for k, value in scope.items() if k != "requirement_tags") and set(scope["requirement_tags"]) & set(p["record"]["requirement_tags"]):
                if item["artifact"]["valid_until"] is not None and moment(item["artifact"]["valid_until"]) <= now:
                    revalidation.append(p["record"]["record_id"])
                    continue
                matches.append(item)
        records = [i["payload"]["record"] for i in matches]
        assessment = assess_and_validate(records, **{k:scope[k] for k in ("work_id", "requirement_id", "presentation_mode", "requirement_tags")})
        exports = [build_export([r for r in records if r["source_commit"] == sha], export_id="VRSE-memory-" + sha, source_commit=sha) for sha in sorted({r["source_commit"] for r in records})]
        return {"contract_version": "viewer-memory-export/v1", "creator_id": self.creator, "code_commit": self.code_commit,
            "knowledge_commit": commit, "scope": scope, "knowledge_status": "COMMITTED" if records else "NO_NEW_EVIDENCE",
            "assessment": assessment, "exports": exports, "source_record_ids": [r["record_id"] for r in records], "revalidation_required": revalidation, "evaluated_at": at}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "append", "query"])
    parser.add_argument("--store-root", type=Path, required=True); parser.add_argument("--creator", required=True)
    parser.add_argument("--collection", required=True); parser.add_argument("--code-commit", required=True)
    parser.add_argument("--knowledge-commit", required=True); parser.add_argument("--candidate", type=Path)
    parser.add_argument("--operation-id"); parser.add_argument("--run-id"); parser.add_argument("--scope", type=Path)
    parser.add_argument("--correction-approval-ref")
    parser.add_argument("--at", help="explicit query clock")
    args = parser.parse_args()
    try:
        memory = ViewerMemory(args.store_root, args.creator, args.collection, args.code_commit)
        if args.command == "query": result = memory.query(args.knowledge_commit, json.loads(args.scope.read_text()), at=args.at)
        else:
            candidate = json.loads(args.candidate.read_text())
            if args.command == "validate": memory.validate(candidate); result = {"status": "VALID"}
            else:
                if not args.operation_id or not args.run_id: raise ValueError("operation/run required")
                result = memory.append(candidate, args.knowledge_commit, args.operation_id, args.run_id, correction_approval_ref=args.correction_approval_ref)
        print(stable_json(result)); return 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        status = "CONFLICT" if str(exc) in {"OPERATION_CONFLICT", "PARENT_CONFLICT"} else "REJECTED"
        print(stable_json({"status": status, "reason": str(exc)})); return 2


if __name__ == "__main__": raise SystemExit(main())
