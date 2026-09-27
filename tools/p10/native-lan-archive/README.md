# Verify a transferred native LAN candidate

The native LAN publisher already checked a newly written ZIP against its local package directory. The launcher checked files after extraction. `verify_native_lan_archive.py` closes the transfer-verification gap: it checks an archive directly against a separately selected SHA256, without extracting or executing anything.

```powershell
python tools/p10/verify_native_lan_archive.py --archive Build/Packages/RacingBois-NativeLan-20260927T161958Z.zip --expected-sha256 e38decb99a8a78798331098f6d22027a478ceb5c0500c9e349be5e039420cbfd --expected-protocol 6 --expected-content-hash p08-C655ECB89DF77CFD
python -m unittest discover -s tools/p10 -p test_verify_native_lan_archive.py -v
```

Select the external digest from the intended candidate's publication receipt. The archive's own manifest is not a substitute for that trust anchor. The optional protocol/content arguments reject a package different from the explicitly selected identities; they do not discover a Windows player's protocol automatically. `--receipt <new-path.json>` writes a new verification record and refuses an existing path.

The verifier checks the exact native-LAN root/file set, per-file hashes and lengths, offline realm/candidate identity, canonical Windows paths, deterministic ZIP metadata, x64 PE32+ headers and self-contained runtime configuration. It rejects path traversal, case aliases, file/directory prefix collisions, links, duplicate JSON keys, unexpected payloads and private realm/key/source files. The archive digest is checked before and after reading.

Twenty generated-fixture controls passed. The preserved real `20260927T161958Z` archive also passed with 361 archive entries / 360 payload files and 112,981,068 bytes; see [the fresh read-only receipt](../../../docs/p10/native-lan/archive-verification-20260928.json). No existing archive, publication receipt or packaging tool was changed.

This establishes transferred archive integrity and its declared compatibility identities. It does not establish current-source freshness, final release acceptance, actual Windows-player/host pairing, physical LAN, graphics/input/performance or geographic gameplay. Those gates remain separate. The full Windows player build is still unavailable pending its own content/runtime acceptance, and its current archive schema does not yet independently expose a paired-host protocol identity.
