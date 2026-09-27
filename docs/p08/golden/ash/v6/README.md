# Ash V6 — native-review candidate, visually unaccepted

V6 preserves V4/V5 and follows the locked `ash-v2.png` and `UI/main-v2.png`.
It uses direct Blender MCP on port 9876 and existing local licensed data only.
No Jarvis MCP, ImageGen, cloud service, installation, Unity Editor call,
Client/server/shared/probe edit or live Assets write occurred in this pass.

## Reference comparison and geometry

The initial V5 goggles measured about 80% of the helmet's frontal width,
but each optic was too tall and the inner rim gap was approximately 29 mm.
The concept calls for a low rounded rectangle and a much closer bridge.
V6 changes the outline from a 2.6-power superellipse to 3.4, lowers the
authored lens height from 60.8 to 42.8 mm, and widens each authored lens from
73.6 to 81.6 mm while moving their centres inward. The fitted bridge endpoints
are now approximately 19.3 mm apart. These are measured construction changes,
not a similarity score or proof that the optical assembly matches every view.

Facial corrections use named rest-space landmarks with explicit support and
millimetre displacements in `landmarks-receipt.json`. No random facial noise
or global head distortion was used. The front/profile probes recorded in
`preserved-gameplay.json` show the nasal root projecting forward 4.79 mm,
the dorsum 4.75 mm, the chin profile 4.16 mm and the submalar surface receding
5.27 mm at fixed probe coordinates. Individual vertex displacement peaks at
5.24 mm. The ray differences include interpolation across the changed surface;
they must not be confused with a concept-measured identity error.

The concept's close portrait and helmeted full-body views have different
perspectives. Comparisons use orthographic front, quarter and side renders
plus a separate menu camera; no fabricated pixel-perfect alignment or inferred
focal length is claimed. The current head remains recognizably more generic
and smooth than the portrait. Eyelids, brows, lips and facial texture still
need likeness refinement. Nose-tip and jaw relationships need another visual
review rather than treating the landmark edits as acceptance.

Obsolete hair cards and crossing forehead fibers were removed on the V6 copy.
The replacement uses fitted curved fibers with varied endpoints. The first
parallel bundles looked like strips and were rejected. The final fringe has
zero triangle intersections against the authored helmet shell and rolled rim,
but remains too sparse and lacks the reference's convincing volume.

## Materials and export

Each equipment LOD has its own actual baked atlas: 2048, 1024 and 512 pixels.
This retains the shell, band, goggles, hardware and fringe in one material per
LOD. A separate 2048 skin set adds restrained beard-region pigment and roughness.
There are 16 new runtime PNGs: Base Color, tangent Normal, Metallic/Smoothness
and Occlusion for four roles. Mask packing is R=metallic, G=AO, B=0,
A=1-roughness. Read-only PNG checks show zero byte-channel packing error.
Fresh FILE images were reloaded before packing; packed-byte fingerprints are
compared with external PNG bytes. No generated image candidate was used.

The optical material is opaque polished amber in this candidate. It does not
provide the reference's glass transmission. Enamel still appears too clean;
the existing jacket, collar and boots are also below the concept. Three merged
skins contain 142,881 / 70,114 / 20,799 triangles. These are technical counts,
not an approved desktop or multiplayer performance budget.

Two LOD2 socket quads had a collinear triangulation diagonal. Choosing the
alternate diagonal repaired them without moving a vertex or UV. Facial edits
also made 16/8 old eyebrow microcaps fall below the geometric threshold;
their radius was increased by at most 0.067 mm. The unused archival UVSource
layer was removed; verified UV0 remains. No threshold was weakened.
Final source and FBX roundtrip have no triangle or primary-UV degeneracy.

## Rig and menu pose

All 45 rest bones and all 12 gameplay actions compare exactly against V5.
Glove/boot positions and weights compare exactly for 13,807 / 5,206 / 1,435
vertices. Existing vertex indices may be remapped by removing old head parts.
All 13 actions are sampled at five times for finite deformation.

The previous MenuHero head faced approximately −40 degrees in Blender while
the review camera was approximately −42 degrees, causing a near-camera gaze.
V6 changes only the four Head quaternion curves of MenuHero: +30 degrees
world yaw and 4 degrees upward pitch. Head origin moves less than 0.0002 mm
from numerical decomposition; all other menu curves remain exact. This gives
the intended screen-right gaze in the source comparison. It also exposes
existing collar deformation/gaps, which remain unresolved. No clothing weight
changes were introduced under the preservation requirement.

Use the parent-verified native policy: 12 gameplay bindings, the separate
MenuHero preview, six explicit looping clips, and `restPose=bind`. The source
and actual FBX contain 13 named animation stacks. Root still needs to verify
the actual Unity hierarchy, clip imports, loops, materials and presentation.
Menu hands use the retained ApexR2 contact reference. Final ApexR3 contact
validation remains required. No production registry/mask or acceptance changed.
