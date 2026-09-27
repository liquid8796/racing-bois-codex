# Apex R3 work in progress — unaccepted

Owner uses only direct Blender MCP port9878 (current task process34596). Root now owns Garage port9877; Ash uses9876. No Unity calls, production masks or earlier source files are changed by this authoring task.

The immutable master is `ArtSource/Concepts/P08/Golden/apex-v2.png`; its review fixes1.43m wheelbase, approximately0.63m tyres and0.82m seat. Perspective guesses do not override those canonical contacts. Native R2 front/side/quarter images in `docs/p08/golden/unity/native-actors-20260927-0502` were inspected before editing.

R3 retains useful named R2 mechanical parts, then replaces its tank, tail skins, fairing/ducts, headlight housings, screen and mirrors. Every headlight has one main projector. Actual lower cooling slots are cut through the skins. The latest revision shares white/black lower fairing boundaries, encloses the underseat frame triangle, uses a planar tank front shoulder region, and seats the screen base against the cowl surface. It is not a production-ready or100% accepted asset.

`apex_r3_author.py` is a literal safe-mode Blender recipe; `apex_r3_nose.py` is its source fragment, copied into that literal recipe outside Blender. Source iterations01–05 are preserved under `ArtSource/P08/Golden/Apex/V8/R3/IterationXX`. Current saved editable source is `RB_Golden_Apex_r3_editable.blend`; current author/audit receipts end `-09-mcp.json`. Current source and staged FBX now use the final constrained panel topology; see README.md and handoff-manifest.json for the authoritative 83,380 / 41,690 / 16,278 triangle LOD results. All three levels pass the physical, manifold and UV gates.

An initial helper held a UV layer reference across `bmesh.to_mesh`, followed by a native Blender attribute-access crash. Only the verified task-owned9878 process was restarted; acquiring UVs after topology conversion resolved it. Later collinear polygon ears were replaced by centre fans or redundant boundary-vertex dissolution without lowering the1e-16 physical threshold.

The optional real-drilled-rotor experiment is preserved only in Iteration05 and separate tools/receipts. It produced24 collinear triangulation failures and was removed from the current revision when root correctly prioritized silhouette/cohesive bodywork. Current wheels use the preserved R2 parts. Do not promote the experimental rotor output.

Actual multiview renders exposed wrong panel intersections, an overly bare tail/subframe, a high detached screen, simplified tank shape and pale headlight glass. Those are genuine failures, not waived by mesh checks. New renders and a labelled lens-off diagnostic are required before any staged export. Root still owns native Unity calibration and acceptance; all earlier CanyonV16/GarageV1/V2/Ash sources remain frozen.

UV join correction: Blender merges UV layers by name. The author recipe now normalizes each existing active layer to `UV0_SurfaceMetres`, preserving values before joining. Inner white fairing skins use the shared graphite material, with an explicit outward hint before solidify; ray probes proved the former pale triangle under the nose was the opposite white inner skin. The lens-off control confirms the cavity itself is dark; the compound cover retains real glass reflection and remains visually unaccepted.

Final handoff is staged and frozen, with no Assets write by this agent. Root owns native publication/review. The previous Boolean and first LOD assemblies are rejected diagnostics; final source uses CDT with exactly three boundary loops and bounded collapsed-fragment removal after triangulation/validation.
