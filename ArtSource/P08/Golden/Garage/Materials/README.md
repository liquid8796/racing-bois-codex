# Garage surface source provenance

Eight original 2k PNG maps were downloaded from Poly Haven with upstream MD5 and local SHA256 validation. `PROVENANCE.json` records exact URLs, bytes and hashes. The geometry is authored locally from the locked generated concept; these are surface inputs only.

- [Hangar concrete floor](https://polyhaven.com/a/hangar_concrete_floor), nominal 2m tile.
- [Concrete wall 007](https://polyhaven.com/a/concrete_wall_007), nominal 2.2m tile.
- [Poly Haven asset license](https://polyhaven.com/license): CC0.

Each set supplies diffuse, OpenGL normal, roughness and occlusion. Unity exports use metallic in R, smoothness in A, and occlusion in G. Source scalar PNG precision is normalized before 8-bit packing. Authoring tint/coating adjustments are disclosed in each candidate's `textures.json`, while downloaded source files remain unchanged.
