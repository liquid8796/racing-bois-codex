# Candidate 05 descriptor bounds correction

Native import attempt `f1fae1f4f9f241669d004ad4f1295d20` failed the declared
physical envelope. The failure and original descriptor/source/FBX remain intact.

The original publisher used the source audit's union across all three LODs.
`GoldenSampleBuilder.ValidateAsset` consumes only LOD0 when accumulating
`CurrentGeometryBounds`, which transforms actual mesh vertices. The incorrect
union mixed LOD1's minimum height with LOD2's maximum height; this overstated
the expected vertical size. This was a descriptor measurement error, not grounds
for widening tolerance or changing geometry.

Independent read-only measurements of the same frozen source and FBX show:

| Measurement | X size | Y size | Z size |
| --- | ---: | ---: | ---: |
| Source LOD0 | 850.0 | 200.9237442 | 1538.0 |
| Actual FBX reimport LOD0 | 850.0 | 200.9238358 | 1538.0000019 |
| Root native Unity LOD0 | 850.0 | 200.9238 | 1537.99988 |
| Original all-LOD union | 850.0066833 | 201.3190002 | 1538.0012817 |

All 217 LOD0 meshes are covered. The minimum/maximum Y extrema come from
`Canyon_L0_Opposite_32` and `Canyon_L0_Far_36` in both the FBX and native probes.
The read-only FBX audit restores exact object, mesh, material and image membership;
it saves no source and exports no new FBX. Root's independent native receipts
are `native-lod0-bounds.json` and `native-lod0-y-extrema.json`.

`candidate05-descriptor-r1.json` changes only `minimumSize`, `maximumSize` and
`maximumBelowGround`. The dimension envelope remains measured LOD0 size ±0.05
metres, and the below-ground allowance remains measured LOD0 minimum +0.01 metres.
Source, FBX, textures, module mapping, camera recipe, geometry and UVs are unchanged.
`candidate05-publication-r1.json` binds the correction and preserved failed attempt.

Root should verify the new handoff, then import the new descriptor through the
existing strict native importer. No FBX copy or optimization install is required:

```powershell
& .\_local\blender-env\Scripts\python.exe tools/p08/golden/canyon_v17_bounds_r1/prepare_revision.py verify
```

The subsequent native import result must be recorded separately. This correction
does not grant visual acceptance; the recorded concept discrepancies remain open.
