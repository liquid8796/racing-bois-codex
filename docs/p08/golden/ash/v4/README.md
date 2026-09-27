# Ash V4 — staged appearance and menu-pose candidate, unaccepted

V4 is **not accepted for production** and does not match the locked Ash/UI
concepts100%. The actual baked front, side, quarter and portrait images were
inspected before export. No mesh/animation test is offered as a substitute for
visual approval. This subtask wrote no live Assets files and made no Unity
calls. All DCC work used the direct pinned Blender MCP9876 with safe mode on;
no Jarvis or paid service was used.

## Changes and preserved data

The V3 source, FBX and texture inputs remain unchanged. The anatomical base
continues to use the documented licensed CC0 source from V2; this is not a
claim of all-new anatomical topology.

V4 tightens the existing continuous jacket, adds local tension folds and
shortens its former shirt-length hem by79mm. Shortened-jacket thigh influence
is reassigned to pelvis/torso; the authored sleeve, waistband, yoke, zipper,
collar, pocket and shoulder/elbow quilting details are weighted to the same
rig. Ochre sleeve bands follow continuous surface-projected paths instead of
the previous disconnected bone-cylinder masks. There are five new baked
material roles: Skin, TailoredLeather, LeatherDetails, HelmetEnamel and
Forelocks. The other nine runtime materials reuse the existing maps.

Facial contour/tone changes are small and remain insufficient for likeness.
The first broad forelock ribbons looked pointed and were rejected; the final
candidate uses authored fine fibers, with fewer fibers at LOD1 and the
existing silhouette at LOD2. The first helmet crackle pattern was rejected;
localized projected scratches replace it. The helmet, hair volume, facial
features and garment/boot/glove construction still need visual work.

An independent reopen-and-compare audit confirms all45 rest bones and all12
gameplay actions unchanged, including5,400 curves, key values, handles and
extrapolation. Original glove/boot contact vertices, indices and skin weights
match V3 exactly:13,807/5,206/1,435 checked vertices across the three LODs.
This preserves the previous contact inputs; it does not upgrade their sparse
V3 contact diagnostics into a collision/fidelity proof.

## Separate menu action

`RB_P06_Rider_Rig|RB_MenuHero` is an additional actual FBX animation stack:
61frames at30fps, a two-second loop, no gameplay root motion. It is separate
from Idle and from the twelve clips in the staged RiderAnimationSet contract.
The diagnostic actor offset from the bike is Unity`(-0.30,0,-0.25)` with the
existing actor import rotation. `menu-pose.json` records the actual R2 surface
and wrist targets. The new pose uses real tank/tail geometry, not arbitrary
floating targets. Final ApexR3 contacts remain required.

The first menu test exposed a leg axial-roll error and the cropped camera;
those failed images are preserved. The corrected pose retains the standing
bone roll and samples actual keyed animation in
`menu-hero-r2-roll-fixed.png` and the corresponding hand images. These images
precede the last shortened-jacket weight cleanup and use imported R2 bike
materials; they are contact/pose evidence, not native bike material approval
or final main-v2 composition.

## Texture and export evidence

Twenty new PBR PNGs live under ArtSource/P08/Golden/Ash/V4/Textures. Blender
baked BaseColor, tangent Normal, Roughness and Occlusion from the actual
candidate. Numeric mask packing also ran inside Blender:
R=dielectric0, G=AO, B=0, A=1−roughness. Read-only PNG checks verify normal
lengths and exact channel packing; the maximum8-bit channel error is0.
BaseColor/Normal/AO copies are byte-identical to their bake outputs.

All new FILE images were reloaded and decoded before packing. The56 runtime
image packed-byte fingerprints and lengths match external PNGs; their
external SHA256 values are recorded. A procedural source checkpoint is kept
separately. No concept image is projected as a fake character surface or
background. The parent-generated
TextureCandidates/tailored-leather-detail-v1.png remains unapproved and unused.

Final LODs contain147,379/67,748/14,355 triangles. Source and actual FBX
reimport counts match exactly, with zero physical triangles below the existing
squared-cross threshold1e-16 and zero degenerate primary-UV triangles. Each
vertex has at most4 normalized bone influences. Five deformation times were
checked for each of13 clips across all three skins.

The first export exposed179 duplicate faces in LOD2:126 aged-brass faces and
53 older hair-fiber faces. Blender's importer removed them automatically.
V4 now removes these duplicates explicitly while preserving every vertex,
shape-key coordinate and skin weight; the repaired source and export counts
match. The initial report checked geometry/UV finiteness but not count parity
and is superseded by `roundtrip-final-mcp.json` / `roundtrip.json`. The prior
FBX remains under `_local` with a PreValidation suffix. No gate was weakened.

Uniform small-surface/fiber UV reuse is intentional. This is not a claim that
every UV island is exclusive. The collar normal-disabled control retains
most of its visible shape issue, so that issue must not be misreported as
fixed by numeric texture checks. Native import, shader behavior, draw calls,
memory and gameplay FPS have not been accepted.

## Remaining visual failures

The face is still generic relative to ash-v2; the brows, hair volume, goggles,
helmet/strap construction and weathering differ. Leather still reads too
clean, with insufficiently convincing tailored folds and worn edge detail.
Ochre seam transitions, collar fit, glove knuckles/fingers, knee construction
and boot silhouette/detail remain below the concept. The main-menu gaze,
camera framing and final R3 contact combination also need actual matched-view
review. Do not use this candidate to populate the rider roster or unlock a
production content mask.

## Handoff

`delivery.json` and `descriptor-staged.json` bind the source, staged FBX,
references, material files and actual FBX stack names. Root must copy the FBX
and20new maps to fresh V4 Assets paths, verify unchanged hashes, and rebind
those paths before native import. Reused V2/V3 maps remain at their old paths.
Keep `restPose=bind`, the semantic hand markers and the12gameplay clip entries.
The optional menu action is separately documented in `menu-pose.json`.

Frozen source SHA256:
`a42a84a423fb158eb84995bbe2d842d7925c23a872fe36902f5566570cf64a30`

Frozen FBX SHA256:
`b2bd4e1a7cb966c857acff268a342fab7b78db3af1f6d27e94187d41bf6997e2`

The source/FBX/map tests are technical evidence only. All current renders and
the model remain visually unaccepted.

Native follow-up: `descriptor.json` remains the publisher's immutable byte-level
handoff. Unity import `597c131dc93545b4b7ea70ad93159b92` passed, but engine inspection
found all imported loop flags false. The separate `descriptor-native.json` declares
six looping in-place clips and keeps `MenuHero` outside the12 gameplay bindings.
Import `00e8b998d5734c5aae4f7a55fc2dc471` sampled all13 clips and passed. Native
`native-animation-policy.txt` verifies the flags,12 gameplay bindings and zero
position/rotation discontinuity between MenuHero endpoints. This does not accept
its deformation appearance or hand contact on ApexR3. Actual main-menu image is
`../../ui/r3-ashv4-main-1920.png`; background composition and hero art remain wrong.
