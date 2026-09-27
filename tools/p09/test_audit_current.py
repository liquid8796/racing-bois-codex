"""Negative controls for deployment evidence and current source freshness."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("audit_current", Path(__file__).with_name("audit-current.py"))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditControls(unittest.TestCase):
    def setUp(self):
        self.manifest = {"releaseId": "f", "source": {"sha256": "runtime"},
                         "testSource": {"sha256": "tests"}, "files": [{}], "protocolVersion": 6}
        self.package = {"manifestSha256": "manifest"}
        self.local = {"source": {"matches": True}, "sourceStableDuringAudit": True}
        self.remote = {"releaseId": "f", "sourceSha256": "runtime", "testSourceSha256": "tests",
                       "releaseManifestSha256": "manifest", "verifiedFiles": 1,
                       "health": {"protocolVersion": 3, "multiplayer": {"protocolVersion": 6, "persistenceFailures": 0}},
                       "monitor": {"status": "passed", "ageSeconds": 30, "issues": []},
                       "backup": {"status": "passed", "ageSeconds": 3600}}
        self.routes = [{"path": "/ready", "statusCode": 200, "body": {"status": "ready", "protocolVersion": 6}},
                       {"path": "/health/", "statusCode": 404}]

    def failures(self):
        return audit.assess(self.manifest, self.package, self.local, self.remote, self.routes)

    def test_current_multiplayer_protocol_is_used_instead_of_legacy_health_version(self):
        self.assertEqual([], self.failures())

    def test_added_changed_and_removed_sources_are_all_reported(self):
        old = {"sha256": "old", "files": [{"path": "changed.cs", "sha256": "a"}, {"path": "removed.cs", "sha256": "b"}]}
        new = {"sha256": "new", "files": [{"path": "changed.cs", "sha256": "c"}, {"path": "added.cs", "sha256": "d"}]}
        result = audit.compare_sources(old, new)
        self.assertFalse(result["matches"])
        self.assertEqual(["added.cs", "changed.cs", "removed.cs"], [row["path"] for row in result["changes"]])

    def test_runtime_drift_cannot_be_a_pass(self):
        self.local["source"]["matches"] = False
        self.assertIn("deployed_runtime_source_differs_from_workspace", self.failures())

    def test_source_change_during_audit_cannot_be_a_pass(self):
        self.local["sourceStableDuringAudit"] = False
        self.assertIn("runtime_source_changed_during_audit", self.failures())

    def test_wrong_remote_manifest_cannot_be_a_pass(self):
        self.remote["releaseManifestSha256"] = "different"
        self.assertIn("active_manifest_mismatch", self.failures())

    def test_public_readiness_does_not_hide_private_route_exposure(self):
        self.routes[1]["statusCode"] = 200
        self.assertIn("private_route_is_public", self.failures())

    def test_wrong_public_protocol_cannot_be_a_pass(self):
        self.routes[0]["body"]["protocolVersion"] = 5
        self.assertIn("public_protocol_mismatch", self.failures())

    def test_wrong_multiplayer_protocol_cannot_be_a_pass(self):
        self.remote["health"]["multiplayer"]["protocolVersion"] = 5
        self.assertIn("private_multiplayer_protocol_mismatch", self.failures())

    def test_persistence_failures_cannot_be_a_pass(self):
        self.remote["health"]["multiplayer"]["persistenceFailures"] = 1
        self.assertIn("persistence_failure_counter_nonzero", self.failures())

    def test_old_or_future_operational_receipts_cannot_be_a_pass(self):
        for name, ages in (("monitor", (-1, 601)), ("backup", (-1, 7201))):
            for age in ages:
                with self.subTest(name=name, age=age):
                    remote = copy.deepcopy(self.remote)
                    remote[name]["ageSeconds"] = age
                    self.assertIn(name + "_not_fresh_and_passed", audit.assess(self.manifest, self.package, self.local, remote, self.routes))

    def test_monitor_issue_cannot_be_hidden_behind_passed_status(self):
        self.remote["monitor"]["issues"] = ["disk_free_below_2GiB"]
        self.assertIn("monitor_reports_issues", self.failures())


if __name__ == "__main__":
    unittest.main()
