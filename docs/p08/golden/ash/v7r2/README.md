# Ash V7R2 — Fall-only articulated landing candidate

This is a new, unaccepted animation revision. Root explicitly broadened the
earlier vertical-only assessment to allow joint articulation inside `RB_Fall`.
The [initial diagnosis](FALL_DIAGNOSIS.md) remains the record of why a root-only
translation was insufficient; its statement that no candidate had been saved
describes that earlier boundary.

The same locked Ash v2 character concept was inspected before authoring. Its
SHA256 remains `6fa1090e13547df14e578f0ac77504ae5722d99a031a09e5f575c2775f9ce7e6`.
No character design, geometry, UV, map, weight, rest bone, gameplay rule or
physics state was changed. Only the Fall animation changed; its name, first
pose and 19-frame range at 24 fps (0.75 seconds) remain intact. All twelve other
actions, including MenuHero, remain exact.

## Authored change

The old clip drove a nearly rigid tilt. Its left boot passed approximately
156 mm through the flat source floor; its final fingertip lay much lower than
its torso, preventing a believable landing through root translation alone.

The new clip turns onto the left side, folds both arms forward to protect the
upper body, bends the knees asymmetrically and adds a small torso curl/head
side bend. Three end-pose trials were rendered and inspected before choosing
the target. The first two remained too elevated around the hip/torso; trial03
brings the hip and ground-side upper arm near the floor without burying a hand.

The chosen pose is blended through the existing Fall interval. A measured
vertical correction is authored into the Hip's local Y/Z curves together,
using its actual rest basis; horizontal Hip translation is preserved. This is
asset animation data, not a runtime floor clamp or an authority correction.
Sixty quaternion channels for fifteen joints and two Hip translation channels
change. Other Fall channels and all other actions are checked for exact source
equality. Modified curves use bounded automatic handles and consistent
quaternion signs between keys.

## Measured evidence

`fall-source-audit.json` records the authoring checks. `dense-regions.json`
independently reopens the saved compressed source and evaluates all three LODs
at 145 times, every one-eighth frame, across the whole clip. It records floor
proximity for meaningful regions grouped by dominant bone at every sample.

| Measurement | Frozen V7R1 | V7R2 candidate |
| --- | ---: | ---: |
| Worst sampled mesh floor bound | -0.156288 m at frame 9.25 | +0.002875 m at frame 17.375 |
| Final Hip region minimum, LOD0 | +0.261531 m | +0.004098 m |
| Final Torso region minimum, LOD0 | +0.272866 m | +0.013750 m |
| Final ground-side upper-arm minimum, LOD0 | +0.143599 m | +0.004054 m |
| Final Head/helmet region minimum, LOD0 | +0.397891 m | +0.013473 m |

At the final pose, 59 Hip-region vertices and 77 ground-side upper-arm vertices
are within 10 mm of the plane. The other regions need not all touch the plane;
the hands are raised for protection, and the bent feet remain above it. These
are evaluated geometry measurements, not contact forces or a physics proof.

The Hip trajectory retains a small initial rise of about 6 mm while the support
changes, and at most 0.889 mm upward movement between adjacent one-eighth-frame
samples. The main descent follows afterward. These motions are reported rather
than hidden behind a single nonpenetration flag.

## Actual render review

Nine fresh Cycles CPU renders use the same fixed camera and lighting:
`renders/before-frame-{1,9_25,19}.png` and six after views at frames
1, 3, 9.25, 10, 17.375 and 19. All nine images were opened and inspected.

- The first pose remains visually the same. The pixel check records at most
  one stored byte of channel difference; it does not claim byte-identical
  rendering or a concept-fidelity score.
- At the old penetration frame, the boot is now above the floor and the arms
  have begun folding. The pose still reads as a stylized tipping motion; weight
  transfer and impact timing need actual moving/native review.
- The final view has a curled side landing with support near the hip/upper arm,
  replacing the old hovering rigid pose. The gloves cross near the chest during
  transition; fine wrist/garment contact and self-intersection review remain
  open. The images do not establish a complete narrow-phase contact audit.
- Existing face likeness, hair, collar, cloth folds, glove finish and material
  differences from the locked character concept remain unaccepted. This patch
  does not disguise them or repair the rest of the animation library.

## Delivery and preservation

`handoff.json` binds the new native-compressed source (87,335,715 bytes), staged
FBX, exact original files, maps and actual renders. `descriptor-staged.json`
selects ID `RB_Golden_Ash_V7R2` with explicit `fallenRootOffset=0`; its FBX and
all thirteen clip paths must be rebound only after root publishes the exact
bytes into a fresh Assets path.

The independent binary FBX comparison establishes exact full mesh records
(including geometry, UVs, normals and polygon material indices), 135 skin
clusters, six shape deltas and ordered material bindings. All twelve non-Fall
animation takes are exact. The exported Fall take has 404 changed derived
transform channels; that count is distinct from the 62 authored quaternion/
translation channels. No exported change occurs in another take.

Original V7, V7R1 and protected Club SHA256 values still match their frozen
records. No Unity source or Assets files were written by this authoring task.
The first export failed before writing because the post-render Blender context
lacked `selected_objects`; the corrected export uses an explicit native
selection context and the original failure is retained. Safe mode remained
enabled throughout; direct pinned Blender MCP used the owned process on 9878,
with rendering capped at four CPU threads. No Jarvis or paid service was used.

Root must perform fresh native import, dense BakeMesh floor checks, moving
captures and transition/contact review against the same source/FBX hashes.
Slopes, collision/VFX/audio alignment, runtime blending, comfort and performance
are still separate gates. No native, physical or visual acceptance is claimed.
