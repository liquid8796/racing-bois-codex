"""Distribution failure tests. Fixture bytes are not Unity or playable media."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_publish import audit


class DistributionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.entries = []
        for identity in ["actors"] + [f"route-{i}" for i in range(5)] + [f"score-{i}" for i in range(25)]:
            kind = "actors" if identity == "actors" else "route" if identity.startswith("route-") else "music"
            data = (b"OggS" if kind == "music" else b"UnityFixture") + identity.encode()
            sha = hashlib.sha256(data).hexdigest()
            url = identity + "-" + sha + (".ogg" if kind == "music" else ".bundle")
            (self.root / url).write_bytes(data)
            self.entries.append({"id": identity, "kind": kind, "url": url, "sha256": sha,
                                 "bytes": len(data), "asset": "assets/content.asset",
                                 "courseIndex": int(identity[-1]) if kind == "route" else -1})
        self.manifest = {"schema": 1, "contentHash": "test-content", "actorsId": "actors", "bundles": self.entries}
        self.save()

    def tearDown(self):
        self.temporary.cleanup()

    def save(self):
        (self.root / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_exact_distribution_accepts(self):
        _, rows = audit(self.root, "test-content")
        self.assertEqual(len(rows), 31)

    def test_same_length_corruption_rejects(self):
        path = self.root / self.entries[0]["url"]
        data = bytearray(path.read_bytes())
        data[2] ^= 1
        path.write_bytes(data)
        with self.assertRaises(ValueError):
            audit(self.root)

    def test_truncated_bundle_rejects(self):
        path = self.root / self.entries[0]["url"]
        path.write_bytes(path.read_bytes()[:-1])
        with self.assertRaises(ValueError):
            audit(self.root)

    def test_cross_version_rejects(self):
        with self.assertRaises(ValueError):
            audit(self.root, "other-content")

    def test_manifest_traversal_rejects(self):
        self.entries[0]["url"] = "../" + self.entries[0]["url"]
        self.save()
        with self.assertRaises(ValueError):
            audit(self.root)

    def test_duplicate_id_rejects(self):
        self.entries[-1]["id"] = self.entries[-2]["id"]
        self.save()
        with self.assertRaises(ValueError):
            audit(self.root)

    def test_route_identity_rejects(self):
        self.entries[2]["courseIndex"] = 4
        self.save()
        with self.assertRaises(ValueError):
            audit(self.root)


if __name__ == "__main__":
    unittest.main()
