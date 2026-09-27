# Spark 450 V1 — authoring specification, not acceptance

The actual [hero concept](../../../../../ArtSource/Concepts/P08/Golden/spark-v1.png) and [side reference](../../../../../ArtSource/Concepts/P08/Golden/spark-v1-side.png) were inspected before modeling. The hero is the design master. The generated side image retains slight perspective and is not a calibrated blueprint. Its prompt's “orthographic left side” wording does not establish a camera calibration or physical component sidedness.

Hero SHA256: `e358ecf1a809f5373aa45ef92cbd6897ed1e1693cacc73b0f6df697d91bedce6`.
Side SHA256: `ad5478c942350462a34d12b1ba9f9714cb00a595ff9465bc1d000cf6b5e7ad0b`.

The locked visual family is an original compact classic naked motorcycle: copper teardrop tank with cream inset and fine dark/cream boundary, long ribbed brown seat with modest rear rise and passenger strap, black tubular cradle frame and triangular side covers, finned parallel-twin engine with round dark cases, two rear coil shocks, telescopic fork, round headlamp, twin analog dials, round mirrors, amber indicators and a rear red lamp/bracket. Two satin-metal silencers are stacked on the visible flank. Cast wheels have narrow open spokes and perforated discs; they are not Apex's swept sportbike wheel/body treatment.

## Canonical authored dimensions

`VehicleDimensions.cs` defines a shared collision envelope, not wheel or rider-contact coordinates: half-width0.475m, half-length1.070m and height1.200m. The following are deliberate authoring decisions within that envelope, not measurements recovered from the images:

| Item | Metres / semantic coordinates |
|---|---|
| Wheelbase | 1.390 |
| Nominal tyre outside diameter | 0.630 |
| Wheel centers | left/right0; forward±0.695; up0.315 |
| Front / rear tyre section | 0.125 /0.160 |
| Rider seat contact | left/right0; forward-0.340; up0.800 |
| Grips | left/right±0.330; forward0.420; up1.020 |
| Foot contacts | left/right±0.270; forward-0.180; up0.335 |
| Mirror upper extent | At most1.200 |

Blender uses X/semantic-right, Y/forward, Z/up. Both source images visibly show the chain and stacked silencers on the same camera-facing flank. Root explicitly requires that visible relationship to be preserved. That flank is assigned semantic-right (+X) as an authored convention, not a physical sidedness fact recovered from the images. The chain's intended center plane is X+0.075m, inboard of the silencers at X+0.231/+0.243m and the rear brake plane at X+0.105m. Actual chain/frame/swingarm/rotor/pipe clearances must be checked; these nominal planes alone are not intersection proof. Wheel, steering and rider clearance must also be measured and verified in Unity; no canonical physics/source files are changed to accommodate the mesh.

Only original project-authored mechanical algorithms may be reused. No Apex body geometry and no downloaded GLB mesh, texture or rig enters Spark. A new scene/source preserves all existing Apex and Club files. Model silhouette and joined mechanisms are reviewed in real quarter/side renders before texture baking or export. Exact concept fidelity, technical production checks and native performance remain separate gates; this document grants no acceptance.
