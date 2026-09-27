# RB_Fall assessment — no V7R2 candidate saved

The frozen, compressed V7R1 source was opened read-only in the owned direct
Blender MCP process on port 9878. Original V7/V7R1 files, meshes, UVs, maps,
rest rig and actions were not saved or modified. The actual V7 fall-start,
midpoint and end renders were inspected alongside the measured poses.

`RB_Fall` spans frames 1–19 at 24 fps: 0.75 seconds. The source probe samples
the whole clip every quarter frame (73 times) across all three actual evaluated
LOD meshes. Its worst floor bound is **-0.156288 m at frame 9.25**, on the left
boot/shin, consistent with the separate native midpoint measurement near
-0.153 m. The original probe request used a disallowed dunder method as a sort
key and was rejected before execution; the revised allowed script uses ordinary
list operations. Both receipts are preserved and safe mode remained enabled.

## Why a root-only repair is insufficient for believable contact

At final frame 19, actual LOD0 region minima, grouped by dominant bone, are:

| Region | World Z above the fixed source floor |
| --- | ---: |
| Left pinky fingertip | 0.034973 m |
| Left hand | 0.056148 m |
| Left forearm | 0.089177 m |
| Left upper arm | 0.143599 m |
| Hip | 0.261531 m |
| Torso | 0.272866 m |

The final rendered figure is a rigid tilted body suspended above the floor.
Translating the skeleton down until the fingertip has 2 mm clearance leaves
the torso approximately **0.240 m above the floor**. Translating the torso down
to 2 mm instead would bury that fingertip approximately **0.236 m**. A vertical
translation cannot change these relative distances or make the extended arm
into a plausible supporting/landing pose.

## Feasible bounded correction and its limit

The parentless Hip bone could receive an authored vertical correction without
changing the simulation, mesh, map, rest rig, rotations or other actions. World
up expressed in its rest-local coordinates is approximately
`(0, 0.939316273, 0.343052357)`. Such a correction would change the Hip's local
Y/Z animation curves together; changing local Z alone would not be vertical.

A source-authored clearance envelope would need a peak lift near 0.158 m around
frame 9.25. It could preserve the first pose and smoothly settle the minimum
mesh envelope near the floor, then be independently checked at dense subframes,
exported and tested by native BakeMesh. This would be a **penetration-only
technical candidate**, not a credible final landing: it would still balance
the floating body on its fingertip. No runtime height clamp is proposed.

For a contact repair that looks plausible, `RB_Fall` also needs deliberate
landing articulation, particularly the left arm/hand and torso/hip. That changes
the requested scope beyond a pelvis/root vertical correction. The inherited
stiff tilt and missing landing response should remain unaccepted until that
design is authorized and reviewed. No V7R2 `.blend`, FBX or descriptor was
created merely to turn the numerical floor test green.

Evidence: `fall-before.json`, `contact-design.json`, their direct MCP receipts,
and the preserved V7 images under `../v7/poses/`. These measurements establish
source pose geometry, not collision forces, comfort or visual acceptance.
