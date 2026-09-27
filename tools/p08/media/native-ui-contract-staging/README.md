# Installed native UI-tree contracts

This helper references only the installed Library production assemblies. It does
not link application/presentation source, load replacement production DLLs, edit
Assets, execute a Bootstrap, contact a server, or mutate PlayerPrefs/quality/display
settings. Compile is preparation; root alone executes it in Unity Editor.

```powershell
dotnet build tools/p08/media/native-ui-contract-staging/NativeUiContracts.csproj --no-restore
```

Load `bin/NativeUiContracts/Debug/netstandard2.1/RacingBois.Tools.NativeUiContracts.dll`
and call `RacingBois.Tools.NativeUi.NativeUiContracts.Run(projectRoot,
compiledProofPath, textUnionPath)`. The independently generated compiled proof
must have passed and match the actual loaded Application/Presentation/Bootstrap
MVIDs, DLL bytes and physical source checksums. Use the current root-owned proof
at `docs/p08/media/global-copy-compiled-sources-20260928.json`.

`authored-text-union.json` freezes all 394 global and 531 cinematic keys across
six locales, with source hashes. The run compares every native lookup to that
union. It then creates a uniquely owned preview scene/GameObject/UIDocument,
asserts no PanelSettings/panel, and constructs UI Toolkit elements from the exact
current UXML declarations. **Style nodes are deliberately omitted**; no USS/font
assets are requested. This verifies native bindings/state against the declared
hierarchy, not Unity UXML import, CSS/layout/rendering, input dispatch or focus.
The attached copied-font fixture is owned separately by p09/root.

Contracts cover six-locale main/quality/practice choices and opaque name/address
data, no locale-driven preference/quality/gameplay events, scoped status/error
copy, old MP tick600/event200 → menu → language change → new tick0/event1, no
same-race event replay, and no idle old-race panel resurrection. Career controls
retain account drafts and the exact pending CareerIntent while relabeling; an
explicit invocation of the real Clickable callback must emit that same intent
once. Multiplayer controls preserve room/join data and raw server-code routing;
an explicit CreateRoom method invocation must retain its intended payload.

Race view inputs are explicitly synthetic and are projected through installed
readmodel code; the fixture uses reflection for internal immutable read-state
construction and private display callbacks only. It does not claim earned race
or campaign progress. Multiplayer identity uses real production
MultiplayerSession/UnityWireCodec with an in-memory transport. No sockets or
persistent credentials are used. Returned JSON is CLR-serialized and says
`rendered=false`, `inputDispatchVerified=false`, `focusVerified=false`, and
`fullGameLocalizationAccepted=false`.

Global quality, display dimensions/mode, frame-rate/time-scale and the four
relevant PlayerPrefs entries are read before and after; any change fails rather
than silently restoring over a concurrent user choice. All owned sessions,
objects and the preview scene are cleaned in finally. Source/proof/union bytes
must remain unchanged. Root should additionally retain the original-font checks
coordinated with the separate attached renderer.
