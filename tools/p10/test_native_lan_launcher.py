"""Real PowerShell launcher contracts on synthetic files; no server is launched."""
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "tools/p10/native-lan/launch-native-lan.ps1"
REQUIRED = ["RacingBois.Server.Host.exe", "RacingBois.Server.Host.dll", "RacingBois.Server.Host.runtimeconfig.json",
            "coreclr.dll", "hostfxr.dll", "hostpolicy.dll", "System.Private.CoreLib.dll", "e_sqlite3.dll",
            "Microsoft.AspNetCore.Server.Kestrel.Core.dll", "launch-native-lan.ps1", "launch-native-lan.bat", "README.txt", "public/README.txt"]


class NativeLanLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.package = self.root / "package"
        self.data = self.root / "uncreated-private-realm"
        for name in REQUIRED:
            path = self.package / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"explicit synthetic fixture, never executable")
        shutil.copyfile(LAUNCHER, self.package / "launch-native-lan.ps1")
        self.runtime = {"runtimeOptions": {"includedFrameworks": [{"name": "Microsoft.NETCore.App", "version": "10.0.9"}]}}
        self.save_runtime()
        self.manifest = {"schema": 1, "kind": "native-lan-host-candidate", "runtime": "win-x64", "realmKind": "offline",
                         "releaseAccepted": False, "protocolVersion": 6, "contentHash": "fixture-only", "files": self.rows()}
        self.save_manifest()

    def tearDown(self):
        self.temporary.cleanup()

    def rows(self):
        return [{"path": path.relative_to(self.package).as_posix(), "bytes": path.stat().st_size,
                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in sorted(self.package.rglob("*")) if path.is_file() and path.name != "package-manifest.json"]

    def save_runtime(self):
        (self.package / "RacingBois.Server.Host.runtimeconfig.json").write_text(json.dumps(self.runtime), encoding="utf-8")

    def save_manifest(self):
        (self.package / "package-manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def run_launcher(self, *args, shell="powershell.exe"):
        return subprocess.run([shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.package / "launch-native-lan.ps1"), *map(str, args)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)

    def test_ps51_plan_is_offline_private_and_side_effect_free(self):
        result = self.run_launcher("-PlanOnly", "-LocalOnly", "-DataRoot", self.data)
        self.assertEqual(0, result.returncode, result.stdout)
        plan = json.loads(result.stdout)
        self.assertEqual("offline", plan["realmKind"])
        self.assertEqual("loopback", plan["bind"])
        self.assertIn("--RealmKind", plan["arguments"])
        self.assertFalse(plan["releaseAccepted"])
        self.assertFalse(self.data.exists())

    def test_ps7_verify_when_available(self):
        shell = shutil.which("pwsh")
        if not shell:
            self.skipTest("PowerShell 7 is not installed")
        result = self.run_launcher("-VerifyOnly", shell=shell)
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertTrue(json.loads(result.stdout)["verified"])

    def test_changed_file_rejected(self):
        (self.package / "coreclr.dll").write_bytes(b"changed fixture")
        result = self.run_launcher("-VerifyOnly")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing or changed", result.stdout)

    def test_extra_private_data_rejected(self):
        (self.package / "realm.sqlite3").write_bytes(b"synthetic private fixture")
        result = self.run_launcher("-VerifyOnly")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Unregistered file", result.stdout)

    def test_required_file_missing_from_manifest_rejected(self):
        (self.package / "e_sqlite3.dll").unlink()
        self.manifest["files"] = self.rows()
        self.save_manifest()
        result = self.run_launcher("-VerifyOnly")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Required native file absent", result.stdout)

    def test_duplicate_alias_manifest_rejected(self):
        self.manifest["files"].append(dict(self.manifest["files"][0], path=self.manifest["files"][0]["path"].upper()))
        self.save_manifest()
        result = self.run_launcher("-VerifyOnly")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unsafe or duplicate", result.stdout)

    def test_path_escape_rejected(self):
        self.manifest["files"][0]["path"] = "../outside.dat"
        self.save_manifest()
        result = self.run_launcher("-VerifyOnly")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unsafe or duplicate", result.stdout)

    def test_data_cannot_be_bundled_or_public(self):
        result = self.run_launcher("-PlanOnly", "-DataRoot", self.package / "public/private")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("outside the immutable package", result.stdout)
        self.assertFalse((self.package / "public/private").exists())

    def test_online_realm_manifest_rejected(self):
        self.manifest["realmKind"] = "online"
        self.save_manifest()
        result = self.run_launcher("-VerifyOnly")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("manifest is invalid", result.stdout)

    def test_external_runtime_rejected(self):
        self.runtime = {"runtimeOptions": {"framework": {"name": "Microsoft.NETCore.App", "version": "10.0.9"}}}
        self.save_runtime()
        self.manifest["files"] = self.rows()
        self.save_manifest()
        result = self.run_launcher("-VerifyOnly")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("external runtime", result.stdout)

    def test_actual_link_rejected(self):
        path = self.package / "coreclr.dll"
        path.unlink()
        outside = self.root / "outside.dll"
        outside.write_bytes(b"explicit synthetic fixture, never executable")
        try:
            path.symlink_to(outside)
        except OSError as error:
            self.skipTest("Filesystem does not permit fixture symlink: " + str(error))
        result = self.run_launcher("-VerifyOnly")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("links or junctions", result.stdout)


if __name__ == "__main__":
    unittest.main()
