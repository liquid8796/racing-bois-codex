# Apex R6 fairing study — source checkpoint 05

The locked specification remains [Apex v2](../../../../../ArtSource/Concepts/P08/Golden/apex-v2.png),
SHA256 `f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819`.
The concept, R5 Blender side/quarter and actual R5 Windows views were inspected
before this correction. Independent review selected the same dominant defect:
the broad outer fairing read as a flat hanging white sheet instead of a wrapped,
faceted shell with a deliberate lower enclosure.

Checkpoint05 changes the fairing system only: a more defined shoulder and lower
plane, an explicit white/graphite seam, and recessed front-edge returns. The
intakes remain physical openings with their recessed walls/grilles. The same
existing material palette and map bytes are used. The original belly, tank,
seat, frame and mechanical geometry remain exact in this study.

Actual [quarter](05-quarter.png) and [side](05-side.png) use R5's exact source
camera settings, lighting, 1280×900 resolution, Cycles CPU/four threads and24
samples. The [front](05-front.png) is an additional diagnostic, not a calibrated
R5 camera match. The common source side/quarter cameras view vehicle-right;
asymmetric chain-side detail must additionally be reviewed from vehicle-left.

The rendered shoulder and lower color boundary are clearer. The overall panel
still reads broader/flatter than the reference; intake placement/outline and the
simple lower enclosure remain different. The tank/seat/frame void, lamp cowl,
optics, mechanical detail and finish still need work. **Visual acceptance remains
false.** Root independently inspected the study and requested continued whole-
asset correction. No fidelity percentage is generated.

Preserved iterations:

- 01: panel-volume/crease/seam change. Actual quarter and side retained.
- 02: added front returns; its actual quarter looked excessively box-like. Not
  selected as the visual direction.
- 03: narrower return study. A back-layer coordinate reuse error was caught
  before rendering; this source remains preserved and is not selected.
- 04: corrected paired back layers to their intended3.5mm forward-axis offset.
  Actual quarter/side retained. Its UV audit failed and remains recorded.
- 05: explicit triangulation and704 collapsed finish-UV triangle repairs in the
  changed system, without moving vertex positions. Final views above use05.

[Audit05](audit05.json) reports zero non-manifold, physical-area or UV-area
failures in the edited meshes; zero intersections against the unchanged R5
belly in the named scope;571 untouched mesh signatures identical to a reopened
R5 source; and unchanged wheel transforms and overall bounds. The smallest
physical triangle margin remains close to the existing threshold, so a future
FBX roundtrip is still necessary. These are structural observations, not visual
acceptance or a whole-bike collision/steering test. No LOD assembly, FBX, Assets
export, Unity import or production mapping was performed.

[Preservation check](preservation-after-fairing.json) verifies162 prior/reference/
protected files unchanged, including all R5 artifacts, shared R4 maps, Club,
unowned Ash and the two original fonts. Source checkpoints live separately under
`ArtSource/P08/Golden/Apex/R6`. Further Apex work continues from a fresh checkpoint;
05 and these comparisons remain immutable.

Direct pinned Blender MCP only, existing task-owned port9878/PID32112, separated
from the terrain worker's9877. Its saved R5 file and clean state were verified
before reuse; safe mode stayed enabled and automatic scripts disabled. The
pinned server/venv bytes match the documented telemetry-only patch. No new Blender
process, Jarvis bridge, paid service or external model import was used.
