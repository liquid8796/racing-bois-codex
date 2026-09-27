# Ash V7 — staged native-review candidate, visually unaccepted

V6 was published separately with immutable input pins, complete preflight,
no-overwrite publication and an actual idempotent retry. Seven isolated
publisher tests passed. V7 is a separate source and export; it does not
replace V4/V5/V6, the protected Club source, or any production acceptance.
Only direct pinned Blender MCP9876 and existing local/free data were used.
No Jarvis MCP, paid/cloud service, image generation or Unity Editor call was used.

## Collar and upper garment

The original collar edge carried up to 90.8% Head influence, its old side snap
100%, and its overlap tab/snap only about 38–42%. A head turn therefore pulled
the parts apart. The collar components now share the Torso binding; the old
floating side snap was removed. The overlap tab sits outside the collar,
has rounded corners and a real inner facing underneath the old skin slit.

Actual neck sweeps over 17 pose samples fitted the collar geometry. The first
vertex-only check was insufficient: triangles crossed the neck between their
vertices. The final repair checks those actual intersections and face/edge
samples. No triangle threshold was relaxed. All three LODs are checked.

An over-broad initial transfer of Head influence from the upper jacket
exposed skin near the shoulder. A attempted broad geometric fit hit its
30 mm displacement guard and was rejected without saving. Original V6 jacket
weights were then restored outside the separately repaired collar. The real
menu portrait shows the exposed shoulder patch resolved. No skin geometry
was deleted, changed or hidden. Collar silhouette remains too broad/flared
relative to the reference and is still a visual defect.

## Glass and helmet finish

Amber optics have a separate material and explicit transparent descriptor
binding: URP Lit, alpha blend, opacity 0.38, metallic 0, smoothness 0.895,
backface culling, no alpha clip. Base Color alpha stays 1; surface opacity is
the descriptor parameter. The Blender preview uses alpha-blended Principled
shading. It does not claim refractive or transmission parity with the concept.
The underlying helmet and its surface marks are visible through the lenses.

V4's positional wear strokes missed much of the changed V6 shell. V7 projects
92 restrained scratches and 48 edge chips onto its actual shell. Cream paint,
brown worn areas, roughness and normal detail are baked into separate opaque
equipment atlases at 2048/1024/512. Glass is excluded from those atlases and
uses four explicit constant 512 PBR maps. There are 16 new PNGs in total.
Existing V2/V3/V4/V6 material maps remain unchanged. Numeric PNG checks show
zero byte-channel packing error. Runtime image files are reloaded before
packing, and packed bytes are compared with the external PNGs.

## Canonical R4 menu contact

Reference: `Assets/RacingBois/Art/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4.fbx`,
SHA256 `4e57cfeaefe2e27643c17bb083b04acb15dd483276a02058f05e687f69c16841`.
The bike is at Unity origin/yaw0, Ash root at (-0.30,0,-0.25)/yaw0 with
model yaw180. Author-space bike placement is Translation(-0.30,-0.25,0)
times Rz(180). Reconstructed native marker positions verify handedness and
forward direction; the old R2 placement is not silently reused.

The retained menu gesture had real glove intersections. An initial lift
removed them but balanced on a curled finger while the palm floated; that
comparison was rejected and retained. V7 reorients each hand from the actual
R4 support normal and the real central-palm support envelope, then relaxes
the menu-only finger rotations over the surface. It preserves rest bone
lengths, glove vertices/weights and every gameplay action.

The final contact audit samples 17 times over the two-second menu loop at
all three LODs. It independently checks triangle intersections, containment
of connected glove parts inside the closed bike components, Euclidean
surface clearance, and a central-palm region. Current source minima are
approximately 1.14 mm left and 1.80 mm right for the whole glove. The central
palm minimum ranges from approximately 2.59 to 5.71 mm across samples/LODs.
These numerical gates support the actual close views; they do not establish
100% concept fidelity. Native Unity sampling remains required.

A nearest-triangle-plane sign initially misclassified one glove point that
was 43.3 mm above a vertical gas-cap edge. The final gate uses closed-component
containment rather than accepting that plane sign or loosening a tolerance.
Two expensive diagnostic attempts timed out because a staged script rebuilt
the complete glove graph inside its per-vertex loop. That implementation bug
was fixed and has a targeted AST regression check. Only the saved task-owned
9876 Blender instance was restarted; other instances were left alone. Failed
receipts and rejected comparison images remain available.

## Preservation and remaining review

All 45 rest bones and 12 gameplay actions compare exactly against V6.
Glove/boot rest coordinates and weights match for 13,807/5,206/1,435 vertices.
Only MenuHero arm, hand and finger quaternion curves change; its head, torso,
legs, translations and scales remain unchanged. The explicit native policy
retains six loop flags, 12 gameplay bindings, separate MenuHero preview and
`restPose=bind`. Three skins have 142,973/70,234/20,933 triangles.

Source geometry/UV, finite deformation, actual FBX roundtrip and texture
checks are technical evidence only. Review the 17 full-body images, helmet
front/side/quarter, menu portrait and both close hand views. Face identity,
fringe density, jacket tailoring/folds, glove appearance, collar silhouette
and reference-specific weathering remain visibly below the locked concepts.
No visual, native-runtime or performance acceptance is claimed, and no
production registry/mask was promoted.
