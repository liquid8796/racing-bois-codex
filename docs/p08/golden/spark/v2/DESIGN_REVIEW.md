# Spark V2 — bounded mechanical refinement, not visual acceptance

The pinned hero and supporting side concept were opened before editing, alongside
V1's actual Unity `unity-studio-20260927-02/quarter-lod0.png` and `side-lod0.png`.
The initial comparison and proposed dimensions were sent to the root before
geometry edits. The hero remains the design master; the side image contains
perspective and is not a calibrated engineering drawing.

- Hero SHA256: `e358ecf1a809f5373aa45ef92cbd6897ed1e1693cacc73b0f6df697d91bedce6`.
- Side SHA256: `ad5478c942350462a34d12b1ba9f9714cb00a595ff9465bc1d000cf6b5e7ad0b`.
- `before-manifest.json` freezes 64 original files, including all V1 source/maps,
  locked concepts/prompts, the protected Club and canonical vehicle dimensions.

## Comparison that drove this revision

V1 renders show a solitary tall rectangular fin tower over a flat crankcase box,
simple detached-looking circular lids, and large unused spaces behind the intake.
The concept shows rounded cylinder/head castings, a joined lobed lower case,
varied cover shoulders, real intake connections and denser mechanical transitions.
The V1 tank is short and bulbous in the quarter view; the saddle has weak cushion
separation and a thin-looking rider region. These are visible differences, not a
similarity score.

V2 replaces the engine with original rounded twin barrel geometry, a continuous
lobed fin casting, separate domed rocker covers, a common curved crankcase,
shouldered circular covers, bolt bosses, ribs, intake collars, round carburettor
castings and connecting hoses/lugs. The tank has fuller controlled shoulders and
lower sidewalls. The saddle retains its contact height with a thicker base,
raised passenger region, piping and a separate wrapping strap. Source images and
canonical physics were not modified.

Dimensions are authored decisions, not metric measurements recovered from the
concept. Wheelbase remains 1.390 m, wheel centers remain Y ±0.695/Z 0.315, and
tyre outside diameter remains 0.630 m. Seat/grip/foot markers remain exactly at
their V1 declared coordinates. Final seat surface at the canonical center contact
is Z 0.799999952 m; revision 05 shifts the rib phase to put a crest at Z 0.800
instead of leaving that point in a 2.7 mm groove.

## Mechanical revision and technical evidence

Revision 01's new case intersected the inherited chain plane, and its tank
intersected the steering head/clamp/frame rails. Those failures were measured and
retained. Revision 02's chain passage was rejected as an inferior mechanical
solution. The final candidate restores the intact case and changes the authored
drive plane from X +0.075 to +0.245 m. Chain, countershaft and rear sprocket move
together. Downstream exhaust/silencers move +0.075 m outboard, with the original
front ports held and connecting shafts/hangers adjusted. Both mechanisms remain
on the same semantic-right flank. The exact 503 changed inherited mesh names and
their transforms are recorded in `mechanical-clearance-03c-mcp.json`.

Tank underside/neck cavities clear the actual original structural objects.
Boolean boundary cleanup removed nine collinear samples, at most 0.000004279 m
from their surviving edge. The physical-triangle threshold was not relaxed.
Two earlier attempts after loading a file in the same tool call failed on Blender
context access; they did not produce a final saved candidate. The successful run
uses a separate load call and data-created connector meshes. Failed receipts are
retained.

The scoped audit checks all 180 new meshes for physical/UV triangle failures and
non-manifold edges. It also checks the chain against 225 named engine, frame,
shock, exhaust and rotor obstacles and tests the tank against the named steering
and frame structure. Revision 04 passed those checks; revision 05 reruns them
after the seat adjustment. Intentional positive surface contacts at nine engine
joints are separately recorded in `joints-04-mcp.json`. These are static checks,
not swept steering/suspension clearance, export/LOD validation or visual acceptance.

The visible mesh bounds stay within the prior envelope:
X [-0.406, +0.406], Y [-1.032, +1.010], Z [0, 1.194905] m.
The source is a new native compressed Blender file; no V1 file is overwritten.

## Remaining corresponding-view differences

The actual revision 04 and final revision 05 quarter/side renders were opened and
inspected; revision 05 only adjusts the seat rib phase and repeats the same cameras. Both are compared with
the matching concept views and the V1 `04-*` Blender cameras. The Unity baseline
uses different lighting/framing, so it is not treated as a calibrated material
comparison.

| Area | Current remaining difference | Status |
| --- | --- | --- |
| Engine | The casing is joined and rounded, but cylinder-bank proportions, fin spacing, head contours, cover shapes and the density of small fittings still differ. | Unaccepted |
| Tank | Fullness and shoulder transitions still differ; the retained cream paint boundary is not the exact concept inset. Clearance scallops/slots at the neck and underside are visible and need a designed outer surface, despite passing intersection checks. | Unaccepted |
| Saddle | Raised cushion and strap are present, but silhouette, padding sections, seam/stitch scale and leather finish remain different. | Unaccepted |
| Frame/intake | The new manifold connects the assembly, but open frame regions and bracket/support shapes still differ from the concept. | Unaccepted |
| Chain/exhaust | Static clearance is improved. The more exposed front sprocket and outboard pipe arrangement need further corresponding-view review; a whole-bike swept-clearance claim is not made. | Unaccepted |
| Inherited mechanisms | Wheel/spoke profiles, rotor/caliper detail, cockpit, headlamp, cables and finish remain visibly simplified. These were not replaced by this bounded engine/tank/seat task. | Unaccepted |
| Materials | Copper, cream, leather and metal response still differ. V1 textures are preserved; no new texture bake or shader-fidelity claim is made. | Unaccepted |

This is a distinct V2 refinement candidate. No FBX/LOD export, Unity payload
update, roster/content-mask change, gameplay change, commit or push is performed
by this task. Geometry checks cannot substitute for the required concept match.

## Reproduction

Use only the task-owned Spark Blender process through the pinned direct MCP
client on port 9879. The server revision is
`6f992ffbca3cb715d111fc640b737b808632273c`, protocol 7, Blender 5.2.1 LTS;
safe mode remains enabled and script auto-execution is disabled. Ash/Unity were
not touched and no downloaded geometry or paid service was used.

Run `spark_v2_inspect.py`, then `spark_v2_refine.py`. To reproduce the final
mechanical placement from its saved revision 01, run `spark_v2_reload01.py` in a
separate call, followed by `spark_v2_mechanical_clearance.py`,
`spark_v2_tank_topology.py`, and `spark_v2_seat_contact.py`. Use the final
`spark_v2_render_05_quarter.py` / `spark_v2_render_05_side.py` and scoped audit.
Revision 02 is historical evidence and is not part of the final reproduction path.
