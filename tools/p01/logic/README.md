# Native P01 research tools

Run from repository root with Python3.13:

```powershell
python -m pip install --target tools/p01/logic/vendor -r tools/p01/logic/requirements.txt
python tools/p01/logic/native_project.py
python tools/p01/logic/emulate_fixtures.py
python tools/p01/logic/bike_component_bench.py
```

All static/emulator scripts read source files only and write `docs/p01/logic`. The PE must match the pinned SHA-256 or the address-based tools stop. Prior P00 `vendor` is a fallback dependency location; installing requirements into this directory supports independent execution.

The SQLite file is a persistent analysis project with original bytes, membership, call graph, aliases and unresolved edges. It is usable with Python's built-in sqlite3 without installing a GUI disassembler. `--show 0x4391d0` prints a decoded routine. `parity-fixtures.json` contains exact case inputs/expected/actual/hooks; no mocked downstream behavior is disguised as full-game execution.

Native compatibility experiment, explicitly separate from emulator fixtures:

```powershell
python -m pip install frida==17.9.11
python tools/p01/logic/native_probe.py --seconds 20
python tools/p01/logic/install_local_ddraw.py
python tools/p01/logic/native_probe.py --seconds 30
python tools/p01/logic/native_probe.py --seconds 25 --race --scenario brake
python tools/p01/logic/native_probe.py --seconds 20 --race --scenario steering
python tools/p01/logic/native_probe.py --seconds 20 --race --scenario combat
python tools/p01/logic/summarize_native.py
python tools/p01/logic/decode_native_frames.py
python tools/p01/logic/verify_p01.py
```

Additional P01 native contact and AI scenarios:

```powershell
python tools/p01/logic/native_probe.py --seconds 20 --race --scenario hit
python tools/p01/logic/native_probe.py --seconds 20 --race --scenario steal
python tools/p01/logic/native_probe.py --seconds 32 --race --scenario police
python tools/p01/logic/ai_fixtures.py
python tools/p01/logic/validate_native_contacts.py
```

`native_extended.js` records live actor roles/behavior dispatch, original damage recipient mutations and range checks. The hit/steal arena relocates the player beside a real opponent immediately before each hit-processing opportunity, resets recipient pools once per weapon case, and for steal initializes the target attack via the original routine. Police initial spawn invokes the original spawn function. These are explicit controlled test conditions, not natural-play physics traces. Vehicle observations are read only inside live callback0x440dd0; earlier periodic snapshots of recycled constructor pointers are rejected.

The probe copies the source under this tool's ignored `runtime-copy`, excluding BAT/REG files. Frida spawns only that EXE suspended, installs guards, acknowledges readiness, then resumes. It virtualizes the game registry, blocks networking/child processes, hides the task's window, uses process-private fonts, and blocks display-mode changes for system DirectDraw. With the pinned local wrapper it uses GDI/windowed presentation. It records actual events and cleans up its exact spawned PID; it does not run original launchers or modify source registry. This is inspected-API containment, not an OS sandbox for arbitrary programs. Do not point it at arbitrary binaries.

`--race` explicitly bypasses pre-race movies/menu, cancels only this game window's menu timers, selects mode2/character1/level0/bike4/course1, disables demo/joystick, fixes CRT seed1996 and injects the documented input schedule. Physics/combat/animation routines remain native. Frame capture reads original DirectDraw surface buffers and palettes, never the desktop; samples can precede HUD composition. `cleanup_probe_fonts.py` exists only to remove session registration references from early probes at this newly-created runtime-copy path; current probes use FR_PRIVATE and require no global font cleanup.

Fixtures: original machine code under Unicorn. Component bench: selected physics routines under Unicorn, explicit rider parameter75, 60Hz nominal. Native probe: real process with compatibility hooks. Full campaign, target-hit/steal, video capture and all required behavior parity remain separate open gates.
