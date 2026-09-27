# P03/P04 final verification checklist

Use the current source and final Web artifact for acceptance. Old P02 receipts and an Editor screenshot do not establish the P03/P04 browser result.

## Native/shared checks

Run from the project root after gameplay/protocol edits are settled:

```powershell
dotnet run --project src/Tests/RacingBois.Gameplay.Tests -c Release
dotnet run --project src/Tests/RacingBois.RaceIntegration.Tests -c Release -- docs/p03p04/backend/application-integration.json
dotnet run --project src/Tests/RacingBois.Foundation.Tests -c Release -- docs/p03p04/backend/foundation-regression.json
dotnet run --project src/Server/RacingBois.Server.Host -c Release -- --SelfTest
```

Require nonzero test counts and zero failures. Integration checks include an entire 20,000-tick race against client snapshot validation, maximum protocol payload, local/core equivalence, immutable publication, authority ownership and actual damage. Preserve the source/build identity next to final receipts.

## Editor and original-asset checks

- Force Unity script import/compile, wait for completion, then inspect Console; an old loaded assembly is not a fresh compile.
- Run `RaceAssetBuilder.Setup()` and its independent `Validate()`. Confirm all generated prefabs import at the intended meter scale with LODs, normals/tangents/UVs, one appropriate collider, shared URP material, identity root and no missing references.
- Compare the final imported vehicle bounds with the shared collision dimensions, including van height. The gameplay collision proxy is authoritative; prefab colliders are disabled during runtime presentation.
- Enter Play mode from the saved race scene. Check a local start, attack/kick side, crash/recovery, restart and return to menu. Preserve a real GameView screenshot including UI.
- Check current authored FBX/texture provenance and independent mesh audit. A successful import does not turn a failed mesh audit into a pass.

## Release Web build

- Build to a fresh versioned output folder using the final saved scene and current scripts. Capture Unity build result, errors/warnings, compression and artifact sizes/hashes.
- Publish the matching server to a fresh folder. Only after both artifacts are ready, stop the previously recorded task-owned host and start the new executable with the exact new WebRoot. Preserve process identity and root marker.
- Confirm `/health` reports race protocol v2 and gameplay rules/content expected by the Web build. Keep the preserved P02 fixture isolated.

## Browser acceptance

- Load the final Web page normally with the trusted local certificate. Verify initial menu text, responsive layout and no browser/Unity errors.
- Start local play with no game-server WebSocket. Drive, brake, steer, corner, hill/landing, attack left/right, kick, crash/run/remount, result/restart and menu must remain usable. Inspect at gameplay camera distance.
- Verify zeroed inputs on focus loss, clear cruise-control state on return/restart, endpoint validation and recovery from a disconnected server.
- Connect the same build through WSS, observe remote riders and increasing authoritative ACK/tick, then leave/reconnect without stale views or identity. Native WSS is supporting evidence; this browser check is separate.
- Record viewport, browser/device, warm-up/duration, frame-time p50/p95, memory, entity/traffic count, local/online mode and route segment. Distinguish browser frame timing from simulation execution time. A single menu FPS observation is not a driving benchmark.
- Review both low-motion mode and sound toggle. Final art/animation polish and broad hardware/browser coverage remain P06/P10 gates.

## Live authority regression when relevant

Only rerun after a relevant gameplay/protocol/host change. Start the current host on unused loopback ports, then run the eight-client scenarios sequentially:

```powershell
dotnet run --project src/Tests/RacingBois.RaceIntegration.Tests -c Release -- --live ws://127.0.0.1:17920/ws docs/p03p04/backend/live-ws.json
dotnet run --project src/Tests/RacingBois.RaceIntegration.Tests -c Release -- --live wss://localhost:17921/ws docs/p03p04/backend/live-wss.json
```

Require both receipts `PASS`, then stop the exact task-owned probe process and verify its listeners closed. This loopback test does not close P05 multi-machine Internet/LAN gates.

## Claims and remaining gates

Record recovered rules separately from newly tuned physical units, AI and animation timings. Native reference side-by-side measurements remain necessary before asserting exact Road Rash parity. One authored test route does not satisfy the future five-course/full-content requirement, and P03/P04 local progress is not the P07 online economy.
