# Tripo conversion inventory — 2026-09-30

`inventory.json` records the current disk and provenance inventory for the new
direct TripoAI + Blender workflow. It does not submit jobs, access the key file,
change model sources, integrate Unity assets or grant production acceptance.

There is one existing **TripoAI API delivery**: Apex trial
`7c8068e9-c221-4be9-aeed-c80a8f79803e`, H3.1 `v3.1-20260211`, standard geometry
and standard PBR texture. Its historical receipt records 30 credits consumed.
The balance in that receipt is historical; it establishes neither today's
balance nor today's key count. The separate ignored Apex TripoSR local trial is
not an API job.

The saved API trial has one mesh, 789,003 vertices, 1,480,371 triangles, one
material and three packed 2048px maps. Physical scale, part articulation, rig,
LODs and Unity integration are absent. Actual front-quarter, side and rear
renders were inspected against the locked master and derived input. The opaque
silver screen, blank lamp optics, long round rear cans, tall central rear lamp
and soft tank/fairing joins remain visible mismatches. The trial is unaccepted.

The roster inventory covers **15 bike slots, eight rider slots and 24 P08 prop
exports**, plus **15 existing legacy core semantic mappings**. These numbers
must not be added as independent models: starter Bike00 aliases the P06 bike,
police rider shares the P06 rider source, and each environment source contains
multiple modular props. Seven Canyon/shared-furniture core mappings supplement
the 24 P08 props. The Club source remains protected and any Tripo replacement
must use a fresh path.

The first useful controlled upgrade is Apex: its existing single-view input and
standard-quality output provide a concrete baseline for one provider-supported
quality change. Root owns current API schema verification, credit planning and
job submission. The front/quarter input does not establish the canonical rear;
the compact twin rounded-rectangle under-tail outlets still need explicit
Blender construction against the master rear view.

The priority queue then covers Ash, Spark, missing Odyssey/Havoc, the remaining
distinct bike identities, the remaining rider identities and their portraits,
modular Canyon assets, the other route props and legacy auxiliary actors.
Whole scene posters and multi-panel character sheets require reviewed
single-asset conditioning before generation. Current authored Apex R7, Ash V8
and Canyon V20 sources are inventoried as separate unaccepted checkpoints;
they have no Tripo API lineage yet.

The JSON binds exact actual reference/source/export/receipt/render hashes and
records the 12 existing Ridge source/export declaration mismatches. All files
were stable during hashing. Only the listed images were directly inspected in
this audit; historical `inspectedBefore3d` fields for other concepts are not
fresh visual review. No acceptance flag, catalog mask or historical receipt was
changed. The existing production binding gate remains mandatory.

The old trial tooling supports one stdin key and standard-quality generation;
it has no file inventory refresh, rotation or exhausted-key removal. Its saved
submission boundary prevents blind POST retries. A new shared dispatcher needs
to preserve that boundary while root adds the requested key-file lifecycle and
current provider parameters.
