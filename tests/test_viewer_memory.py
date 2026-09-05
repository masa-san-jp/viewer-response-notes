import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from viewer_memory import ViewerMemory, encoded, digest, key, POLICY
from viewer_contract import dedup_key
from export_signals import write_export

NOW = "2026-09-05T00:00:00Z"


class ViewerMemoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.store_root = self.root / "memory"; self.store_root.mkdir()
        self.code = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        gitdir = self.store_root / "objects.git"
        subprocess.run(["git", "init", "--bare", "-q", str(gitdir)], check=True)
        (self.store_root / "store.json").write_text(json.dumps({"owner": "viewer-response-notes", "creator": "creator-a", "collection": "viewer-a"}))
        tree = subprocess.check_output(["git", "--git-dir", str(gitdir), "mktree"], input=b"").decode().strip()
        commit = subprocess.check_output(["git", "--git-dir", str(gitdir), "-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid", "commit-tree", tree], input=b"synthetic setup").decode().strip()
        subprocess.run(["git", "--git-dir", str(gitdir), "update-ref", "refs/heads/knowledge", commit], check=True)
        self.memory = ViewerMemory(self.store_root, "creator-a", "viewer-a", self.code)

    def candidate(self, suffix="A", condition="conditions/a", passed=19):
        record = json.loads((ROOT / "tests/fixtures/viewer-response-records.jsonl").read_text().splitlines()[0])
        record.update(record_id="VRR-" + suffix, evidence_refs=["viewer-response:study-" + suffix], observed_at=NOW,
                      outcome_counts={"pass": passed, "fail": 20-passed, "unknown": 0})
        record["dedup_key"] = dedup_key(record)
        context = {"project_id": "project/synthetic", "work_revision": 1, "intended_experience_refs": ["experience/clarity"],
            "collection_method": "survey", "period_start": NOW, "period_end": NOW, "presentation_conditions_ref": condition,
            "source_identity": "source/" + suffix, "sample_set_ids": ["sample-set/" + suffix], "overlaps_sample_sets": [], "corrects_record_ids": []}
        payload = {"record": record, "context": context}
        artifact = {"contract_version": "artifact-record/v1", "record_id": record["record_id"], "revision": 1,
            "origin_instance_id": "instance-a", "creator_id": "creator-a", "owner_repository": "viewer-response-notes",
            "collection_id": "viewer-a", "kind": "viewer-response", "payload_schema": POLICY["contract_version"],
            "payload_ref": "", "content_sha256": digest(encoded(payload)), "sources": [], "derived_from": [],
            "epistemic_status": "observed", "lifecycle": "accepted", "applicability": {"work_id": record["work_id"], "presentation_conditions_ref": condition},
            "rights": {"knowledge_write": True, "redistribute": False}, "access_scope": "creator-private", "consent_ref": "consent/synthetic",
            "created_at": NOW, "reviewed_at": None, "valid_until": None,
            "producer": {"kind": "tool", "generator_version": POLICY["contract_version"], "code_commit": self.code, "run_id": "synthetic"},
            "supersedes": [], "invalidates": []}
        artifact["payload_ref"] = "records/payloads/" + key(artifact) + ".json"
        return {"artifact": artifact, "payload": payload}

    def rehash(self, candidate):
        candidate["artifact"]["content_sha256"] = digest(encoded(candidate["payload"]))

    def append(self, candidate, operation="one", **kwargs):
        return self.memory.append(candidate, self.memory.head(), operation, "synthetic", **kwargs)

    def scope(self, candidate):
        p = candidate["payload"]
        return {k: p["context"].get(k, p["record"].get(k)) for k in POLICY["scope_fields"]}

    def test_ac1_condition_separation_assessment_export_cli_and_git_reopen(self):
        a, b = self.candidate(), self.candidate("B", "conditions/b", 0)
        self.append(a); last = self.append(b, "two")
        reopened = ViewerMemory(self.store_root, "creator-a", "viewer-a", self.code)
        result = reopened.query(last["target_commit"], self.scope(a), at=NOW)
        other = reopened.query(last["target_commit"], self.scope(b), at=NOW)
        self.assertEqual("SUPPORTED", result["assessment"]["status"])
        self.assertEqual("COMMITTED", result["knowledge_status"])
        self.assertEqual("CONTRADICTED", other["assessment"]["status"])
        self.assertEqual(20, result["assessment"]["measured_sample_size"])
        query = self.root / "query.json"; output = self.root / "export.json"
        query.write_text(json.dumps({"store_root": str(self.store_root), "creator": "creator-a", "collection": "viewer-a", "code_commit": self.code,
            "knowledge_commit": last["target_commit"], "scope": self.scope(a), "at": NOW}))
        command = [sys.executable, str(ROOT / "tools/export_signals.py"), "--memory-query", str(query), "--output", str(output)]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(0, first.returncode, first.stdout + first.stderr)
        self.assertEqual(result, json.loads(output.read_text()))
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual("ALREADY_EXPORTED", second.stdout.strip())

    def test_ac2_duplicate_source_sample_overlap_external_counts_and_creator_fail_closed(self):
        a = self.candidate(); self.append(a)
        for mode in ("source", "samples", "declared-overlap", "external", "creator"):
            b = self.candidate("B")
            c = b["payload"]["context"]
            if mode == "source": c["source_identity"] = a["payload"]["context"]["source_identity"]
            if mode == "samples": c["sample_set_ids"] = a["payload"]["context"]["sample_set_ids"]
            if mode == "declared-overlap": c["overlaps_sample_sets"] = a["payload"]["context"]["sample_set_ids"]
            if mode == "external": b["payload"]["record"]["source_kind"] = "external"
            if mode == "creator": b["artifact"]["creator_id"] = "creator-b"
            self.rehash(b)
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.append(b, mode)
        with self.assertRaises(ValueError): ViewerMemory(self.store_root, "creator-b", "viewer-a", self.code)

    def test_ac3_append_correction_preserves_original_and_recalculates_active_assessment(self):
        a = self.candidate(); first = self.append(a)
        old_bytes = self.memory.read(first["target_commit"], a["artifact"]["payload_ref"])
        corrected = self.candidate("C", passed=0)
        corrected["payload"]["context"].update(source_identity="source/A", sample_set_ids=["sample-set/A"], corrects_record_ids=["VRR-A"])
        corrected["artifact"]["invalidates"] = [{k:a["artifact"][k] for k in ("origin_instance_id", "owner_repository", "record_id", "revision")}]
        self.rehash(corrected)
        with self.assertRaises(ValueError): self.append(corrected, "correction")
        second = self.append(corrected, "correction", correction_approval_ref="approval/synthetic-fixture")
        self.assertEqual(2, len(self.memory.candidates(second["target_commit"])))
        self.assertEqual(old_bytes, self.memory.read(second["target_commit"], a["artifact"]["payload_ref"]))
        self.assertEqual("SUPPORTED", self.memory.query(first["target_commit"], self.scope(a), at=NOW)["assessment"]["status"])
        active = self.memory.query(second["target_commit"], self.scope(a), at=NOW)
        self.assertEqual("CONTRADICTED", active["assessment"]["status"])
        self.assertEqual(["VRR-C"], active["source_record_ids"])

    def test_ac4_name_free_response_raw_secret_and_private_url_rejected(self):
        for field in ("sources", "derived_from", "invalidates", "supersedes"):
            candidate = self.candidate()
            candidate["artifact"][field] = [{"respondent_name": "Alice"}]
            with self.subTest(field=field), self.assertRaises(ValueError): self.append(candidate)
        candidate = self.candidate()
        candidate["artifact"]["invalidates"] = [{"origin_instance_id": "instance-a", "owner_repository": "viewer-response-notes", "record_id": "VRR-missing", "revision": 1}]
        with self.assertRaisesRegex(ValueError, "unresolved"): self.append(candidate)
        for field, value in (("respondent_name", "Synthetic Person"), ("free_response", "not allowed"), ("raw", "not allowed")):
            candidate = self.candidate(); candidate["payload"]["context"][field] = value; self.rehash(candidate)
            with self.assertRaises(ValueError): self.append(candidate)
        for value in ("https://user:password@example.test/private", "https://127.0.0.1/private", "viewer-response:token=synthetic-secret"):
            candidate = self.candidate(); candidate["payload"]["record"]["evidence_refs"] = [value]
            candidate["payload"]["record"]["dedup_key"] = dedup_key(candidate["payload"]["record"]); self.rehash(candidate)
            with self.assertRaises(ValueError): self.append(candidate)

    def test_ac5_empty_history_and_zero_samples_are_unknown_not_negative_evidence(self):
        candidate = self.candidate(); parent = self.memory.head()
        empty = self.memory.query(parent, self.scope(candidate), at=NOW)
        self.assertEqual("NO_NEW_EVIDENCE", empty["knowledge_status"])
        self.assertEqual("UNKNOWN", empty["assessment"]["status"])
        candidate["payload"]["record"].update(sample_size=0, outcome_counts={"pass": 0, "fail": 0, "unknown": 0})
        candidate["payload"]["context"]["sample_set_ids"] = []; self.rehash(candidate)
        self.assertEqual("NO_NEW_EVIDENCE", self.append(candidate)["status"])
        self.assertEqual(parent, self.memory.head())

    def test_replay_stale_parent_and_export_publication_race_preserve_success(self):
        candidate = self.candidate(); parent = self.memory.head(); receipt = self.append(candidate)
        self.assertEqual(receipt["target_commit"], self.memory.append(candidate, parent, "one", "synthetic")["target_commit"])
        with self.assertRaises(ValueError): self.memory.append(self.candidate("B"), parent, "two", "synthetic")
        output = self.root / "raced.json"
        def competing_writer(source, target):
            Path(target).write_text("other writer")
            raise FileExistsError()
        with patch("export_signals.os.link", side_effect=competing_writer), self.assertRaises(ValueError):
            write_export({"synthetic": True}, output)
        self.assertEqual("other writer", output.read_text())


if __name__ == "__main__": unittest.main()
