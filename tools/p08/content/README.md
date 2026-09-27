# P08 content ledger tools

From the repository root:

```powershell
python tools/p08/content/content_ledger.py --write
python tools/p08/content/content_ledger.py --check
python -m unittest discover -s tools/p08/content -p test_*.py
```

The builder uses `docs/p08/content/reference-baseline.json`, a checked-in metadata-only snapshot of P00/P01 research, and `production-mappings.json`, the explicit production registry. It writes deterministic JSON, CSV and Markdown. No extracted image, pixel buffer, sprite, sound, video, font or executable is copied by this tool.

`--check` validates current bound paths and hashes, category coverage, source-file coverage, source baseline totals, unique IDs, dependencies, concept presence for 3D entries, and whole-file source-copy detection in `Assets` and `ArtSource`. Its exit status means evidence integrity only. It deliberately prints `content_acceptance_passed: false` while any required row is pending or partial.

The acceptance command is stricter:

```powershell
python tools/p08/content/content_ledger.py --check --require-complete
```

This must exit 1 while required content remains unaccepted. Do not change pending flags merely to make this command pass. An accepted row needs actual replacement IDs, reviewed mapping evidence, real QA evidence, a build pack and no remaining work; referenced production assets must also be accepted. Hashes and JSON flags alone cannot prove visual quality or creative originality.

To recheck the supplied mod without modifying it:

```powershell
python tools/p08/content/content_ledger.py --write --source-root 'C:\Users\Liquid\Downloads\Unity\racing_bois_mod'
```

This checks the original 374 file paths, sizes and SHA-256 values against the frozen reference metadata. To deliberately refresh the metadata snapshot after re-running the original P00/P01 audit locally:

```powershell
python tools/p08/content/content_ledger.py --capture-reference
python tools/p08/content/content_ledger.py --write
```

The capture mode needs the gitignored local research JSON; ordinary build/check does not. Its `upstream_audits` hashes preserve provenance without packaging original media.

## Adding P08 production work

Add each actual production asset or explicitly shared set to `production-mappings.json` with a stable ID, `asset_kind`, exact output/source/concept/provenance/QA paths, authorship note, QA state and intended build pack. Declare shared rigs, chassis, atlases and animations in the note. A future path or a generated concept without a model is not a completed 3D production asset. Source art may be referenced before full acceptance if its status and remaining work remain explicit.

Add mappings using existing reference row IDs. Mapping updates cannot overwrite the immutable original category, path, count unit or evidence fields. One-to-many and many-to-one mapping is permitted where review supports it; never multiply counts for reused assets. Filename hints and approximate roles can be recorded as partial candidates, with uncertainty stated.

Then run `--write`, `--check` and the regression suite. Because ongoing work changes bound files, regenerate at a stable delivery checkpoint and validate again after any line-ending normalization or deliberate source change. The current user-edited `ArtSource/Weapons/RB_Club.blend` is read only by the ledger and remains untouched; its historical export QA is not promoted to proof of the later source edits.

Build archives are outside this tool's scan. Their source manifests, import/build receipts and runtime content integration must be validated separately before closing final P08 acceptance.
