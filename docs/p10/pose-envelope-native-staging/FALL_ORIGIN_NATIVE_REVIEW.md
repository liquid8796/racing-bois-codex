# Authored rider fall origin — native comparison

The production view now reads an explicit, validated visual offset from `RiderAnimationSet`. Existing prefabs and descriptors retain the legacy `-0.55m` default; a separate `RB_Golden_Ash_V6_GroundOrigin` candidate declares `0m`. Unity confirmed both defaults and the candidate value. Simulation, recorded height/mode, original clips, FBX and original prefab were not changed.

The Windows x64 Mono/DX11 build `Build/PoseEnvelopePreview/20260927-ground-origin05` passed with zero errors/warnings, unchanged effective source and successful Editor restoration. Fingerprint: `0b4a9b2bbb59a1bca2a101fd47a4b6a1e45bb4b62b6ab757b0b3b7622fd711ff`.

The [owned launch](launch-16daf4c3c23b4ff2b22923ca2d69edb2.json) exited normally with unchanged packaged files. The [independent verifier](native-check-20260927-ground-origin05.json) checked 48 actual camera captures and 1,484 observations. There were 79 missed sample slots and a maximum gap of 0.228 seconds. No performance acceptance is inferred.

Compared the forecast-wrecked envelope40 settled frame and largest Riding-to-Falling envelope40 midpoint against the preserved `resumed04` baseline. The settled body is now visible above the road rather than mostly buried. The midpoint also has the duplicate 55cm shift removed. These are actual separate runs, so small timestamp/camera differences are retained, not presented as pixel-identical conditions.

The original clip still reaches approximately -0.153m at its midpoint at root zero, as measured in [the native ground diagnosis](ashv6-native-ground-diagnosis.json). That requires an authored animation/contact repair. This patch does not accept that clip, the model's concept fidelity, camera comfort or either smoothing variant. Production content masks remain unchanged.

The Golden importer now saves only its own generated materials during import; it no longer calls a global asset save. This prevents an import operation from explicitly flushing unrelated user-owned dirty assets.
