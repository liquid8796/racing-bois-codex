# Explicit constant-map import policy

The 22 entries in `constant-map-declarations.json` are now declared by role in
the staged descriptor's `constantMaps` arrays. The exact previous descriptor is
preserved as `descriptor-before-constant-maps.json`; the update receipt binds
both versions and the declaration file. No image bytes were changed or enlarged.

Opt-in maps must be original 4x4, 8-bit RGB/RGBA PNGs with all 16 decoded pixels
identical, including alpha. The importer verifies source hashes, checks the PNG
header before allocation, then uses an owned Unity decoder independently of
TextureImporter. The decoder is destroyed in `finally`. The imported texture
must still be 4x4 and keeps the ordinary base-color, normal, mask or emission
interpretation. Unlisted textures retain the existing minimum 256x256 policy.
Unknown/duplicate roles, missing inputs, bad dimensions and nonconstant pixels
are rejected; no rescaling, inflation or rebaking is permitted by this path.

Contract tests do not prove native PNG decoding or successful Unity import.
Root must run the source decoder and importer on the actual bound inputs.
Clearcoat/transmission differences and all visual/concept acceptance remain open.
