# Canyon V16 candidate

This candidate closes the open CC0 scan skins and removes duplicate source faces. It remains **visually unaccepted** against `canyon-v2.png`; native Unity rendering and review are required. No production content mask is changed.

V15 created finite, outward closed backs with bounded simple extrusion. V16 preserves that geometry while normalizing 489 redundant faces that Blender's FBX importer otherwise discarded. The current saved source and FBX now have exactly matching per-mesh triangle counts for all 651 renderers: 1,631,580 / 830,091 / 340,515 across the three LODs. The actual FBX roundtrip found no physical triangle with cross-product squared at or below `1e-16` square-metres squared. All road/paint/shoulder front faces point upward.

`descriptor.json` binds 50 hashed inputs, including the immutable concept, saved source, FBX, material maps, and 217-module LOD mapping. `restPose` is explicitly `file`. The candidate has no contact colliders; course authority and collision integration remain separate work.

Evidence: `normalize-mcp.json`, `source-audit-mcp.json`, `exact-roundtrip-mcp.json`. Earlier V13 raw-local triangle failure counts were affected by a Unity validator unit error: imported renderers had scale 100, so those counts do not prove equivalent physical-metre degeneracy. Root corrected the validator and proved scale invariance before native V14 validation.

FBX SHA256: `bc731bbf85aefbd98d12f73a5e6320b4eeb5d33c5981a2ea11e1ab9debde81ea`.
Module map SHA256: `e7e89b494e3cd466444b592e51514e972902576585a0f9465277846d09ee888a`.
