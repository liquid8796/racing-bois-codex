# Canyon material dependencies

The new Canyon geometry follows the inspected original Racing Bois canyon-v2 concept. Its ground/rock/asphalt surfaces use selected free **Poly Haven CC0** PBR texture inputs, not extracted Road Rash artwork. Attribution: https://polyhaven.com. Asset-specific source pages, original download URLs, upstream MD5, local SHA256 and byte sizes are preserved in PROVENANCE.json.

Inputs: rock_face, asphalt_02, brown_mud_rocks_01; each has2k diffuse, OpenGL tangent normal, roughness, AO and displacement. Read their file metadata and actual images before assigning scale/color. Licensed inputs are dependencies, not falsely described as textures painted entirely from scratch. Golden Unity masks must explicitly map metallicR and smoothnessA; roughness cannot be dropped directly into that slot.

Primary license: https://polyhaven.com/license. API usage reviewed at https://polyhaven.com/our-api on2026-09-27; public endpoints are free, including commercialuse. No paid API/service/marketplace used. No Jarvis MCP used.
