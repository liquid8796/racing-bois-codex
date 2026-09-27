# Canyon V19 — Far-chain composition studies

**Candidate03 is rendered and visually unaccepted. No Assets export, native
import, production binding, acceptance entry or mask change is made.**

The locked reference remains `ArtSource/Concepts/P08/Golden/canyon-v2.png`
(`83273dae6721d9f2c6f5d6bf4a6f39146322d8efeabc5cec0cb332e5a1cfa610`).
Compare these actual Blender renders with its corresponding top panel. The
frozen V17 candidate05 camera, lighting, color management and resolution are
retained through V18-02. Road, near cliffs, Bend and Opposite modules remain
unchanged. Only Far33–44 across three LODs are rebuilt.

## Actual visual findings

- **01:** front-facing stepped heightfields still exposed large flat closing
  planes and looked like a quarry wall. Preserved and rejected.
- **02:** four closed masses per module removed those closing planes, but the
  Far chain became repeated smooth block/cylinder steps with broad blank faces.
  Its nine angular joints and approximately0.34m erosion were too sparse and
  shallow for the large masses. Preserved and rejected.
- **03:** many smaller fractures, stronger metre-scale relief, varied tops and
  sloping lower talus make the previously blank faces more broken. Nevertheless,
  the chain still reads as continuous vertical corrugation, its horizontal
  bedding and setbacks are weaker than the reference, and its talus is an overly
  continuous repeated apron. It remains visibly unaccepted.

The useful next correction is broken horizontal cliff bands and staggered rock
faces with interrupted talus, rather than more uniform vertical noise. The
unchanged near cliff, overhanging Bend/Opposite shapes, rail, road, foliage,
valley composition and lighting retain their previously documented differences.
This study does not establish full Canyon fidelity.

Candidate03 also corrects02's upper-mass offset sign: the second upper mass is
now10m lower rather than10m higher. Both upper masses overlap the lower volume.
All new surfaces use the existing `Canyon_Sandstone` material and primary UVs
projected from world geometry at2.4m per repeat. No new material/image datablock
is introduced; no scan is anisotropically stretched for this candidate.

## Technical evidence and limits

All36 changed meshes pass the existing primary UV cross `>1e-14`, physical
triangle cross squared `>1e-16 m^4`, no duplicate-triangle and closed-manifold
checks. Candidate03 minima are0.00345733261838177 and0.00045388509170152247
respectively; every mesh has zero boundary/nonmanifold edges and positive
signed volume. The source audit compares616 other scene meshes exactly,
including vertices, topology, UVs, material slots, transforms and visibility.
Camera/light/world/color state and material/image membership also match.

| Candidate | Whole-scene LOD0 triangles | LOD1 | LOD2 |
| --- | ---: | ---: | ---: |
| 01 | 1,702,056 | 857,515 | 350,131 |
| 02 | 1,710,380 | 861,187 | 351,551 |
| 03 | 3,795,244 | 1,778,515 | 705,975 |

Candidate03 is a costly shape study, not an optimized runtime asset. No triangle
budget is raised and no performance acceptance is claimed. There is no FBX or
Unity validation for these new candidates.

The03 author receipt's fields `minimumJointSpacingMetres` and
`maximumJointSpacingMetres` describe **undeformed reference-plan arc intervals**
(3.94419–8.98602m;36–152 joints per closed mass). They are not a guarantee that
every final surface separation is3–10m: row scale, talus expansion, relief and
warping alter those distances. The receipt's `signedVolumeCubicMetres` values
are mesh-local signed volumes; `candidate03-transform-audit.json` records the
world determinant needed for conversion. These clarifications preserve the
original receipt rather than rewriting evidence to make a stronger claim.

`candidate03-inputs.json` freezes02 source/script/render plus the locked concept
and protected Club before authoring. `candidate03-review.json` binds the actual
render and independent inspection conclusions. `candidate03-freeze-manifest.json`
binds these studies, sources, scripts and receipts. Previous candidates are not
overwritten. Authoring and rendering used the owned direct pinned Blender MCP
on port9877 with safe mode enabled; no Unity/Jarvis or paid service was used.
