# P06 audio and cosmetic effects

All audio in `Assets/RacingBois/Audio/P06` is newly authored. No recovered/reference audio, instruments, recordings, loops, or melodies were copied. Unity MCP provider discovery reported `fal` available but unconfigured; no provider generation was attempted. The reproducible Python authoring source uses deterministic oscillators, filtered seeded noise, percussion envelopes and an original eight-bar instrumental phrase. It does not claim a named generative model produced these sounds.

These effects add no modeled 3D asset. Dust/sparks use billboard particles and skids use transient runtime trails. Any later modeled prop still needs a generated 2D concept before Blender authoring.

## Deliverables and evidence

- `tools/p06/audio/author_audio.py`: deterministic seed `6068796`, NumPy 2.4.6, 32 kHz 16-bit source WAVs.
- `tools/p06/audio/verify_audio.py`: independent WAV decode, source/file hashes, format, DC, silence, PCM clipping, four-times oversampled true peaks, one-shot edges and loop seam checks.
- `audio-manifest.json`: 17 exact source-file hashes and generator hash.
- `audio-validation.json`: all 17 clips pass; 7 loops pass continuity checks; source PCM 3,502,080 bytes, estimated fully decoded float storage 7,004,160 bytes.
- Actual Unity 6000.5.7f1 Core/Audio/ParticleSystem module compilation of all three presentation scripts passed with zero errors/warnings. This isolated compile checks API compatibility, not a Player run. Root integration owns the final Editor/browser receipts.

The highest PCM peak is 0.880. The highest measured four-times true peak is approximately 0.880. Loop continuity checks compare the wrap sample delta with 1.5 times the within-clip 99th percentile adjacent delta (minimum tolerance 0.003); every current loop passes, with the largest ratio approximately 0.179. Short loops are imported PCM to preserve these boundaries. The music is imported Vorbis; final compressed loop playback still needs an audible browser review.

| Content | Source duration | Playback |
|---|---:|---|
| Engine low / engine high | 1 s each | Periodic harmonic layers, crossfade from speed and authoritative gear |
| Tire / gravel | 2 s each | Ground/contact/speed/lean/deceleration response |
| Wind | 4 s | Speed-squared mix |
| Canyon ambience | 8 s | Low continuous environmental texture |
| Canyon Drive instrumental | 16 s stereo | Original 120 BPM, eight-bar D-minor motif |
| Body impact / crash | 0.32 / 0.75 s | Authority events only |
| Club / fist / chain / swing | 0.30 / 0.19 / 0.48 / 0.24 s | Authoritative hit and attack events |
| Gear shift | 0.14 s | Authority gear change envelope |
| Confirm / back / finish | 0.70 / 0.70 / 0.90 s | UI activation and finish feedback |

## Audio integration

After scripts compile, execute `tools/p06/audio/import-audio.cs.txt` using Unity MCP `execute_code`. It imports the 17 WAVs, sets 32 kHz, mono except stereo music, preload and DecompressOnLoad, PCM for short continuous loops, Vorbis for one-shots/music, explicit WebGL settings, and writes `Assets/RacingBois/Audio/P06/RB_P06_AudioBank.asset`. Repeat execution preserves existing GUIDs. A build must reference the complete bank from the saved scene/bootstrap, rather than loading source file paths at runtime.

```csharp
audioView.Initialize(AudioBank);
audioView.Render(world, local, active, screen.AudioEnabled, dt);
```

Keep the existing `Render` call. Call `UnlockFromUserGesture()` from a real user activation (pointer, keyboard or gamepad start/confirm); then call `PlayUi(true)` for a confirmation or `PlayUi(false)` for a back/cancel. The presentation gate alone does not prove a browser AudioContext resumed. Unity Web runtime owns that platform operation; verify audible output after actual input. Use the UI audio flag in every Render; `SetMuted(true)` stops ongoing voices immediately and the next Render synchronizes it with that flag. `OnDisable` also stops all sources.

There are exactly 15 AudioSources: seven loop sources and eight reused transient voices. No runtime clip generation, `PlayOneShot` accumulation, scene physics or per-frame managed collection creation. RPM derives from the immutable rider speed/gear. A gear change briefly reduces engine gain and triggers a short transient. Damage/crash/finish events duck music up to 70%, with a gradual release. Event IDs reject duplicate reliable/snapshot copies; events more than 45 ticks old are consumed silently after reconnect. Menu/race transitions and an obvious fresh race tick reset clear the event cursor. Call `ResetEvents()` explicitly when replacing a race without a transition if the new match can reuse event IDs at a high tick.

Eight simultaneous maximum transient gains use a 0.35 bus multiplier. Combining independent worst-case loop maxima with eight source true peaks gives a conservative pre-codec peak bound below 0.90; normal mixed content is considerably lower. This analytical budget is not a measured capture of Web playback or an acoustic loudness certification. Browser output level and subjective quality remain part of root/user playtesting.

## VFX integration

```csharp
effects.Initialize(Stage.Road, dustMaterial, sparkMaterial, skidMaterial);
effects.SetQuality(lowQuality);
effects.Render(world, local, active, dt, screen.ReducedMotion);
```

`RaceEffectsView` owns the new effects. Disable/remove the legacy impact-particle emission in `RaceStageView` when wiring it; the camera's bounded impact response can remain. Do not call both effects implementations for the same event.

Material requirements for root's builder:

- Dust: URP Particles/Unlit, transparent alpha blending, no depth write, vertex color, small radial alpha texture, no shadows.
- Spark: URP Particles/Unlit, additive blend, no depth write, vertex color, small soft radial texture, no shadows.
- Skid: URP Particles/Unlit or equivalent vertex-color unlit shader, transparent alpha, no depth write, **Cull Off**, no shadows. The trail renderer aligns its surface normal to the route grade.

Materials must be scene-referenced so the needed shader variants survive Web stripping. Use shared materials; the controller never clones one per rider. Particle rendering is world-space and colliders are disabled/not created. The core gameplay still owns all contact and damage decisions.

Bounds: sixteen rider dust/trail slots, six impact slots, at most 720 live particles (16 × 36 + 6 × 24). Each skid has a 2.4 s lifetime and 0.32 m minimum vertex spacing; movement corrections over 6 m clear its history. Dust only emits from grounded off-road riders, with a 75 m interest distance (45 m at low quality). Impacts older than 24 ticks are consumed silently, and only tracked riders within 65 m generate bursts (35 m at low quality). Slots are reused and cleared on retirement. Low quality processes at most eight rider slots and halves burst density. Reduced motion cuts dust/bursts to one quarter and clears previous spark bursts without replaying event IDs. The effects controller never adds camera shake, light flashes or screen distortion.

## Final review still required after root integration

Verify the complete bank and three materials are present, the removed legacy pool no longer double-emits, play/pause/destroy has no console warning, browser audio starts after interaction and can be muted, a full 16 s music wrap has no audible pop, engine gear shifts are readable at gameplay volume, skids follow road grade without z-fighting, dust reads at gameplay distance, reduced motion changes the live effect density, and multiplayer repeated event batches do not replay sounds/particles. Measure the actual Web build frame time/memory with this system enabled. PCM checks and isolated compilation do not substitute for these gates.
