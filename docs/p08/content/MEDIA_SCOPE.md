# P08 media scope and acceptance boundaries

This register measures the supplied mod snapshot, not a complete universe of every Road Rash release. Counts and durations were recomputed from the P00/P01 manifest and fully decoded media metadata, then all 374 original file hashes were rechecked read-only. See `reference-baseline.json` for portable metadata and original/upstream SHA-256 values. Original images/audio/video remain outside production.

**P08 authoring update:** the subsequent [media handoff](../media/README.md) contains 72 new cues, 14 full new compositions, 11 additional short scores and 59 real-time sequence definitions. Signal/codec and compiled direction checks pass. This baseline document's semantic, contextual listening and playback gates remain applicable; library counts are not a completed acceptance claim.

## Audio and music

| Reference group | Files | Unique file hashes | Gross duration | Deduplicated duration |
|---|---:|---:|---:|---:|
| PCM sound effects | 72 | 72 | 29.140763 s | 29.140763 s |
| PCM music | 15 | 14 | 3508.591973 s | 3415.374150 s |
| RIFF/MIDS music | 11 | 11 | Not added to PCM duration | Arrangement/composition equivalence unresolved |
| SoundFont 1.0 | 6 | 6 | Instrument dependencies | Not six more compositions |

`SG_KICKS.RRA` and `SG_KICKS.WAV` are an exact duplicate. Five `GRUNGE*` and five `SBKGRNG*` names suggest counterparts, but filenames alone do not prove identical compositions or complete instrument playback. The ledger therefore retains each unique source file while leaving the independent composition total unknown. It does not claim 25 original compositions from 14 PCM files plus 11 MIDS.

P06 supplies 17 original synthesized clips: seven loops and ten one-shot cues, including one original music loop. Their authoring script, note sequences, source manifest, clipping/loop audit and durations are hash-bound in the production registry. This does not cover the complete original voice palette, bike/traffic/police timbres, crash intensities, footsteps, tunnel/boost behavior or music library. Candidate matches for obvious filenames such as `CHAINIMP` remain **partial**, because exact event selection and acoustic equivalence are unproven.

For each new cue, preserve an original synthesis/recording/composition project, intended event, intensity/variation, duration, loop behavior, gain and concurrency policy. Verify audible playback and contextual mix after implementation. New voice or music identities should be intentionally directed; changing pitch/seed or rendering the same phrase into many files cannot manufacture meaningful parity. Do not use original samples, melodies, stems or re-encoded audio.

## Cinematics and showcases

61 AVI files contain 59 unique byte streams. Gross duration is **1697.933334 seconds**; the unique-file total is **1660.000000 seconds**. `START.AVI` duplicates `START4.AVI`, and `WIN.AVI` duplicates `WIN1.AVI`.

| Source filename family | Unique files | Deduplicated seconds | Role confidence |
|---|---:|---:|---|
| RAT / SPORT / SUPER | 15 | 120.666665 | Bike showcase family; exact SPEC-to-filename association still needs evidence |
| BUSTED | 6 | 143.800001 | Filename suggests arrest outcomes; exact branch selection unresolved |
| START | 6 | 62.666667 | Filename suggests race-start variations; exact branch selection unresolved |
| WIN | 6 | 177.733333 | Filename suggests winning outcomes; exact branch selection unresolved |
| LOSE | 10 | 221.733332 | Filename suggests losing outcomes; exact branch selection unresolved |
| WRECK | 6 | 152.066667 | Filename suggests wreck outcomes; exact branch selection unresolved |
| LEVEL | 6 | 175.733334 | Numbered progression family; six files do not imply six campaign levels |
| INTRO | 1 | 86.266667 | Intro filename; staging/story role requires visual/runtime review |
| DUEL | 1 | 280.066667 | Named standalone clip; do not assume exact gameplay trigger |
| JESSIE | 1 | 195.266667 | Named standalone clip; do not infer a playable character identity |
| FINALWIN | 1 | 44.000000 | Finale filename; exact trigger/state remains a review item |

These families are planning hints. The upstream trigger audit found literal references for 89 of 148 audio/video files, and it explicitly leaves full event-branch semantics open. A filename, pointer match or successful decode cannot close the selection/trigger requirement.

A new cinematic requires original shot direction, camera/staging, animation, lighting, sound, timing, and an actual product integration point. Real-time Unity sequences are acceptable replacements when documented and reviewed as such; they need not imitate a 1990s video codec or repeat its exact byte size. Showcase variations must communicate each bike's actual design. Changing a tint or swapping only a caption is insufficient to claim independent event/story content.

The 12-second P06 combat/recovery capture is evidence of game animation. It is a QA artifact, not an authored replacement for any of these 59 unique clips. A looped still, repeated camera orbit, padded duration or a source video re-encode also cannot close the library gate.

## Work split and final gate

1. Review the reference atlas/filmstrip/runtime context and group genuinely shared compositions, events and scene roles. Keep unknowns explicit.
2. Write original direction for music, voice/effects and cinematic storyboards; generate and inspect 2D concepts before any new 3D assets used by those sequences.
3. Author sources and production outputs with stable semantic IDs, declared shared dependencies and meaningful distinctions.
4. Integrate event triggers, mute/reduced-motion/skip behavior, replay policy, subtitle/localization behavior and route/content packaging.
5. Capture playback, contextual audio mix, frame-time and memory evidence on browser quality tiers; include all required assets in the offline LAN distribution.
6. Close ledger rows only after explicit semantic mapping and real QA. Keep the duration/library measurements visible, but assess content sufficiency by verified roles and meaningful variety rather than padding to 503 MB.

This document does not silently remove the original P08 requirement for media. If final production deliberately combines or omits source roles, record the concrete product decision and evidence; do not declare an unmapped row complete by renaming it.
