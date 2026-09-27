"""Generated contract fixtures; never actual Unity build acceptance."""
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_desktop as candidate



def aggregate(rows):
    return hashlib.sha256("\n".join(row["path"] + " " + row["sha256"] for row in rows).encode()).hexdigest()


class DependencyReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.rows = []
        self.names = candidate.UNITY_DEPENDENCY_ROOTS + [
            "Assets/RacingBois/Materials/Test.mat", "Assets/RacingBois/Prefabs/Test.prefab",
            "Assets/RacingBois/UI/Fonts/Test.ttf", "Assets/RacingBois/Art/Test.png"]
        for name in self.names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"contract fixture: " + name.encode())
            self.rows.append({"path": name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        self.rows.sort(key=lambda row: row["path"])
        all_rows = {row["path"]: row for row in self.rows}
        for name in candidate.SOURCE_SETTINGS:
            if name not in all_rows:
                path = self.root / name;path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'{"dependencies":{}}' if name == "Packages/packages-lock.json" else b"settings fixture")
                all_rows[name] = {"path": name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        source_rows = [all_rows[name] for name in sorted(all_rows)]
        self.receipt = {"unityDependencySchema": 2, "unityDependencyRoots": candidate.UNITY_DEPENDENCY_ROOTS,
                        "unityVersion": "6000.5.7f1", "unityPackages": [], "unityBuiltInDependencies": [],
                        "unityDependencies": [dict(row, assetPath=row["path"]) for row in self.rows],
                        "sourceFiles": copy.deepcopy(source_rows), "sourceFingerprint": aggregate(source_rows)}
        self.receipt["unityDependencyFingerprint"] = candidate.dependency_fingerprint(self.receipt)
        self.project = patch.object(candidate, "PROJECT", self.root)
        self.project.start()

    def tearDown(self):
        self.project.stop()
        self.temporary.cleanup()

    def reject(self, expression=None):
        with self.assertRaisesRegex(ValueError, expression or ".*"):
            candidate.audit_sources(self.receipt)

    def test_exact_engine_declared_closure_is_allowed(self):
        candidate.audit_sources(self.receipt)

    def test_not_a_blanket_assets_allowlist(self):
        name = "Assets/RacingBois/Art/Unlisted.png"
        path = self.root / name
        path.write_bytes(b"not listed")
        self.receipt["sourceFiles"].append({"path": name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        self.receipt["sourceFingerprint"] = aggregate(self.receipt["sourceFiles"])
        self.reject("union|order")

    def test_source_missing_declared_dependency_rejected(self):
        self.receipt["sourceFiles"].pop(0)
        self.receipt["sourceFingerprint"] = aggregate(self.receipt["sourceFiles"])
        self.reject("union")

    def test_source_dependency_record_mismatch_rejected(self):
        self.receipt["sourceFiles"][0]["bytes"] += 1
        self.reject("Current source differs")

    def test_changed_dependency_bytes_rejected(self):
        (self.root / self.names[2]).write_bytes(b"changed material")
        self.reject("Current source differs")

    def test_missing_dependency_rejected(self):
        (self.root / self.names[2]).unlink()
        self.reject("source file is missing")

    def test_missing_dependency_manifest_rejected(self):
        self.receipt.pop("unityDependencies")
        self.reject("closure is absent")

    def test_missing_required_root_rejected(self):
        self.receipt["unityDependencies"] = [row for row in self.receipt["unityDependencies"] if row["path"] != self.names[0]]
        self.receipt["unityDependencyFingerprint"] = candidate.dependency_fingerprint(self.receipt)
        self.reject("required roots")

    def test_other_roots_rejected(self):
        self.receipt["unityDependencyRoots"] = ["Assets/Other.unity"]
        self.reject("roots/schema")

    def test_wrong_schema_and_boolean_rejected(self):
        for value in [True, 2.0, 1, "2", None]:
            with self.subTest(value=value):
                self.receipt["unityDependencySchema"] = value
                self.reject("roots/schema")

    def test_changed_closure_aggregate_rejected(self):
        self.receipt["unityDependencyFingerprint"] = "0" * 64
        self.reject("dependency aggregate")

    def test_changed_source_aggregate_rejected(self):
        self.receipt["sourceFingerprint"] = "0" * 64
        self.reject("source aggregate")

    def test_duplicate_dependency_rejected(self):
        self.receipt["unityDependencies"].append(copy.deepcopy(self.receipt["unityDependencies"][0]))
        self.reject("duplicated")

    def test_case_alias_dependency_rejected(self):
        row = copy.deepcopy(self.receipt["unityDependencies"][0]); row["path"] = row["path"].replace("Test", "TEST")
        self.receipt["unityDependencies"].append(row)
        self.reject("duplicated")

    def test_dependency_order_rejected(self):
        self.receipt["unityDependencies"].reverse()
        self.receipt["unityDependencyFingerprint"] = candidate.dependency_fingerprint(self.receipt)
        self.reject("closure order")

    def test_path_aliases_and_traversal_rejected(self):
        for name in ["../outside.png", "/Assets/a.png", "C:/Assets/a.png", "Assets//a.png", "Assets/./a.png",
                     "Assets/a.png ", "Assets/a.png.", "Assets/a.png:stream", "Assets/%2e%2e/a.png", "Assets\\a.png"]:
            with self.subTest(name=name):
                self.receipt["unityDependencies"][0]["path"] = name
                self.receipt["unityDependencies"][0]["assetPath"] = name
                self.reject("canonical")

    def test_nonunity_dependency_rejected(self):
        self.receipt["unityDependencies"][0]["assetPath"] = "_local/player.sqlite"
        self.reject("outside Unity logical roots")

    def test_boolean_size_rejected(self):
        self.receipt["unityDependencies"][0]["bytes"] = True
        self.reject("fingerprint")

    def test_extra_dependency_fields_rejected(self):
        self.receipt["unityDependencies"][0]["untrusted"] = True
        self.reject("row is invalid")

    def test_source_duplicate_case_rejected(self):
        row = copy.deepcopy(self.rows[0]);row["path"] = row["path"].replace("Test", "TEST")
        self.receipt["sourceFiles"].append(row)
        self.reject("duplicated")

    def test_same_byte_symlink_rejected(self):
        target = self.root / self.names[2]
        real = self.root / "retained-target"
        target.rename(real)
        try:
            os.symlink(real, target)
        except OSError as error:
            self.fail("Cannot execute required real symlink control: " + type(error).__name__)
        self.reject("symlink or junction")

    def add_virtual_package(self):
        name = "com.unity.fixture"
        resolved = "Library/PackageCache/" + name + "@123abc"
        files = {resolved + "/package.json": json.dumps({"name": name, "version": "17.5.0"}).encode(),
                 resolved + "/Runtime/Shader.shader": b"shader dependency fixture"}
        def row(path):
            file = self.root / path
            return {"path": path, "bytes": file.stat().st_size, "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
        for path, content in files.items():
            file = self.root / path;file.parent.mkdir(parents=True, exist_ok=True);file.write_bytes(content)
        package = {"name": name, "version": "17.5.0", "resolvedPath": resolved, "manifest": row(resolved + "/package.json")}
        self.receipt["unityPackages"] = [package]
        shader = row(resolved + "/Runtime/Shader.shader")
        self.receipt["unityDependencies"].append(dict(shader, assetPath="Packages/" + name + "/Runtime/Shader.shader"))
        self.receipt["unityDependencies"].sort(key=lambda value: value["assetPath"])
        lock_path = "Packages/packages-lock.json"
        (self.root / lock_path).write_text(json.dumps({"dependencies": {name: {"source": "registry", "version": "17.5.0"}}}))
        self.receipt["sourceFiles"] = [value for value in self.receipt["sourceFiles"] if value["path"] != lock_path]
        self.receipt["sourceFiles"] += [row(lock_path), package["manifest"].copy(), shader]
        self.receipt["sourceFiles"].sort(key=lambda value: value["path"])
        self.receipt["sourceFingerprint"] = aggregate(self.receipt["sourceFiles"])
        self.receipt["unityDependencyFingerprint"] = candidate.dependency_fingerprint(self.receipt)
        return package

    def test_virtual_package_resolves_exact_physical_file(self):
        self.add_virtual_package()
        self.assertFalse((self.root / "Packages/com.unity.fixture/Runtime/Shader.shader").exists())
        candidate.audit_sources(self.receipt)

    def test_unresolved_virtual_package_rejected(self):
        self.add_virtual_package();self.receipt["unityPackages"] = []
        self.reject("unresolved")

    def test_missing_virtual_package_file_rejected(self):
        package = self.add_virtual_package()
        (self.root / package["resolvedPath"] / "Runtime/Shader.shader").unlink()
        self.reject("missing")

    def test_package_mapping_cannot_admit_other_library_file(self):
        self.add_virtual_package()
        self.receipt["unityDependencies"][-1]["path"] = "Library/Other/private.bin"
        self.reject("mapping differs")

    def test_package_root_cannot_admit_whole_cache(self):
        package = self.add_virtual_package();package["resolvedPath"] = "Library/PackageCache"
        self.reject("exact embedded/cache directory")

    def test_package_root_wrong_identity_rejected(self):
        package = self.add_virtual_package();package["resolvedPath"] = "Library/PackageCache/com.other.fixture@123abc"
        self.reject("exact embedded/cache directory")

    def test_changed_package_manifest_rejected(self):
        package = self.add_virtual_package()
        (self.root / package["manifest"]["path"]).write_text('{"name":"wrong","version":"17.5.0"}')
        self.reject("Current source differs")

    def test_package_version_identity_rejected(self):
        package = self.add_virtual_package();package["version"] = "99.0.0"
        self.reject("manifest/lock")

    def test_unused_package_record_rejected(self):
        self.add_virtual_package();self.receipt["unityDependencies"].pop()
        self.reject("Unused package")

    def test_explicit_builtin_is_version_bound(self):
        self.receipt["unityBuiltInDependencies"] = ["Resources/unity_builtin_extra"]
        self.receipt["unityDependencyFingerprint"] = candidate.dependency_fingerprint(self.receipt)
        candidate.audit_sources(self.receipt)
        self.receipt["unityVersion"] = "6000.5.8f1"
        self.reject("aggregate differs")

    def test_unknown_builtin_cannot_hide_missing_file(self):
        self.receipt["unityBuiltInDependencies"] = ["Library/MissingFile"]
        self.reject("Unknown or duplicate built-in")

    def test_source_nondictionary_rejected(self):
        self.receipt["sourceFiles"][0] = "not a file record"
        self.reject("file row is invalid")

    def test_source_order_gap_rejected(self):
        self.receipt["sourceFiles"].reverse()
        self.receipt["sourceFingerprint"] = aggregate(self.receipt["sourceFiles"])
        self.reject("snapshot order")

    def test_missing_authored_source_rejected(self):
        path = self.root / "Assets/RacingBois/Client/Unlisted.cs"
        path.parent.mkdir(parents=True, exist_ok=True);path.write_text("// unlisted source")
        self.reject("union")

    def test_source_noncanonical_path_rejected(self):
        self.receipt["sourceFiles"][0]["path"] = "Assets/../outside.cs"
        self.reject("canonical")


if __name__ == "__main__":
    unittest.main()
