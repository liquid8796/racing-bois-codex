# V7R2 native import, floor samples and Windows captures

Actual Unity import `d922112601bf473986f0eb64738614be` passed with unchanged input hashes. It checks primary UVs, materials, three LODs, rig and all 13 clips. The original V7 source, V7R1 UV repair, geometry/maps and the 12 other animation takes remain preserved.

The [native floor probe](native-floor-probe.json) uses the imported prefab and its actual `RiderAnimationSet` clip binding. It samples the 0.75-second clip at 145 times for each LOD, then separately runs the production `RiderAnimationView` through a 60Hz Riding-to-Falling blend. These are actual Unity `BakeMesh` measurements at root zero, without changing the clip or recorded input.

| Imported geometry | LOD0 | LOD1 | LOD2 |
| --- | ---: | ---: | ---: |
| Minimum Y over direct clip samples | 2.094 mm | 2.133 mm | 1.986 mm |
| Minimum Y during sampled Riding-to-Falling blend | 2.109 mm | 2.166 mm | 2.006 mm |

All measured minima remain above the flat ground plane. They differ from Blender's source minima because the FBX is resampled at whole source frames; both sets of measurements are retained. This closes the sampled flat-ground penetration defect, not every terrain, collision or animation transition.

The Windows x64 Mono/DX11 build `Build/PoseEnvelopePreview/20260927-ashv7r2-06` passed with zero errors/warnings, unchanged effective sources and restored Editor state. Fingerprint: `d3e89ea5a4c8d4732fe6cd61cbb17da2e72b90e4506fbb87d8295c6f99c48da1`.

The [owned launcher](../../../../p10/pose-envelope-native-staging/launch-6a7d4bb53ab74a8f8ab65069d47a4b59.json) exited normally with unchanged player files. The [independent verifier](../../../../p10/pose-envelope-native-staging/native-check-20260927-ashv7r2-06.json) verified 48 PNGs and 1,502 chronological samples. It records 59 missed slots and a maximum gap of 0.194 seconds; this is not a performance pass.

Inspected the actual forecast-wrecked envelope40 settled image and largest Riding-to-Falling midpoint against the preserved ground-origin05 run. The settled pose now places the hip/upper-arm side near the floor instead of supporting a hovering torso on the fingertips. Midpoint boots no longer show the earlier flat-ground penetration in these views. The original trace is still only a reconstructed pose pair; the displayed mode is Falling, not an invented authoritative wreck.

Movement still needs review for impact timing, slopes, self-contact, wrist/cloth deformation and gameplay camera comfort. Character likeness, materials and concept fidelity remain unaccepted. Neither the actor nor either staged smoothing variant was promoted to production content.
