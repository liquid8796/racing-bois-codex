# Direct Tripo + Blender workflow

The user's 2026-09-30 instruction adds direct Tripo AI generation from the supplied
free-credit keys, followed by the separately pinned direct Blender MCP. Existing
assets join the same conversion inventory. Keep their locked concepts, original
sources and exact hashes; protected Club remains untouched. The
`blender-jarvis-pro` skill/plugin and Jarvis MCP are excluded.

`generate_candidate.py` discovers the current key file before selection and every
poll. Keys stay inside process memory and authenticated headers. Receipts use
opaque fingerprints, counts, balances, parameters, task IDs and artifact hashes.
No top-up, purchase or subscription endpoint is called. The API balance is an
aggregate: free-credit provenance and600-credit allowances are user supplied.

The client serializes generation per checkout with a native Windows file lock.
It checks the allowance, existing receipt costs, available balance and frozen
credits before submitting. Positive but unaffordable keys, held credits and
unverified balances are preserved. Only fresh authenticated balance0/frozen0
permits removing a key. The keyring rereads under an exclusive handle and retains
concurrent appends, comments, BOM and line endings; it creates no secret copy.
It has rollback on write failure and does not claim power-loss atomicity.

Each new task uses a fresh candidate folder. The submission boundary and returned
task ID are persisted before polling. Unknown submission outcomes remain blocked;
definitive parameter/account rejection is recorded and diagnosed. GET polling
can retry; generation POSTs are not retried. Recover an existing task with:

```powershell
python tools/p08/tripo/recover_candidate.py ArtSource/P08/Tripo/ASSET/RUN
```

Recovery issues no generation POST, validates the task's key owner and ID, reuses
only hash-matching owned artifacts, and preserves partial downloads under fresh
names. Returned CDN downloads receive no API authorization header.

Current generation profiles are H3.1 detailed geometry plus pinned v3.5 extreme
PBR texture; separate H3.1 detailed **untextured** parts; and P1 bounded low-poly.
Parts and texture/PBR cannot be requested together. Exact parameter constraints
and the retained first rejection are in
`docs/p08/tripo/API_PARAMETERS_20260930.md`. Published price estimates and
preflight reserves are recorded; the API exposes no documented per-task hard cap.
Actual task costs and delivered map sizes are inspected separately.

Example using an already reviewed single-bike input:

```powershell
python tools/p08/tripo/generate_candidate.py --input ArtSource/Concepts/P08/Golden/spark-v1-side.png --reference ArtSource/Concepts/P08/Golden/spark-v1.png --out ArtSource/P08/Tripo/Spark/NEW-RUN --profile high-quality
```

Raw output is an unaccepted source candidate. Import through direct pinned Blender
MCP, save raw and review copies, reload and verify geometry/UV/material data,
then compare actual front/side/rear/quarter renders with the corresponding locked
concept views. Shape repair, physical scale, separate moving parts, contacts,
rigging, baking, retopology, LODs and native Unity review follow. Provider completion
does not grant production acceptance, change masks or certify fidelity.

Run the offline lifecycle controls with:

```powershell
python -m unittest discover -s tools/p08/tripo -p 'test_*.py' -v
```

The controls use fake keys and a socket guard. They cover native exclusive locks,
append-preserving key removal, credit bounds, no resubmission, task recovery and
secret-safe transport errors. They do not consume real credits.
