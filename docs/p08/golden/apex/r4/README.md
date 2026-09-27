# Apex R4 — original authored candidate, not visually accepted

R4 is a separate source/export revision for native comparison. The locked [bike concept](../../../../../ArtSource/Concepts/P08/Golden/apex-v2.png), [garage concept](../../../../../ArtSource/Concepts/P08/Golden/UI/garage-v2.png) and actual [R3 garage render](../../ui/r3-v7-focus-1920.png) were inspected before the changes. The bike concept SHA256 remains `f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819`.

Two publicly licensed motorcycles were inspected separately as mechanical references; their source, license and geometry findings are in [the reference assessment](../../../apex-base-feasibility-20260927/REPORT.md). **No donor mesh, texture, rig or material was incorporated into R4.** It retains project-authored R3 mechanisms and replaces or reshapes the named original project components below. It is not described as an entirely new scratch-built bike.

## Changes and evidence

- A new tank cross-section gives the shoulder an explicit crease and the knee area a real concavity. Broad surface character still differs from the concept.
- The main fairing is curved outward at the shoulder and recessed toward the frame at the knee. A closed stepped belly replaces the previous thin side planes.
- Two swept optical apertures have recessed projectors, cavity walls, protective lenses and a continuous lower nose return. The windscreen has compound curvature, a seated collar, narrow side supports and thicker mirror arms meeting those supports.
- A new rider saddle, raised passenger pad, continuous tail skin and exposed subframe replace the filled triangular under-seat panel. Ray tests exposed white tail skin intersecting the saddle; the clearance correction now returns the rider saddle at all five measured centerline points, including approximately0.824m at the contact point.
- Exactly two under-seat titanium cans have taller rounded-rectangle openings, rolled rims, liners, branches, mounting bands and brackets. This is original authored geometry.
- The old tyre “channels” were raised decorative tubes. Both tyres now have actual3.5mm-deep directional grooves in the closed mesh, at unchanged wheel centers and nominal diameter.

Actual assembled LOD0 views: [quarter](final-quarter.png), [side](final-side.png). Source-stage [front](06-front.png) and [rear](06-rear.png) show the same main cowl/outlet/tread geometry before the final narrowing of screen supports. Actual reduced-mesh views: [LOD1](lod1-quarter.png), [LOD2](lod2-quarter.png). All renders used direct Blender9878, Cycles CPU with four threads; no Jarvis or paid service was used.

## Material intent

[surface-intent.json](../../../../../ArtSource/P08/Golden/Apex/V8/R4/Textures/surface-intent.json) declares numerical base reflectance in **linear light**, stored using the explicit sRGB transfer function. Emission colors are also sRGB encoded. Normal, roughness, metallic and smoothness maps are linear data. This is an intentional R4 material revision, not proof of an earlier Unity engine bug.

The [PNG artifact check](texture-artifact-check.json) decoded the actual files, checked their hashes, measured the resulting mean reflectance and verified the metallic/smoothness channels. Images were loaded fresh, reloaded only after generation completed, and packed into the R4 source. R2/R3 maps were not changed. Native tint/reflection/opacity, compression and memory still require root's Unity review; bright studio renders do not establish the garage appearance.

## Technical results

| Gate | Actual final result |
|---|---|
| LOD0 / LOD1 / LOD2 triangles | 103,470 / 51,734 / 20,448 |
| Renderer meshes / material roles | 9 / 9 |
| Non-manifold edges, all LODs | 0 |
| Physical triangles with cross squared≤1e-16 | 0 |
| UV triangles with area<1e-12 | 0 |
| Actual FBX roundtrip | Exact renderer names and per-mesh triangle counts preserved |
| Minimum roundtrip world cross squared | 3.1613510299732803e-16 |

The minimum physical area is relatively close to the unchanged threshold; actual Unity import remains required. The attempted20µm micro-vertex cleanup merged **zero** vertices and did not improve this minimum, so it is not claimed as a geometry repair. The initial assembly had five UV triangles between the repair and audit thresholds. The repair condition was tightened to match the existing audit, and fresh checks passed. The earlier FBX is preserved as [`rejected-uv-stage-01.fbx`](../../../../../_local/p08-apex-r4-staging/rejected-uv-stage-01.fbx); it is not the current candidate.

Final technical receipts: [assembly](assemble-clean-mcp.json), [geometry/UV](audit-final-clean-mcp.json), [export](export-final-mcp.json), [roundtrip](roundtrip-final-mcp.json). UV overlap for shared manufactured-finish textures is intentional; a unique decal unwrap is not claimed. Physical marker conventions remain Blender X/right, Y/forward, Z/up; Unity must prove forward+Z, left-X, right+X and ground together.

## Handoff and remaining rejection reasons

[handoff-manifest.json](handoff-manifest.json) binds the editable and assembled sources, recipes, texture intent, staged FBX and the exact descriptor to use after copying. FBX SHA256: `4e57cfeaefe2e27643c17bb083b04acb15dd483276a02058f05e687f69c16841`. Root may run `python tools/p08/golden/apex_r4_manifest.py --publish` when Unity is ready; all30 destinations are checked before copying and a different published file is never overwritten. No production availability mask is promoted by this handoff.

**This is not a100% concept match.** The tank, fairing curvature and panel transitions remain simplified; the belly has visible longitudinal surface bands; the optics and screen reflections differ; mechanism/casting detail and exact material response are unresolved. LOD1 changes some tyre/groove shading, and LOD2 visibly loses rotor, lamp and small mechanical detail in the close diagnostic view. Native LOD transitions at their intended distances, geometry shading, materials, collider/prefab integrity and frame/memory measurements remain unverified. Technical checks cannot waive these visual gaps.

The protected Club SHA256 remains `553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f`; bound R3 sources/export and locked concepts remained unchanged. No Client/server/shared/probe source was edited during the frozen operational soak.
