# Windows candidate archive contract

`tools/p10/package_desktop_candidate.py` fills the native-player archive gap left
by the older Web-specific P07 packager. It creates an explicitly **unaccepted
candidate**, never a final release. No real P08 player archive has been created:
the current art/content and native runtime gates remain open.

The package command calls the existing desktop distribution auditor with source
verification enabled before and after writing. The selected actual Unity build
receipt must bind the native PE files, installed Windows content, source/settings
and engine dependency closure. Missing content, a fabricated receipt lacking that
closure or a failed build is rejected before packaging. The packaging tool and
both imported auditors are hashed before/after as well. A consistent receipt is
not proof that someone actually ran Unity; the operator must select the genuine
engine receipt.

The ZIP contains `RacingBois-Windows/` with exact player bytes, plus the original
Unity build receipt and a file manifest under `evidence/`. Each member is streamed
back and SHA256 checked after writing. The external `.candidate.json` receipt
records the archive digest, byte count and scope. The verifier requires that
external digest when checking a transferred archive and never extracts it.
Both manifest and receipt force `releaseAccepted=false`.

Sorted entries, fixed timestamps, portable file permissions and ZIP_STORED make
the same input bytes reproduce the same archive bytes without depending on file
mtime or a compressor version. This costs disk/transfer size. Paths reject
traversal, Windows device names, alternate data streams, case aliases, links and
junctions. Existing archives/receipts are never overwritten. If a concurrent
input change makes verification fail, the attempted ZIP is retained without a
success receipt; use a new filename for the next attempt.

Run only after the actual desktop build exists, using its real content hash:

```powershell
python tools/p10/package_desktop_candidate.py package --player-root Build/Desktop-P08-CANDIDATE --build-receipt docs/p08/desktop/ACTUAL-BUILD.json --expected-content-hash ACTUAL-CONTENT-HASH --archive Build/Packages/RacingBois-Windows-CANDIDATE.zip
python tools/p10/package_desktop_candidate.py verify --archive Build/Packages/RacingBois-Windows-CANDIDATE.zip --expected-sha256 ACTUAL-ARCHIVE-SHA256
python -m unittest discover -s tools/p10 -p test_package_desktop_candidate.py -v
```

The generated-fixture tests cover repeatable bytes, real filesystem symlinks,
missing/added/changed files, overwrites, path aliases, corrupt ZIP payloads,
receipt/player mismatches and an attempted false release bit. A real invocation
of the production source auditor rejects the fabricated fixture's missing engine
dependency closure. These tests establish packaging behavior, not a native build.

A separate offline LAN host archive, matching protocol/content compatibility,
operator instructions, physical two-PC WAN-disconnected testing, native player
runtime/input/performance, hardware and regional client evidence remain required.
The archive cannot accept any of those gates or promote art/content.
