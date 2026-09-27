# Atomic native-import receipt repair

The retained `import-b89d27372abd44b6a0d80e4528ec1c70.json` contains a real
contradiction: `passed=true` alongside an IOException reporting Win32 IO1224 on
`import-latest.json`. The file is preserved unchanged. The import completed its
technical checks, set success, then failed while truncating a mapped latest file;
its catch added failure text without clearing success. Existing consumers trusted
the boolean and could accept that contradictory artifact.

The small shared writer now writes/flushed UTF8 to a unique sibling temporary,
then atomically replaces or moves the complete file. It never opens the destination
for truncation. A reader retaining the old mapped inode can finish with old bytes
while new readers see the complete new receipt. An exclusive Windows sharing lock
can still reject replacement; that case retains the old file and removes only the
writer's own temporary rather than falling back to destructive truncation.

Import and validation catches explicitly set `passed=false`. Native validation,
pinned promotion validation and the pure promotion gate require both success bits
**and empty failure text**. Whitespace is not an empty failure. Source/material/rig
checks and acceptance requirements remain unchanged.

Staged controls pass:

- Seven real filesystem/status controls, including an open memory-mapped reader,
  an exclusive sharing rejection, a directory collision and direct rejection of
  the retained contradictory native receipt without changing it.
- Forty-two promotion contract controls, including a nominal successful native
  receipt carrying real failure text and a whitespace failure.
- Installed Unity assembly preflight with zero warnings/errors.

These are managed/file controls, not a new Unity import or visual acceptance.
Root first checkpointed the exact prior native05 source as `edf57f7`, then
authorized this source repair. `handoff.json` preserves the before/candidate/meta
hashes; `install.py --install` checks all paths before replacing only the five
reviewed sources. Root owns refresh, source re-attestation and fresh native import.

Fresh native verification subsequently completed: Unity 6000.5.7f1 imported
Apex R5 at `2026-09-27T19:10:33.6423771Z`, recorded in
[`import-49b27062373a4591beb759a141fe12cc.json`](../../../../docs/p08/golden/unity/import-49b27062373a4591beb759a141fe12cc.json).
It has `passed=true`, `sourceBindingPassed=true`, an empty `failure`, and source
fingerprint `e01be298512e3267815a41f5f8f815074403325bb3132dadf49811d5dd8d4c23`.
Root also re-attested all three consumed assemblies. This is fresh native import
and source-binding evidence for this revision; the subsequent player build and
visual acceptance remain separate gates. The historical contradictory receipt
is unchanged.
