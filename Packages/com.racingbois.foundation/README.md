# Racing Bois foundation 0.1.0

This embedded package is the single source of truth for the P02 shared definitions, integer road-space transport fixture and wire DTOs. .NET projects under `src/Shared` compile these files by link. Do not copy them to a second runtime folder.

Assemblies:

- `RacingBois.Gameplay.Definitions`: versioned constants for the prototype.
- `RacingBois.Simulation`: integer millimeters, millimeters/second, fixed 60 Hz. No Unity, transport, clock, filesystem, threads or RNG.
- `RacingBois.Protocol`: public-field DTOs compatible with Unity JsonUtility and System.Text.Json with `IncludeFields=true`.

The simulation is newly authored solely to exercise authority, correction and transport. It is not recovered Road Rash movement, a final physics controller, combat, AI or parity evidence. The development content fingerprint `p02-foundation-v1` is a compatibility identifier; production asset/content hashing and schema validation remain later work.

Golden replay: start from `default(RiderState)`, step 300 times with `new RiderInput(1000, 0, 0)`. Expect `DistanceMillimeters=150500`, `SpeedMillimetersPerSecond=60000`, zero lateral/distance/acceleration remainders. Native and Unity Web must each run this fixture; sharing C# source alone does not prove cross-build determinism.

No extracted original-game asset or code is included.
