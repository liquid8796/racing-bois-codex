# Native comparison resumed on 2026-09-27

The settings persistence defect is repaired. Unity rejects persistent project-settings objects in `SaveToSerializedFileAndForget`, while `SaveAssetIfDirty` does not persist those settings files. The builder now serializes owned transient copies of the three effective settings objects before freezing source hashes. It checks full memory and file state after building and restores original bytes, memory and dirty flags independently.

The real Windows x64 Mono/DX11 build `Build/PoseEnvelopePreview/20260927-resumed04` passed with zero errors/warnings, unchanged build-effective sources and successful Editor restoration. Its source fingerprint is `05e3ec1855f20d44d42878301a5d166b480a07f455ef54bd3df8b486fe93d2f7`. The owned process exited normally; its [launch receipt](launch-0de58b5399074e75a43f2867dce69352.json) confirms packaged bytes still matched afterward.

The [independent verifier](native-check-20260927-resumed04.json) checked all 48 actual engine PNGs and 1,492 chronological samples from [the run](captures-20260927-resumed04/run.json). No engine errors/warnings occurred. There were 69 missed sample slots and a maximum observed sample gap of 0.230 seconds; this short diagnostic is not a performance pass. Capture timestamps meet the verifier's comparison window.

## Observed images and remaining defects

Inspected the largest Riding-to-Falling unfiltered correction, envelope40 correction/midpoint, comparison20 midpoint, and forecast-wrecked envelope40 midpoint/settled images. The actors are visible with upright image orientation and actual materials; the road and orange/turquoise markers are diagnostic geometry. This is a reconstructed pose-pair comparison, not full historical WAN playback.

- The unfiltered correction places the rider outside the camera frustum. Its camera-space root is approximately `(0.0096,-3.1786,0.4298)`, 82.3 degrees below camera forward. The midpoint shows the rider again. The envelope correction retains a visible rider. This is camera framing, not a missing mesh.
- The rider visibly sinks through the road in settled Falling. All three variants converge to the same root at `y=-0.55` with zero envelope error. The production placement subtracts 0.55 metres even though Ash's authored fall already lowers and rotates the pelvis.
- A separate [actual Unity BakeMesh measurement](ashv6-native-ground-diagnosis.json) of the unchanged V6 prefab confirms final geometry spans `0.03497..0.78699m` at root zero, or `-0.51503..0.23699m` with the legacy offset. At age 18 the clip itself reaches `-0.15282m` even at root zero. Removing the duplicate legacy offset alone cannot accept the animation.

Neither envelope variant is accepted or installed into production by this run. Ground placement, authored fall contacts, camera behavior, concept fidelity and sustained player performance remain separate open gates. The original captures are retained unchanged for comparison.
