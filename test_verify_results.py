"""Regression checks for malformed or internally inconsistent offline evidence."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import verify_results as verifier

ROOT = Path(__file__).resolve().parent


class EvidenceVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable, str(ROOT / "boundary_probe.py"),
                            "--participant-id", "regression", "--out", directory],
                           check=True, capture_output=True, text=True)
            cls.baseline = {name: json.loads((Path(directory) / name).read_text(encoding="utf-8"))
                            for name in verifier.FILES}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.data = copy.deepcopy(self.baseline)

    def write(self):
        for name, value in self.data.items():
            (self.folder / name).write_text(json.dumps(value), encoding="utf-8")

    def assert_rejected(self):
        self.write()
        self.assertTrue(verifier.verify(self.folder))

    def rehash_config(self):
        config = self.data["run_B.json"]["snapshots"][1]["declared_configuration"]
        config["config_sha256"] = verifier.digest(verifier.canonical(
            {key: value for key, value in config.items() if key != "config_sha256"}))

    def test_generated_fixture_and_cli_pass(self):
        self.write()
        self.assertEqual(verifier.verify(self.folder), [])
        result = subprocess.run([sys.executable, str(ROOT / "verify_results.py"), str(self.folder)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "PASS")

    def test_non_object_documents_fail_without_crashing(self):
        for name in verifier.FILES:
            for value in (None, [], "not an object"):
                with self.subTest(name=name, value=value):
                    self.data = copy.deepcopy(self.baseline)
                    self.data[name] = value
                    self.assert_rejected()
        self.data["run_A.json"] = None
        self.write()
        result = subprocess.run([sys.executable, str(ROOT / "verify_results.py"), str(self.folder)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "FAIL")
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_snapshot_shapes_fail(self):
        for value in (None, {}, [None] * 4, [{"boundary": "1_ingress"}] * 4):
            with self.subTest(value=value):
                self.data = copy.deepcopy(self.baseline)
                self.data["run_A.json"]["snapshots"] = value
                self.assert_rejected()

    def test_four_evidence_compartment_types_are_required(self):
        for key in ("declared_configuration", "observed_execution",
                    "inferred_participation", "unknowns"):
            with self.subTest(key=key):
                self.data = copy.deepcopy(self.baseline)
                self.data["run_A.json"]["snapshots"][0][key] = None
                self.assert_rejected()

    def test_missing_or_contradictory_execution_fails(self):
        self.data["run_A.json"]["snapshots"][2]["observed_execution"] = {}
        self.assert_rejected()
        for key, value in (("client_adapter_invoked", False),
                           ("client_adapter_returned", False),
                           ("execution_kind", "remote_model"),
                           ("tools_called", ["hidden_tool"]),
                           ("remote_inference", True)):
            with self.subTest(key=key):
                self.data = copy.deepcopy(self.baseline)
                self.data["run_A.json"]["snapshots"][2]["observed_execution"][key] = value
                self.assert_rejected()

    def test_second_configuration_change_fails_even_with_valid_hash(self):
        self.data["run_B.json"]["snapshots"][1]["declared_configuration"]["temperature"] = 1
        self.rehash_config()
        self.assert_rejected()

    def test_user_message_change_fails_even_with_valid_context_hash(self):
        assembly = self.data["run_B.json"]["snapshots"][1]["observed_execution"]
        assembly["actual_assembled_messages"][1]["content"] = "A different request"
        assembly["assembled_context_sha256"] = verifier.digest(
            verifier.canonical(assembly["actual_assembled_messages"]))
        self.assert_rejected()

    def test_wrong_egress_length_fails(self):
        self.data["run_A.json"]["snapshots"][3]["observed_execution"]["output_bytes_length"] = 99999
        self.assert_rejected()

    def test_missing_and_egress_mismatched_trace_ids_fail(self):
        self.data["run_A.json"]["trace_id"] = None
        self.assert_rejected()
        self.data = copy.deepcopy(self.baseline)
        egress = self.data["run_A.json"]["snapshots"][3]["observed_execution"]
        egress["output_body"]["trace_id"] = "another-interaction"
        output = verifier.canonical(egress["output_body"])
        egress["output_body_sha256"] = verifier.digest(output)
        egress["output_bytes_length"] = len(output)
        self.assert_rejected()

    def test_recorded_digest_mismatches_fail(self):
        for index, compartment, field in (
                (0, "observed_execution", "raw_body_sha256"),
                (1, "observed_execution", "assembled_context_sha256"),
                (1, "declared_configuration", "config_sha256"),
                (3, "observed_execution", "output_body_sha256")):
            with self.subTest(field=field):
                self.data = copy.deepcopy(self.baseline)
                self.data["run_A.json"]["snapshots"][index][compartment][field] = "0" * 64
                self.assert_rejected()

    def test_comparison_metadata_must_match_evidence(self):
        for key, value in (("client_adapter_kinds", []),
                           ("controlled_change", "model_route"),
                           ("request_sha256_same", 1)):
            with self.subTest(key=key):
                self.data = copy.deepcopy(self.baseline)
                self.data["comparison.json"][key] = value
                self.assert_rejected()

    def test_manifest_declarations_must_match_snapshots(self):
        self.data["run_manifest.json"]["model_route_declared"] = "different/route"
        self.assert_rejected()

    def test_missing_and_malformed_files_fail(self):
        self.write()
        (self.folder / "comparison.json").unlink()
        self.assertTrue(verifier.verify(self.folder))
        (self.folder / "comparison.json").write_text("{not json}", encoding="utf-8")
        self.assertTrue(verifier.verify(self.folder))


if __name__ == "__main__":
    unittest.main()
