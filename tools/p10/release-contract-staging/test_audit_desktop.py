"""Negative distribution-contract tests; generated fixtures are never runtime acceptance."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audit_desktop import dependency_fingerprint, SOURCE_SETTINGS, UNITY_DEPENDENCY_ROOTS, PROJECT, audit_pack, audit_player, audit_sources, pe_machine, validate_config


class DesktopDistributionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.installed = self.root / "RacingBois_Data/StreamingAssets"
        self.content = self.installed / "Content"
        self.content.mkdir(parents=True)
        entries = []
        for index in range(31):
            kind = "actors" if index == 0 else "route" if index < 6 else "music"
            identity = "actors" if index == 0 else f"route-{index - 1}" if index < 6 else f"music-{index}"
            payload = (b"OggS" if kind == "music" else b"bundle-fixture") + identity.encode()
            sha = hashlib.sha256(payload).hexdigest()
            url = ("music/" if kind == "music" else "") + identity + "-" + sha + (".ogg" if kind == "music" else ".bundle")
            target = self.content / url
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(payload)
            entries.append({"id": identity, "kind": kind, "url": url, "sha256": sha, "bytes": len(payload), "crc": 123,
                            "asset": "" if kind == "music" else "assets/fixture.asset", "courseIndex": index - 1 if kind == "route" else -1})
        self.manifest = {"schema": 1, "buildTarget": "StandaloneWindows64", "contentHash": "fixture-gameplay", "actorsId": "actors", "bundles": entries}
        self.save_manifest()
        self.config = {"schema": 1, "connectionMode": "lan", "backendWebSocketUrl": "ws://127.0.0.1:7777/multiplayer", "contentBaseUrl": ""}
        self.save_config()

    def tearDown(self):
        self.temporary.cleanup()

    def save_manifest(self):
        (self.content / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def save_config(self):
        (self.installed / "RacingBois.runtime.json").write_text(json.dumps(self.config), encoding="utf-8")

    def test_complete_offline_catalog(self):
        _, rows = audit_pack(self.content, "fixture-gameplay")
        self.assertEqual(32, len(rows))
        self.assertEqual("installed", validate_config(self.installed / "RacingBois.runtime.json")["contentSource"])

    def test_wrong_platform_rejected(self):
        self.manifest["buildTarget"] = "WebGL"
        self.save_manifest()
        with self.assertRaises(ValueError):
            audit_pack(self.content, "fixture-gameplay")

    def test_wrong_gameplay_version_rejected(self):
        with self.assertRaises(ValueError):
            audit_pack(self.content, "different-gameplay")

    def test_corrupt_or_truncated_content_rejected(self):
        path = self.content / self.manifest["bundles"][0]["url"]
        path.write_bytes(path.read_bytes()[:-1])
        with self.assertRaises(ValueError):
            audit_pack(self.content, "fixture-gameplay")

    def test_missing_music_rejected(self):
        (self.content / self.manifest["bundles"][-1]["url"]).unlink()
        with self.assertRaises(FileNotFoundError):
            audit_pack(self.content, "fixture-gameplay")

    def test_unregistered_master_rejected(self):
        (self.content / "master.wav").write_bytes(b"not-shippable")
        with self.assertRaises(ValueError):
            audit_pack(self.content, "fixture-gameplay")

    def test_path_escape_rejected(self):
        self.manifest["bundles"][0]["url"] = "../outside.bundle"
        self.save_manifest()
        with self.assertRaises(ValueError):
            audit_pack(self.content, "fixture-gameplay")

    def test_private_config_field_rejected(self):
        self.config["password"] = "fixture-only"
        self.save_config()
        with self.assertRaises(ValueError):
            validate_config(self.installed / "RacingBois.runtime.json")

    def test_online_requires_wss(self):
        self.config["connectionMode"] = "online"
        self.save_config()
        with self.assertRaises(ValueError):
            validate_config(self.installed / "RacingBois.runtime.json")

    def test_userinfo_and_nonpublic_content_rejected(self):
        self.config["backendWebSocketUrl"] = "wss://fixture:fixture@example.invalid/multiplayer"
        self.save_config()
        with self.assertRaises(ValueError):
            validate_config(self.installed / "RacingBois.runtime.json")
        self.config["backendWebSocketUrl"] = "ws://127.0.0.1:7777/multiplayer"
        self.config["contentBaseUrl"] = "file:///C:/fixture/"
        self.save_config()
        with self.assertRaises(ValueError):
            validate_config(self.installed / "RacingBois.runtime.json")

    @staticmethod
    def pe_fixture():
        data = bytearray(128)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 64)
        data[64:68] = b"PE\0\0"
        struct.pack_into("<H", data, 68, 0x8664)
        struct.pack_into("<H", data, 88, 0x20B)
        return data

    def test_pe_x86_rejected(self):
        path = self.root / "fixture.exe"
        data = self.pe_fixture()
        path.write_bytes(data)
        self.assertEqual("AMD64 / PE32+", pe_machine(path))
        struct.pack_into("<H", data, 68, 0x14C)
        path.write_bytes(data)
        with self.assertRaises(ValueError):
            pe_machine(path)

    def test_truncated_pe_rejected(self):
        path = self.root / "truncated.exe"
        path.write_bytes(b"MZ")
        with self.assertRaises(ValueError):
            pe_machine(path)

    def test_source_snapshot_mutation_rejected(self):
        names = set(UNITY_DEPENDENCY_ROOTS) | SOURCE_SETTINGS | {"Assets/RacingBois/Client/Fixture.cs"}
        rows = []
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'{"dependencies":{}}' if name == "Packages/packages-lock.json" else b"source fixture: " + name.encode())
            rows.append({"path": name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        rows.sort(key=lambda row: row["path"])
        dependencies = [dict(row, assetPath=row["path"]) for row in rows if row["path"] in UNITY_DEPENDENCY_ROOTS]
        aggregate = lambda records: hashlib.sha256("\n".join(row["path"] + " " + row["sha256"] for row in records).encode()).hexdigest()
        receipt = {"sourceFiles": rows, "sourceFingerprint": aggregate(rows), "unityDependencySchema": 2,
                   "unityVersion": "6000.5.7f1", "unityDependencyRoots": UNITY_DEPENDENCY_ROOTS,
                   "unityDependencies": dependencies, "unityPackages": [], "unityBuiltInDependencies": []}
        receipt["unityDependencyFingerprint"] = dependency_fingerprint(receipt)
        with patch("audit_desktop.PROJECT", self.root):
            audit_sources(receipt)
            receipt["sourceFiles"][-1]["sha256"] = "b" * 64
            with self.assertRaises(ValueError):
                audit_sources(receipt)


    def test_actual_receipt_and_all_player_bytes_bound(self):
        for name in ("RacingBois.exe", "UnityPlayer.dll"):
            (self.root / name).write_bytes(self.pe_fixture())
        for relative in ("RacingBois_Data/Managed/RacingBois.Client.Bootstrap.dll", "MonoBleedingEdge/EmbedRuntime/mono-2.0-bdwgc.dll"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"managed-fixture")
        rows = [{"path": path.relative_to(self.root).as_posix(), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in self.root.rglob("*") if path.is_file()]
        receipt = {"schema": 1, "passed": True, "sourceBindingPassed": True, "result": "Succeeded", "target": "StandaloneWindows64", "scriptingBackend": "Mono2x",
                   "contentHash": "fixture-gameplay", "sourceFingerprint": "a" * 64, "errors": 0, "playerFiles": rows, "output": str(self.root),
                   "manifestSha256": hashlib.sha256((self.content / "manifest.json").read_bytes()).hexdigest()}
        receipt_path = self.root.parent / (self.root.name + "-receipt.json")
        try:
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertTrue(audit_player(self.root, receipt_path, "fixture-gameplay", verify_source=False)["passed"])
            self.config["contentBaseUrl"] = "https://example.invalid/Content/"
            self.save_config()
            with self.assertRaisesRegex(ValueError, "resolve installed content"):
                audit_player(self.root, receipt_path, "fixture-gameplay", verify_source=False)
            self.config["contentBaseUrl"] = ""
            self.save_config()
            (self.root / "UnityPlayer.dll").write_bytes(self.pe_fixture() + b"modified")
            with self.assertRaises(ValueError):
                audit_player(self.root, receipt_path, "fixture-gameplay", verify_source=False)
        finally:
            receipt_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
