# P08 original audio and real-time cinematic direction

The authored media library contains **72 original sound cues**, **14 full original compositions** (3546.87040625 seconds), **11 additional original short scores** (789.54434375 seconds), and **59 directed real-time sequences** (1674.5 seconds / 389 beats / 837 actor cues).

This is a production source and integration handoff. Signal/codec and compiled catalog checks passed; human listening, runtime mix, final 3D playback, staging, subtitle readability, skip behavior and browser memory checks remain open. Original reference event branches and exact semantic equivalence are not automatically proven by the new counts or durations.

The subsequent [runtime implementation](RUNTIME_INTEGRATION.md) adds the actual director/gallery/coordinator and one-element Web music streaming adapter. Conditional C# preflights and JavaScript bridge contract checks passed. Real Unity/browser playback and visual/memory receipts remain separate.

## Authorship and accounting

`tools/p08/media/author_audio.py` defines the new harmony, melodic motifs, rhythms, instrumentation, arrangement sections, oscillators, noise filters, envelopes and reaction contours. It reads reference **metadata only** to retain intended role IDs and duration targets. It never reads source audio samples or source MIDI notes. Every full composition has eight directed arrangement sections with different energy, voicing, bass pattern, phrase variation and fills. The 25 motifs are distinct; different motifs/hashes are an integrity check, not a subjective musical-quality rating.

The score is newly synthesized electronic music. It is not presented as a studio recording of a live rock band. Forty-seven reaction cues use original nonverbal formant synthesis; they are not natural recorded dialogue or voice clones. The remaining 25 cues synthesize engine, tire, patrol, impact, motion and contact roles. Source voice/event nuances and the final character/perceived-emotion match still require listening and contextual review.

WAV masters and their OGG encodings represent **one** authored asset each. No repeated files, decoded representations, mip levels, LODs or codec padding are added to content counts. The 14 full tracks each meet the unique PCM reference duration at a musical bar boundary, giving a measured library total above the 3415.374150-second reference. The additional 11 scores are new alternatives for unresolved MIDS roles, not claimed source transcriptions.

`reference-mids-analysis.json` covers all 11 research MIDS files / 104386 events. All exact note-event and onset/pitch fingerprints differ. The GRUNGE/SBK counterparts therefore cannot be declared identical from exact event comparison. Differences also do not prove separate compositions; arrangement and SoundFont perceptual equivalence remain unresolved. Eleven extra compositions avoid silently treating those roles as covered by unrelated source-name guesses.

## Files and integration API

| Artifact | Purpose |
|---|---|
| `ArtSource/P08/Audio/Music/*.wav` | 25 original stereo music masters |
| `ArtSource/P08/Audio/Sfx/*.wav` | 72 original mono sound masters |
| `ArtSource/P08/Audio/composition-and-sound-design.json` | Explicit score/arrangement and cue recipes |
| `Assets/RacingBois/Art/P08/Audio/**/*.ogg` | 97 compressed runtime imports |
| `audio-manifest.json` | Source/runtime hashes, duration, recipes and status |
| `audio-audit.json` | Full WAV/OGG decode and signal measurements |
| `audio-delivery.json` | Stable IDs, sourceWav, oggPath, durationSeconds, role, course assignment, suggested bundle and cinematic binding |
| `cinematic-storyboards.json` | New scene intent, shot/actor direction, text, duration and reference metadata |
| `cinematic-catalog-receipt.json` | Generator, storyboard and C# hashes |
| `cinematic-native-validation.json` | Actual compiled catalog checks |
| `music-preview.ogg` / `sfx-preview.ogg` | Listen-through excerpts; exact cue times in `preview-timeline.json` |

The original WAV library is **559711756 bytes**; the compressed OGG library is **56083293 bytes**. Those are measurements, not a reason to inflate content. Intended bundles split full music by route, each short score into its own optional pack, and sound effects into a shared pack. Assignments in this handoff are not proof that Unity has built or streamed the bundles.

The largest stereo track would occupy **106496000 bytes** as decoded float PCM. Load only the current music/score and release unused clips. Do not serialize all 25 tracks into the Race scene. Actual browser AudioContext, Unity memory, compression import, transitions and multiple simultaneous voice limits must be profiled during integration.

`CinematicCatalog` lives in `Assets/RacingBois/Client/Application/CinematicCatalog.cs`, under namespace `RacingBois.Client.Application`, with no Unity dependency. It exposes `All`, `Get`, `TryGet`, `ForRole` and `ForEvent`. Each immutable definition contains identity/title/synopsis/role/variant/duration, bike and character indexes, `MusicId` (`AudioId` alias), and beats. Each beat provides camera position/look-at/FOV endpoints, actor cues, text, speaker, transition and participant mask. `CinematicPoint` exposes X/Y/Z in meters relative to the stage, with +Y up and +Z forward. Actor slots are hero=0, rival=1, patrol=2, crew=3. Cues expose Slot/Action/PositionFrom/PositionTo/YawFrom/YawTo/Visible.

Actions use the existing rig vocabulary plus `Celebrate`, `Inspect` and `Converse` for directed procedural additives. The JSON retains higher-level directions such as a nod, handshake or walking; the normalized clip action is only the available animation input. The director must evaluate how those gestures actually look. The catalog cannot prove that a running clip is suitable for every recovery/standing transition.

Camera framing, dialogue, actor motion and beat timing are authored differently for each event story. The 15 showcases use distinct bike assets/features; sharing a shot vocabulary is intentional, not another model count. Long-form sequences follow an introduction, a 40-beat rivalry arc, a 30-beat personal route story for **Juno**, and a finale. All scenes must remain skippable and must never grant rewards or change authoritative race/economy state. Online race control takes precedence over optional scene playback.

## What the checks establish

All 97 source and compressed clips decode. The audit measures sample/4× oversampled peak, clipping, RMS, DC, loop/one-shot edges, exact declared duration, hash uniqueness and per-section energy. No source clip was silent or clipped. Three 0.48-second OGG files have a decoder-emitted quiet tail packet while their Vorbis granule duration remains exactly 15360 samples. The audit explicitly checks the declared duration, bounded extra packet and quiet tail; it does not count that padding as content. The initially strict decoded-length failure is retained in `audio-audit-before-codec-granule.json`.

The C# catalog was actually compiled and exercised with all 59 definitions. Validation covers IDs, role counts, lookup behavior, 389 continuous beat intervals, final duration, camera/actor bounds, participant masks, supported actions, music IDs and 59 distinct asset/choreography signatures. A different signature is not proof of dramatic or visual quality. Those checks remain separate from real-time playback and human review.

## Reproduce

```powershell
python tools/p08/media/author_audio.py
python tools/p08/media/audit_audio.py --preview
python tools/p08/media/analyze_reference_music.py
python tools/p08/media/author_cinematics.py
dotnet run --project tools/p08/media/CatalogChecks -- docs/p08/media/cinematic-native-validation.json
python tools/p08/media/write_delivery.py
```

Audio generation requires NumPy, SciPy and FFmpeg with libvorbis. `analyze_reference_music.py` reads the existing local P01 research JSON and emits fingerprints/metadata only. No research notes are embedded in the production scores. Runtime OGG container bytes can vary with encoder/version; published hashes bind the files that were actually measured. WAV source repeatability is checked separately from codec-container identity.

After Unity import, capture actual gallery/event playback, all skip routes, subtitles at 720p/1080p, representative audio transitions, mute/volume/reduced-motion behavior and memory on browser quality tiers. Keep ledger rows pending/partial until this evidence and semantic review support acceptance.
