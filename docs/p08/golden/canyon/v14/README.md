# Canyon V14 — technical pass, visual hold

The frozen descriptor is `descriptor.json`. Native Unity confirmed the physical-unit geometry checks and the 217-module/651-renderer layout, shared bounds and preserved source meshes/transforms; see `unity-modules.json`.

The earlier raw-local triangle count was not a valid physical-area result because imported renderer scale is 100. The validator now transforms triangle edges into physical metres without weakening the 1e-16 cross-squared threshold. Do not report the earlier unscaled count as verified physical degeneracy.

Actual opaque Unity renders exposed open scan backs and hollow patches. Forcing LOD0 did not remove them; a temporary instance-only two-sided material diagnostic did. This is a visual/geometry-closure failure, so V14 is not production-accepted. Source FBX/materials remain frozen while V15 adds actual closed backing geometry.

No production mask or course collision logic was changed. Rendering quality, concept fidelity and player performance are not accepted by the structural module receipt.
