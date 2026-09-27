# P01 asset/course research tools

Source remains read-only at `C:\Users\Liquid\Downloads\Unity\racing_bois_mod`.
All outputs are reference-only under `docs/p01/assets`, outside Unity `Assets`.
Never use extracted/re-encoded original content as Racing Bois production art.

Python 3.11+ with Pillow, mido 1.3.3 and ffmpeg on PATH is required. P00's
existing resource/DCL parsers and PE reader are reused without modification.
This run installed mido only into the ignored research cache; `validate.py`
also accepts a normal environment with mido installed.

```powershell
python -m pip install -r tools/p01/assets/requirements.txt
tools\p01\assets\run-all.bat
```

The wrapper stops on the first failure and preserves a nonzero exit code.
The first FAM decode takes longer; subsequent runs use content-addressed,
CRC-checked cache files. Source integrity validation reads all 374 originals.

Individual commands from repository root:

```powershell
python tools/p01/assets/decode_courses.py
python tools/p01/assets/decode_sprites.py
python tools/p01/assets/decode_media.py
python tools/p01/assets/complete_reference.py
python tools/p01/assets/close_rpth_legacy.py
python tools/p01/assets/unit_display.py
python tools/p01/assets/validate.py
```

- `decode_courses.py`: graph reconstruction, typed chunks, raw coefficients,
  family-stream events, JSON and DOT for all five courses.
- `decode_sprites.py`: all family/animation records, native LOD aliases,
  complete CANS action metadata, mip hashes, DAT frames and searchable atlas.
- `decode_media.py`: MIDS-to-SMF conversion, complete WAVE decode, AVI filmstrip
  catalog and conservative filename/address references.
- `complete_reference.py`: code evidence slices, course-to-FAM ledger,
  explicitly provisional cloud previews and DAT/RRFD discrepancy report.
- `close_rpth_legacy.py`: original RPTH function execution in Unicorn for every
  source sample in both directions, native node-boundary tests and complete
  legacy-slot reachability classification. Reuses the P01 logic emulator and its
  vendored Unicorn dependency; does not execute Windows imports or alter source.
- `unit_display.py`: exact native HUD mph/kmh, distance counter and25 course-menu
  length values, including threshold/negative fixtures and file/title mappings.
  This recovers display calibration; it does not establish physical meters.
- `validate.py`: valid and malformed parser checks, 6,161 CANS frame links,
  mido independent event/timing comparison, PNG byte roundtrip and source hashes.

Read `docs/p01/assets/REPORT.md` for closed structural gates versus open semantic
gates. A parser PASS does not certify 100% logic, all original render semantics,
or a production-ready Unity asset. Frame/variant counts are not model counts.
