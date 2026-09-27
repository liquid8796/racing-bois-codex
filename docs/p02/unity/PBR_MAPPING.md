# Barrier material mapping

The Blender source uses roughness 0.62. Its production metallic/smoothness PNG stores metallic 0 in red and smoothness about0.38 in alpha.

URP17.5 `Shaders/LitInput.hlsl` multiplies sampled mask alpha by `_Smoothness`. Therefore the barrier material's scalar is **1.0**, not0.38; multiplying twice would make the asset too rough. `FoundationBuilder.CreateBarrierPrefab` sets this explicitly. Normal and metallic/smoothness maps are assigned; map textures are non-sRGB, base color is sRGB.

The authored maps are intentionally simple/constant except the painted stripes; this validates the material pipeline, not a claim of final art detail.
