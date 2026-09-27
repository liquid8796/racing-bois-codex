"""Generated archive fixtures prove packaging contracts, never native acceptance."""
import copy
import hashlib
import json
import os
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

import package_desktop_candidate as candidate


class CandidateArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.player = self.root / "player"
        self.player.mkdir()
        for name, data in [("RacingBois.exe", b"explicit synthetic executable fixture"),
                           ("RacingBois_Data/StreamingAssets/Content/fixture.bundle", b"fixture content"),
                           ("lower.txt", b"lower"), ("Upper.txt", b"upper")]:
            path = self.player / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.rows = candidate.tree_rows(self.player)
        self.build = {"passed": True, "sourceBindingPassed": True, "result": "Succeeded",
                      "target": "StandaloneWindows64", "scriptingBackend": "Mono2x", "errors": 0,
                      "contentHash": "fixture-only", "sourceFingerprint": "a" * 64, "playerFiles": self.rows}
        self.raw_build = candidate.json_bytes(self.build)
        self.manifest = {"schema": 1, "kind": "windows-player-candidate", "releaseAccepted": False,
                         "contentHash": "fixture-only", "sourceFingerprint": "a" * 64,
                         "buildReceiptSha256": hashlib.sha256(self.raw_build).hexdigest(),
                         "packagingTools": {name: "b" * 64 for name in candidate.TOOL_PATHS}, "files": self.rows}
        self.archive = self.root / "candidate.zip"

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        candidate.write_archive(self.archive, self.player, self.rows, self.raw_build, self.manifest)

    def verify(self):
        return candidate.verify_archive(self.archive, candidate.digest(self.archive))

    def rewrite(self, transform):
        with zipfile.ZipFile(self.archive) as source:
            entries = [(info, source.read(info)) for info in source.infolist()]
        other = self.root / "rewritten.zip"
        with zipfile.ZipFile(other, "x") as output:
            for info, data in transform(entries):
                output.writestr(info, data)
        self.archive = other

    def test_exact_fixture_bytes_and_explicit_unaccepted_scope(self):
        self.write()
        result = self.verify()
        self.assertEqual(len(self.rows), result["files"])
        self.assertTrue(result["archiveIntegrityPassed"])
        self.assertFalse(result["releaseAccepted"])
        with zipfile.ZipFile(self.archive) as archive:
            for row in self.rows:
                self.assertEqual((self.player / row["path"]).read_bytes(), archive.read(candidate.PLAYER_PREFIX + row["path"]))

    def test_mtime_and_permissions_do_not_change_archive_bytes(self):
        self.write()
        first = self.archive.read_bytes()
        for path in self.player.rglob("*"):
            if path.is_file():
                os.utime(path, (1234567890, 1234567890))
                path.chmod(stat.S_IREAD | stat.S_IWRITE)
        self.archive = self.root / "second.zip"
        self.write()
        self.assertEqual(first, self.archive.read_bytes())

    def test_existing_archive_never_overwritten(self):
        self.archive.write_bytes(b"preserved prior bytes")
        with self.assertRaises(FileExistsError):
            self.write()
        self.assertEqual(b"preserved prior bytes", self.archive.read_bytes())

    def test_changed_player_rejected_before_archive_creation(self):
        (self.player / "RacingBois.exe").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "changed before"):
            self.write()
        self.assertFalse(self.archive.exists())

    def test_added_player_file_rejected(self):
        (self.player / "new.dat").write_bytes(b"unexpected")
        with self.assertRaises(ValueError):
            self.write()

    def test_missing_player_file_rejected(self):
        (self.player / "RacingBois.exe").unlink()
        with self.assertRaises(ValueError):
            self.write()

    def test_external_digest_required_and_checked(self):
        self.write()
        for digest in [None, "", "b" * 64, "A" * 64]:
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                candidate.verify_archive(self.archive, digest)

    def test_altered_player_payload_rejected_with_updated_outer_digest(self):
        self.write()
        self.rewrite(lambda entries: [(info, data + b"altered" if info.filename.endswith("RacingBois.exe") else data) for info, data in entries])
        with self.assertRaisesRegex(ValueError, "size differs"):
            self.verify()

    def test_same_size_payload_corruption_rejected(self):
        self.write()
        self.rewrite(lambda entries: [(info, b"X" * len(data) if info.filename.endswith("RacingBois.exe") else data) for info, data in entries])
        with self.assertRaisesRegex(ValueError, "hash differs"):
            self.verify()

    def test_unregistered_archive_entry_rejected(self):
        self.write()
        self.rewrite(lambda entries: entries + [(candidate.zip_info("unexpected.txt"), b"unexpected")])
        with self.assertRaisesRegex(ValueError, "file set/order"):
            self.verify()

    def test_archive_case_alias_rejected(self):
        self.write()
        self.rewrite(lambda entries: entries + [(candidate.zip_info("racingbois-windows/racingbois.exe"), b"alias")])
        with self.assertRaisesRegex(ValueError, "case-colliding"):
            self.verify()

    def test_archive_symlink_metadata_rejected(self):
        self.write()
        def symlink(entries):
            info = copy.copy(entries[0][0])
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            return [(info, entries[0][1])] + entries[1:]
        self.rewrite(symlink)
        with self.assertRaisesRegex(ValueError, "entry type"):
            self.verify()

    def test_portable_windows_path_validation(self):
        for name in ["../a", "/absolute", "C:/absolute", "a\\b", "a//b", "a/./b", "a:stream", "CON.txt", "a/LPT1", "a./b", "a /b", " a", "a\x00b", "a?b"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                candidate.canonical_path(name)
        candidate.canonical_path("RacingBois_Data/Managed/Assembly-CSharp.dll")

    def test_actual_filesystem_symlink_rejected(self):
        target = self.root / "outside.txt"
        target.write_bytes(b"outside fixture")
        link = self.player / "linked.txt"
        try:
            link.symlink_to(target)
        except OSError as error:
            self.skipTest("Filesystem does not permit fixture symlinks: " + str(error))
        with self.assertRaisesRegex(ValueError, "symlink"):
            candidate.tree_rows(self.player)

    def test_source_binding_failure_not_promoted_by_archive(self):
        self.build["sourceBindingPassed"] = False
        self.raw_build = candidate.json_bytes(self.build)
        self.manifest["buildReceiptSha256"] = hashlib.sha256(self.raw_build).hexdigest()
        self.write()
        with self.assertRaisesRegex(ValueError, "Unity receipt/player binding"):
            self.verify()

    def test_release_accepted_bit_cannot_be_injected(self):
        self.manifest["releaseAccepted"] = True
        self.write()
        with self.assertRaisesRegex(ValueError, "candidate manifest"):
            self.verify()

    def test_build_player_list_mismatch_rejected(self):
        self.build["playerFiles"] = self.rows[:-1]
        self.raw_build = candidate.json_bytes(self.build)
        self.manifest["buildReceiptSha256"] = hashlib.sha256(self.raw_build).hexdigest()
        self.write()
        with self.assertRaisesRegex(ValueError, "Unity receipt/player binding"):
            self.verify()

    def test_receipt_content_identity_mismatch_rejected(self):
        self.build["contentHash"] = "different-fixture"
        self.raw_build = candidate.json_bytes(self.build)
        self.manifest["buildReceiptSha256"] = hashlib.sha256(self.raw_build).hexdigest()
        self.write()
        with self.assertRaisesRegex(ValueError, "Unity receipt/player binding"):
            self.verify()

    def test_build_receipt_byte_tampering_rejected(self):
        self.write()
        self.rewrite(lambda entries: [(info, data + b" " if info.filename == candidate.BUILD_RECEIPT else data) for info, data in entries])
        with self.assertRaisesRegex(ValueError, "Unity receipt bytes"):
            self.verify()

    def test_package_command_cannot_bypass_production_auditor(self):
        # Present, internally self-consistent fabricated receipt/player files
        # still lack actual engine dependencies. The real source auditor rejects
        # them before the command may create an archive. No audit is mocked.
        with tempfile.TemporaryDirectory(prefix="candidate-fixture-", dir=candidate.PROJECT / "Build") as temporary:
            fixture = Path(temporary)
            player = fixture / "player"
            player.mkdir()
            (player / "RacingBois.exe").write_bytes(b"explicit synthetic fixture")
            build = dict(self.build, output=player.relative_to(candidate.PROJECT).as_posix(),
                         schema=1, playerFiles=candidate.tree_rows(player))
            receipt = fixture / "build.json"
            receipt.write_bytes(candidate.json_bytes(build))
            archive = candidate.PROJECT / "Build/Packages" / (fixture.name + ".zip")
            with self.assertRaisesRegex(ValueError, "dependency roots/schema"):
                candidate.package_candidate(player, receipt, "fixture-only", archive)
            self.assertFalse(archive.exists())


if __name__ == "__main__":
    unittest.main()
