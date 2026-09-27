# Native Mono milestone contract harness

This helper contains only fixture/test code. Its project has **no ProjectReference
and no linked production source**. It references the installed production
Application, Adapters, Protocol and Gameplay.Definitions DLLs plus Unity Core and
the already installed Newtonsoft package. All references have `Private=false`;
do not load copies of production DLLs from the helper output directory.

The fifteen scenarios reuse the frozen milestone correlation tests, with real
CareerSession request/callback, refresh/retry, endpoint switch and logout/login
paths. Synthetic positive rewards/progress are derived from actual shared
EconomyRules/CampaignRules. They do not represent an earned campaign.

Public immutable readmodel constructors are not available from an external
assembly (`MultiplayerProjection` itself is internal). The helper therefore
uses the actual public MultiplayerSession and UnityWireCodec with an entirely
in-memory IRealtimeTransport: synthetic JSON welcome/lobby/result packets pass
through production validation and projection. There are no HTTP/WebSocket calls,
live credentials, scene objects, persistent stores, authority edits or content
mask changes. All owned fixture sessions are disposed after the run.

To prepare the helper before milestone installation, its tracker adapter resolves
only public methods on `typeof(CareerSession).Assembly` by reflection. If the
reviewed production CareerMilestoneTracker is absent, execution fails. No internal
readmodel constructors are invoked by reflection, and no production testing seams
were added. A type inventory rejects helper-local copies of production namespaces.

After installing the reviewed milestone sources and completing Unity compilation
and independent source/DLL/PDB attestation, root can compile:

```powershell
dotnet build tools/p08/media/milestone-native-staging/NativeContracts.csproj --no-restore
python tools/p08/media/milestone-native-staging/freeze.py
```

Root alone loads the resulting
`bin/NativeContracts/Debug/netstandard2.1/RacingBois.Tools.NativeMilestoneContracts.dll`
in Unity and invokes:

```csharp
RacingBois.Tools.NativeMilestones.NativeMilestoneContracts.Run(
    expectedApplicationMvid, expectedProtocolMvid, expectedDefinitionsMvid)
```

Pass the MVIDs from the **independent compiled-source proof**, not values freshly
read inside the same assertion. These three must match the executing assemblies.
The helper additionally reports assembly paths, MVIDs and disk hashes. That report
does not replace root's separate check that current disk/source/PDB correspond to
the loaded native assemblies.

The returned CLR-serialized JSON retains every group result and assembly record;
it checks list counts after serialization. This avoids native JsonUtility list
registration for dynamically loaded helper DTOs. Only the production wire codec
uses JsonUtility on its actual installed protocol types.

`isMono` must be true. `passed=true` requires all fifteen groups and successful
cleanup. `actualNetwork`, `uiPlayback` and `fullCampaignAccepted` remain false.
The helper proves execution of the correlation contracts against real Mono-loaded
production classes, not actual campaign progression, rendering, user interaction
or release acceptance. Native execution is pending until root runs it.
