"""Original P08 synthesis, composition and arrangement; no reference samples/notes.

Reference metadata is used only for role IDs and duration targets. Musical motifs,
harmonies, rhythm, voicings and sound design below are newly authored. This is an
electronic/synthetic score, not a claim to reproduce a live recorded rock band.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave

import numpy as np
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "ArtSource/P08/Audio"
RUNTIME = ROOT / "Assets/RacingBois/Art/P08/Audio"
REPORT = ROOT / "docs/p08/media"
RATE = 32000
TAU = 2 * np.pi


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seconds(length):
    return np.arange(round(length * RATE), dtype=np.float32) / RATE


def envelope(signal, attack=.004, release=.04):
    result = np.asarray(signal, dtype=np.float32).copy()
    a = min(len(result), max(2, round(attack * RATE)))
    r = min(len(result), max(2, round(release * RATE)))
    result[:a] *= np.sin(np.linspace(0, np.pi / 2, a, dtype=np.float32)) ** 2
    result[-r:] *= np.sin(np.linspace(np.pi / 2, 0, r, dtype=np.float32)) ** 2
    return result


def shaped_noise(duration, seed, center=1700, width=2400):
    n = round(duration * RATE)
    rng = np.random.default_rng(seed)
    spectrum = np.fft.rfft(rng.standard_normal(n).astype(np.float32))
    f = np.fft.rfftfreq(n, 1 / RATE)
    spectrum *= np.exp(-((f - center) / max(width, 1)) ** 2)
    spectrum[0] = 0
    result = np.fft.irfft(spectrum, n).astype(np.float32)
    return result / max(float(np.std(result)), 1e-9)


def pitched(midi, duration, timbre, seed=1):
    t = seconds(duration)
    freq = 440 * 2 ** ((midi - 69) / 12)
    if timbre == "bass":
        signal = np.sin(TAU * freq * t) + .24 * np.sin(TAU * 2 * freq * t) + .10 * np.sin(TAU * 3 * freq * t)
        signal *= np.exp(-t * 1.6)
    elif timbre == "guitar":
        # Palm-muted additive string: independent hammer transient and decaying odd partials.
        signal = sum(np.sin(TAU * freq * k * t + .12 * k) / (k ** 1.25) for k in range(1, min(18, int(14000 / freq))))
        signal = np.tanh(signal * 2.8) * np.exp(-t * 4.7)
        signal += .09 * shaped_noise(duration, seed, 3300, 1900) * np.exp(-t * 62)
    elif timbre == "bell":
        signal = np.sin(TAU * freq * t + 2.1 * np.sin(TAU * freq * 2.01 * t) * np.exp(-t * 4)) * np.exp(-t * 2.2)
        signal += .22 * np.sin(TAU * freq * 3.98 * t) * np.exp(-t * 5)
    elif timbre == "keys":
        signal = (np.sin(TAU * freq * t) + .32 * np.sin(TAU * freq * 2 * t) + .1 * np.sin(TAU * freq * 4 * t)) * np.exp(-t * 2.7)
    elif timbre == "brass":
        signal = sum(np.sin(TAU * freq * k * t) / (k ** 1.5) for k in range(1, min(10, int(14000 / freq))))
        signal *= (1 - .22 * np.cos(TAU * 5.1 * t)) * np.exp(-t * 1.4)
    elif timbre == "pluck":
        signal = np.sin(TAU * freq * t + 1.4 * np.sin(TAU * freq * 3 * t) * np.exp(-t * 7)) * np.exp(-t * 4.1)
    else:
        signal = (np.sin(TAU * freq * t) + .24 * np.sin(TAU * freq * 1.002 * t) + .11 * np.sin(TAU * 2 * freq * t)) * np.exp(-t * .35)
    return envelope(signal, .018 if timbre in ["brass", "pad"] else .003, min(.09, duration / 5))


def drum(kind, seed, character=0):
    length = {"kick": .45, "snare": .29, "hat": .13, "open": .42, "tom": .48, "ride": .75}[kind]
    t = seconds(length)
    if kind == "kick":
        signal = np.sin(TAU * ((44 + character * 2) * t + 3.3 * (1 - np.exp(-t * 27)))) * np.exp(-t * 15)
        signal += .09 * shaped_noise(length, seed, 2900, 1600) * np.exp(-t * 95)
    elif kind == "snare":
        signal = (.27 * np.sin(TAU * (160 + character * 7) * t) + .58 * shaped_noise(length, seed, 2500, 2900)) * np.exp(-t * 22)
    elif kind == "tom":
        signal = np.sin(TAU * (102 * t + .9 * (1 - np.exp(-t * 11)))) * np.exp(-t * 11)
    else:
        decay = {"hat": 55, "open": 12, "ride": 6}[kind]
        metal = sum(np.sin(TAU * f * t) for f in [3381, 4177, 5743, 7087]) * .11
        signal = (shaped_noise(length, seed, 6800, 3500) * .22 + metal) * np.exp(-t * decay)
    return envelope(signal, .001, .03)


def put(target, signal, at, gain=1, pan=0):
    start = round(at * RATE)
    if start >= len(target):
        return
    if start < 0:
        signal = signal[-start:]
        start = 0
    signal = signal[:len(target) - start]
    angle = (pan + 1) * np.pi / 4
    target[start:start + len(signal), 0] += signal * np.float32(gain * np.cos(angle))
    target[start:start + len(signal), 1] += signal * np.float32(gain * np.sin(angle))


# Explicit new motifs and progressions, not a source MIDI/PCM transcription.
SCORES = [
    ("amber-apex", "Amber Apex", 128, 38, [0, 5, 3, 7], [0, 7, 10, 12, 7, 3, 5, 10, 7, 5, 3, 2, 5, 7, 3, 0], "guitar", "straight"),
    ("switchback-radio", "Switchback Radio", 112, 43, [0, 8, 5, 10], [0, 3, 7, 5, 10, 7, 12, 10, 5, 3, 2, 7, 8, 5, 3, 0], "keys", "breakbeat"),
    ("concrete-comet", "Concrete Comet", 138, 40, [0, 3, 10, 5], [0, 2, 7, 14, 10, 9, 7, 5, 3, 7, 12, 14, 10, 7, 2, 0], "brass", "driving"),
    ("blue-hour-service", "Blue Hour Service", 104, 45, [0, 5, 10, 3], [7, 12, 10, 5, 7, 3, 0, 2, 5, 10, 12, 15, 14, 10, 7, 5], "bell", "halftime"),
    ("rival-frequency", "Rival Frequency", 122, 42, [0, 7, 3, 8], [0, 6, 7, 12, 10, 7, 6, 3, 2, 6, 10, 14, 12, 7, 3, 0], "pluck", "syncopated"),
    ("orchard-afterburn", "Orchard Afterburn", 116, 41, [0, 10, 5, 7], [0, 5, 9, 12, 14, 9, 7, 5, 4, 7, 12, 9, 5, 2, 4, 0], "guitar", "shuffle"),
    ("two-lane-covenant", "Two Lane Covenant", 132, 37, [0, 3, 5, 8], [12, 7, 3, 0, 2, 7, 10, 14, 15, 10, 7, 5, 3, 2, 7, 0], "brass", "breakbeat"),
    ("freight-of-light", "Freight of Light", 120, 44, [0, 5, 8, 10], [0, 3, 5, 7, 10, 5, 3, 12, 14, 10, 8, 7, 5, 7, 3, 0], "keys", "driving"),
    ("clutch-and-kindness", "Clutch and Kindness", 144, 46, [0, 7, 5, 10], [0, 4, 7, 11, 12, 7, 4, 2, 9, 7, 5, 4, 2, 5, 7, 0], "guitar", "straight"),
    ("dust-signal", "Dust Signal", 108, 39, [0, 8, 3, 5], [7, 10, 12, 15, 10, 7, 5, 2, 0, 3, 8, 12, 10, 8, 5, 3], "pluck", "halftime"),
    ("copper-weather", "Copper Weather", 126, 47, [0, 5, 3, 10], [0, 2, 5, 9, 7, 5, 2, 12, 14, 9, 7, 4, 5, 9, 2, 0], "bell", "syncopated"),
    ("ridge-line-promise", "Ridge Line Promise", 136, 36, [0, 3, 7, 5], [0, 7, 12, 10, 15, 14, 10, 7, 5, 3, 7, 10, 12, 7, 5, 0], "brass", "driving"),
    ("nightshift-meters", "Nightshift Meters", 100, 48, [0, 10, 8, 5], [12, 10, 7, 3, 5, 8, 10, 15, 14, 12, 8, 5, 3, 2, 5, 0], "keys", "shuffle"),
    ("warm-engine-home", "Warm Engine Home", 118, 38, [0, 5, 7, 3], [0, 4, 9, 7, 12, 9, 5, 4, 2, 7, 11, 14, 12, 9, 4, 0], "guitar", "breakbeat"),
    ("paddock-sunrise", "Paddock Sunrise", 88, 48, [0, 7, 5, 9], [0, 7, 9, 4, 2, 5, 11, 9, 7, 4, 12, 11, 9, 5, 2, 0], "keys", "halftime"),
    ("neon-receipt", "Neon Receipt", 96, 43, [0, 2, 7, 5], [0, 2, 9, 7, 14, 12, 5, 2, 7, 9, 16, 14, 12, 7, 5, 2], "pluck", "syncopated"),
    ("brake-light-waltz", "Brake Light Waltz", 90, 41, [0, 5, 8, 3], [0, 3, 8, 12, 10, 5, 3, 7, 12, 15, 10, 8, 7, 5, 3, 0], "bell", "shuffle"),
    ("blueprint-lull", "Blueprint Lull", 82, 45, [0, 3, 5, 10], [7, 3, 0, 5, 10, 7, 2, 3, 12, 10, 5, 7, 15, 12, 10, 7], "pad", "halftime"),
    ("found-the-line", "Found the Line", 106, 50, [0, 5, 7, 10], [0, 7, 5, 12, 14, 9, 7, 2, 4, 9, 12, 16, 14, 7, 4, 0], "brass", "straight"),
    ("meridian-lobby", "Meridian Lobby", 92, 40, [0, 8, 10, 5], [0, 5, 8, 10, 15, 12, 7, 5, 3, 7, 10, 14, 12, 8, 3, 0], "keys", "breakbeat"),
    ("last-light-repair", "Last Light Repair", 86, 47, [0, 5, 10, 8], [12, 7, 5, 2, 0, 5, 10, 14, 15, 10, 8, 5, 3, 7, 5, 0], "bell", "halftime"),
    ("quiet-pitlane", "Quiet Pitlane", 94, 38, [0, 7, 3, 5], [0, 3, 7, 10, 14, 12, 5, 7, 10, 15, 12, 8, 7, 3, 2, 0], "pluck", "shuffle"),
    ("the-short-way", "The Short Way", 102, 44, [0, 2, 5, 7], [0, 5, 9, 14, 12, 7, 4, 2, 5, 11, 14, 16, 12, 9, 5, 0], "guitar", "syncopated"),
    ("after-the-flag", "After the Flag", 98, 42, [0, 5, 3, 8], [0, 7, 10, 15, 12, 8, 5, 3, 2, 5, 8, 12, 14, 10, 7, 0], "brass", "straight"),
    ("safe-passage", "Safe Passage", 80, 46, [0, 5, 7, 9], [12, 9, 7, 4, 5, 9, 14, 16, 14, 11, 9, 7, 5, 4, 2, 0], "pad", "halftime"),
]


def music_spec(index, reference, minimum):
    identity, title, bpm, root, harmony, motif, timbre, groove = SCORES[index]
    bar_seconds = 240 / bpm
    bars = max(24 if index >= 14 else 48, math.ceil(minimum / bar_seconds / 8) * 8)
    # Every composition progresses through named sections; repeated themes are revoiced.
    names = ["opening", "verse-a", "answer-a", "lift", "verse-b", "bridge", "return", "closing"]
    boundaries = [round(i * bars / 8) for i in range(9)]
    sections = [{"name": name, "bar_start": boundaries[i], "bar_end": boundaries[i + 1],
                 "energy": [.34, .67, .76, .92, .71, .48, 1.0, .40][i],
                 "melody_variant": [0, 1, 2, 3, 4, 5, 6, 7][i]}
                for i, name in enumerate(names)]
    return dict(id=identity, title=title, kind="full-composition" if index < 14 else "short-score",
                bpm=bpm, root_midi=root, harmony_degrees=harmony, motif_semitones=motif,
                lead_timbre=timbre, groove=groove, bars=bars, duration_seconds=bars * bar_seconds,
                reference_role=reference, reference_minimum_seconds=minimum if index < 14 else None,
                sections=sections, seed=808100 + index * 997,
                arrangement_note="Eight directed sections with distinct orchestration, phrase endings, bass patterns, fills and melodic transformations. Repetition develops a theme; it is not sample/byte padding.")


def render_music(spec):
    beat = 60 / spec["bpm"]
    song = np.zeros((round(spec["duration_seconds"] * RATE), 2), dtype=np.float32)
    cache = {}
    percussion = {k: drum(k, spec["seed"] + i, spec["seed"] % 5) for i, k in enumerate(["kick", "snare", "hat", "open", "tom", "ride"])}

    def note(midi, dur, timbre):
        key = (midi, round(dur, 6), timbre)
        if key not in cache:
            cache[key] = pitched(midi, dur, timbre, spec["seed"] + midi)
        return cache[key]

    for section_index, section in enumerate(spec["sections"]):
        energy = section["energy"]
        for bar in range(section["bar_start"], section["bar_end"]):
            start = bar * 4 * beat
            chord_index = (bar // (1 if section_index in [3, 6] else 2) + section_index) % 4
            root = spec["root_midi"] + spec["harmony_degrees"][chord_index]
            major = spec["id"] in ["clutch-and-kindness", "warm-engine-home", "paddock-sunrise", "found-the-line", "the-short-way", "safe-passage"]
            third = 4 if major else 3
            # Drum pattern choices differ in structure; not only tempo or a random seed.
            groove = spec["groove"]
            kicks = {"straight": [0, 2], "driving": [0, 1.5, 2, 3.5], "breakbeat": [0, 1.5, 2.75],
                     "halftime": [0, 2.5], "syncopated": [0, .75, 2.5], "shuffle": [0, 1.66, 2, 3.66]}[groove]
            snares = [2] if groove == "halftime" else [1, 3]
            if section_index not in [0, 7] or bar % 2 == 0:
                for position in kicks:
                    put(song, percussion["kick"], start + position * beat, .47 * energy)
                for position in snares:
                    put(song, percussion["snare"], start + position * beat, .23 * energy, -.06)
            for pulse in range(8 if energy > .5 else 4):
                position = pulse * (.5 if energy > .5 else 1)
                if groove == "shuffle" and pulse % 2:
                    position += .15
                kind = "ride" if section_index == 6 and pulse % 2 == 0 else ("open" if pulse == 7 and bar % 4 == 3 else "hat")
                put(song, percussion[kind], start + position * beat, (.058 if pulse % 2 else .076) * energy, -.35)
            if bar % 8 == 7 and section_index not in [0, 7]:
                for hit in range(3):
                    put(song, percussion["tom" if hit != 1 else "snare"], start + (3.25 + hit * .25) * beat, .12 * energy, -.25 + hit * .25)
            bass_degrees = [0, 0, 7, 12, 0, 7, 0, third] if section_index % 2 else [0, 7, 0, 12, 0, third, 7, 0]
            for pulse, degree in enumerate(bass_degrees):
                if energy < .5 and pulse % 2:
                    continue
                put(song, note(root + degree, beat * .47, "bass"), start + pulse * beat * .5, .22 * energy)
            # Two rhythm parts use different voicings and stereo placement.
            for position in ([0, 1.5, 3] if section_index % 2 else [0, 2.5]):
                for degree in [0, 7, 12]:
                    put(song, note(root + degree + 12, beat * .75, "guitar"), start + position * beat, .040 * energy, -.62)
            for degree in [0, third, 7]:
                put(song, note(root + degree + 24, beat * 3.8, "pad"), start, .028 * energy, .53)
            if section_index in [0, 7] and bar % 2:
                continue
            # A and answer phrases have different contour, octave, and rests.
            for pulse in range(4 if energy < .8 else 8):
                ix = (bar * 4 + pulse + section_index * 3) % len(spec["motif_semitones"])
                motif = spec["motif_semitones"][ix]
                if section_index == 5:
                    motif = spec["motif_semitones"][-ix - 1]
                if bar % 8 == 7 and pulse == 3:
                    motif = 0 if section_index in [5, 7] else 7
                octave = 36 if section_index in [3, 6] and pulse % 3 == 0 else 24
                dur = beat * (.70 if pulse % 2 else .95)
                position = pulse * (1 if energy < .8 else .5)
                lead = note(spec["root_midi"] + motif + octave, dur, spec["lead_timbre"])
                gain = .070 * (.7 + energy * .3)
                put(song, lead, start + position * beat, gain, .15)
                put(song, lead, start + (position + .75) * beat, gain * .19, -.7)
                put(song, lead, start + (position + 1.5) * beat, gain * .075, .7)
    # Short crossfeed gives stereo space without hiding arrangement under reverb.
    delay = round(.019 * RATE)
    song[delay:, 0] += song[:-delay, 1] * .065
    song[delay:, 1] += song[:-delay, 0] * .065
    song -= np.mean(song, axis=0)
    song = np.tanh(song * 1.28)
    for channel in range(2):
        song[:, channel] = envelope(song[:, channel], .08, .3)
    return song


PHYSICAL = {
    "BMWLONG": ("engine-touring", "engine", 3.2, 53, .13),
    "BOUNCE": ("suspension-bottom", "impact", .48, 76, .18),
    "CHAINIMP": ("chain-link-contact", "metal", .65, 1870, .2),
    "CLUBIMPA": ("wood-grip-contact", "impact", .36, 310, .14),
    "CRASHHAR": ("crash-barrier-heavy", "crash", 1.4, 62, .3),
    "CRASHLIT": ("crash-shoulder-light", "crash", .64, 210, .13),
    "CRASHMED": ("crash-traffic-medium", "crash", 1.0, 105, .22),
    "ENGCAR11": ("traffic-four-cylinder", "engine", 2.8, 91, .18),
    "ENGNITRO": ("boost-pressure", "engine", 2.4, 173, .4),
    "ENGOTHER": ("opponent-engine", "engine", 2.0, 113, .22),
    "ENGRAT": ("street-single-engine", "engine", 2.0, 64, .12),
    "ENGSPORT": ("sport-twin-engine", "engine", 2.0, 128, .21),
    "ENGSUPER": ("apex-four-engine", "engine", 2.0, 192, .32),
    "ENGTUNNE": ("tunnel-engine-resonance", "engine", 3.0, 78, .3),
    "FOOTSTEP": ("boot-asphalt-step", "step", .24, 150, .11),
    "KICK_MW4": ("boot-side-contact", "impact", .29, 118, .26),
    "PUNCHHEA": ("glove-contact-heavy", "impact", .32, 84, .22),
    "PUNCHLIG": ("glove-contact-light", "impact", .19, 155, .1),
    "RIDERSLI": ("leather-road-slide", "slide", 1.6, 840, .27),
    "SIREN": ("patrol-long-call", "siren", 4.0, 680, .8),
    "SIRENFST": ("patrol-short-call", "siren", 2.0, 1020, 3.0),
    "SKIDOFFR": ("tire-gravel-drift", "slide", 2.0, 530, .6),
    "SKIDONNR": ("tire-asphalt-drift", "slide", 2.0, 1850, .22),
    "SWISHCHA": ("chain-air-sweep", "sweep", .45, 3400, .5),
    "SWISHGEN": ("glove-air-sweep", "sweep", .24, 1200, .2),
}


REACTIONS = [
    "ash-alert", "juno-surprise", "mako-warning", "rook-question", "sol-hold", "vale-ready", "echo-rev", "kai-wait",
    "ash-refuse", "juno-retort", "mako-stop", "rook-caution", "sol-question", "vale-startle", "echo-disbelief",
    "kai-confusion", "ash-concern", "juno-alarm", "mako-greeting", "rook-warning", "sol-effort", "vale-step-back",
    "echo-shock", "kai-protest", "ash-cheer", "juno-lookout", "mako-attention", "rook-startle", "sol-slow",
    "vale-effort-low", "echo-effort-high", "kai-effort-short", "ash-effort-hard", "juno-effort-soft", "mako-effort-deep",
    "rook-effort-burst", "sol-effort-long", "vale-help", "echo-refusal", "kai-surprise", "ash-victory", "juno-panic",
    "mako-tease", "rook-amused", "sol-challenge", "vale-tourist-alarm", "echo-step-aside",
]


def sfx_specs(reference):
    media = {x["path"]: float(x["format"]["duration"]) for x in reference["media"]}
    refs = [x for x in reference["manifest"] if x["path"].startswith("AUDIO/EFFECTS/")]
    reaction = 0
    output = []
    for index, item in enumerate(refs):
        stem = Path(item["path"]).stem
        if stem in PHYSICAL:
            name, family, duration, pitch, color = PHYSICAL[stem]
        else:
            name, family = REACTIONS[reaction], "reaction"
            duration = [.56, .72, .91, .48, 1.08, .64, .84][reaction % 7]
            pitch = [122, 216, 145, 103, 179, 234, 164, 133][reaction % 8]
            color = reaction
            reaction += 1
        duration = max(duration, math.ceil(media[item["path"]] * 100) / 100)
        output.append(dict(id=name, family=family, duration_seconds=duration, pitch=pitch, color=color,
                           seed=808200 + index * 173, reference_role=item["path"],
                           loop=family in ["engine", "siren"] or stem in ["SKIDONNR", "SKIDOFFR"],
                           semantic_mapping="New intended replacement role; source filename/literal evidence is not complete source event-branch proof.",
                           voice_policy="Original nonverbal formant synthesis, not a recording, voice clone or spoken source quote." if family == "reaction" else "Original physical synthesis; no source audio samples."))
    assert reaction == len(REACTIONS) and len(output) == 72
    return output


def render_sfx(spec):
    duration, pitch, color = spec["duration_seconds"], spec["pitch"], spec["color"]
    t = seconds(duration)
    family, seed = spec["family"], spec["seed"]
    if family == "engine":
        phase = TAU * (pitch * t + .07 * np.sin(TAU * 7 / duration * t))
        signal = sum(np.sin(k * phase + k * color) / k ** 1.2 for k in range(1, 18))
        signal = np.tanh(signal * (1.2 + color)) * (.79 + .21 * np.cos(TAU * (round(pitch * duration / 2) / duration) * t))
        signal += shaped_noise(duration, seed, pitch * 13, pitch * 10) * .09
    elif family == "siren":
        f = pitch + 240 * np.sin(TAU * color * t)
        phase = np.cumsum(f) * TAU / RATE
        signal = np.sin(phase) + .18 * np.sin(phase * 3)
    elif family == "reaction":
        # Six vowel trajectories and eight voices create nonverbal reactions with
        # distinct cadence, glottal contour and formant movement, not pitch-only copies.
        vowels = [(760, 1180, 2520), (330, 2120, 3010), (430, 910, 2510), (550, 1710, 2440), (295, 800, 2210), (640, 1420, 2740)]
        formants = vowels[int(color) % len(vowels)]
        glide = [1.28, .78, 1.09, .64, 1.5, .91, 1.18][int(color) % 7]
        base = pitch * (1 + (glide - 1) * t / duration + .025 * np.sin(TAU * (4 + int(color) % 3) * t))
        phase = np.cumsum(base) * TAU / RATE
        source = sum(np.sin(k * phase) / k for k in range(1, 24)).astype(np.float32)
        signal = np.zeros_like(t)
        for fi, center in enumerate(formants):
            bandwidth = [110, 160, 210][fi]
            radius = math.exp(-np.pi * bandwidth / RATE)
            angle = TAU * center / RATE
            signal += lfilter([1 - radius], [1, -2 * radius * math.cos(angle), radius * radius], source).astype(np.float32) / (fi + 1)
        pulses = [1, 2, 1, 3, 2, 1, 2][int(color) % 7]
        cadence = np.maximum(0, np.sin(np.pi * pulses * t / duration)) ** (.7 + int(color) % 3 * .45)
        signal *= cadence
        signal += shaped_noise(duration, seed, 2300 + 130 * (int(color) % 5), 2800) * .025 * cadence
    elif family in ["impact", "crash", "step", "metal"]:
        decay = {"impact": 19, "crash": 4.2, "step": 33, "metal": 9}[family]
        signal = np.sin(TAU * (pitch * t + .7 * (1 - np.exp(-t * 36)))) * np.exp(-t * decay)
        signal += shaped_noise(duration, seed, pitch * 4, max(600, pitch * 3)) * (.25 + color) * np.exp(-t * decay * 1.2)
        if family in ["crash", "metal"]:
            for ratio, gain in [(2.71, .21), (4.13, .12), (5.79, .08)]:
                signal += gain * np.sin(TAU * min(12000, pitch * ratio) * t) * np.exp(-t * decay * .63)
        if family == "crash":
            for bounce in [duration * .24, duration * .51]:
                mask = np.maximum(0, t - bounce)
                signal += (t >= bounce) * np.sin(TAU * (pitch * .71) * mask) * np.exp(-mask * 17) * .19
    else:
        signal = shaped_noise(duration, seed, pitch, pitch * .68)
        if family == "sweep":
            signal *= np.sin(np.pi * t / duration) ** (1.6 + color)
        else:
            signal *= .42 + .58 * np.sin(TAU * (17 if pitch < 1000 else 9) * t) ** 4
            signal += .12 * np.sin(TAU * (pitch * .61) * t)
    return envelope(signal, .002 if family in ["impact", "metal", "step"] else .012, min(.07, duration / 4))


def save_clip(identity, signal, spec, folder):
    signal = np.asarray(signal, dtype=np.float32)
    signal -= np.mean(signal, axis=0)
    peak = .76 if folder == "Music" else .72
    signal *= peak / max(float(np.max(np.abs(signal))), 1e-8)
    if signal.ndim == 1:
        signal = envelope(signal, .001, .004)
    else:
        for channel in range(signal.shape[1]):
            signal[:, channel] = envelope(signal[:, channel], .003, .004)
    pcm = np.rint(signal * 32767).astype("<i2")
    source = SOURCE / folder / ("RB_P08_" + identity + ".wav")
    runtime = RUNTIME / folder / ("RB_P08_" + identity + ".ogg")
    source.parent.mkdir(parents=True, exist_ok=True)
    runtime.parent.mkdir(parents=True, exist_ok=True)
    channels = 1 if pcm.ndim == 1 else pcm.shape[1]
    with wave.open(str(source), "wb") as f:
        f.setnchannels(channels); f.setsampwidth(2); f.setframerate(RATE); f.writeframes(pcm.tobytes())
    process = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(source),
                              "-c:a", "libvorbis", "-q:a", "4", "-map_metadata", "-1", str(runtime)], capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(process.stderr)
    return dict(id=identity, category="music" if folder == "Music" else "sfx", source=source.relative_to(ROOT).as_posix(),
                runtime=runtime.relative_to(ROOT).as_posix(), sourceSha256=digest(source), runtimeSha256=digest(runtime),
                sourceBytes=source.stat().st_size, runtimeBytes=runtime.stat().st_size, frames=len(pcm), sampleRate=RATE,
                channels=channels, seconds=len(pcm) / RATE, loop=spec.get("loop", True), recipe=spec,
                production_state="AUTHORED_AUDIT_PENDING", subjective_listening="PENDING", runtime_integration="PENDING")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["all", "music", "sfx"], default="all")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=1000)
    args = parser.parse_args()
    for directory in [SOURCE, RUNTIME, REPORT]:
        directory.mkdir(parents=True, exist_ok=True)
    reference = json.loads((ROOT / "docs/p08/content/reference-baseline.json").read_text(encoding="utf-8"))["data"]
    media = {x["path"]: float(x["format"]["duration"]) for x in reference["media"]}
    seen = set(); pcm_refs = []
    for item in reference["manifest"]:
        if item["path"].startswith("AUDIO/MUSIC/") and item["extension"] in [".RRA", ".WAV"] and item["sha256"] not in seen:
            pcm_refs.append(item["path"]); seen.add(item["sha256"])
    mids_refs = [item["path"] for item in reference["manifest"] if item["extension"] == ".MID"]
    scores = [music_spec(i, path, media[path] if i < 14 else 48 + (i % 4) * 8) for i, path in enumerate(pcm_refs + mids_refs)]
    effects = sfx_specs(reference)
    recipe_path = SOURCE / "composition-and-sound-design.json"
    recipe_path.write_text(json.dumps(dict(schema=1, originality="All motifs/harmony/instruments/reaction contours authored in generator. Reference metadata only; no audio/MIDI note sample input.", music=scores, sfx=effects), indent=2) + "\n", encoding="utf-8")
    manifest_path = REPORT / "audio-manifest.json"
    existing = json.loads(manifest_path.read_text(encoding="utf-8"))["clips"] if manifest_path.exists() else []
    by_id = {item["id"]: item for item in existing}
    jobs = []
    if args.only in ["all", "music"]:
        jobs += [(item, "Music", render_music) for item in scores[args.start:args.end]]
    if args.only in ["all", "sfx"]:
        jobs += [(item, "Sfx", render_sfx) for item in effects[args.start:args.end]]
    for index, (spec, folder, render) in enumerate(jobs):
        by_id[spec["id"]] = save_clip(spec["id"], render(spec), spec, folder)
        clips = sorted(by_id.values(), key=lambda item: (item["category"], item["id"]))
        manifest = dict(schema=1, generator=Path(__file__).relative_to(ROOT).as_posix(), generatorSha256=digest(Path(__file__)),
                        recipe=recipe_path.relative_to(ROOT).as_posix(), recipeSha256=digest(recipe_path),
                        expectedSfx=72, expectedFullCompositions=14, expectedAdditionalScores=11,
                        sourceMusicMinimumSeconds=3415.37415, clips=clips,
                        policy="Source WAV plus encoded OGG is one asset/composition, not two. Different hashes are not subjective quality or originality proof.")
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(dict(done=index + 1, total=len(jobs), id=spec["id"], seconds=by_id[spec["id"]]["seconds"])), flush=True)


if __name__ == "__main__":
    main()
