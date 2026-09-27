"""Reproducible original Racing Bois sound library. No samples or network inputs.

Requires numpy. All notes, oscillators, noise, percussion and envelopes are authored
here. Circular placement preserves percussion/reverb tails across the music loop.
"""
from pathlib import Path
import hashlib
import json
import math
import wave
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "Assets/RacingBois/Audio/P06"
REPORT = ROOT / "docs/p06/audio-vfx"
RATE = 32000
RNG = np.random.default_rng(6068796)
TAU = 2 * np.pi


def time(seconds):
    return np.arange(round(seconds * RATE), dtype=np.float64) / RATE


def noise(seconds, center=0, width=1, lowpass=6000):
    n = round(seconds * RATE)
    frequencies = np.fft.rfftfreq(n, 1 / RATE)
    spectrum = np.fft.rfft(RNG.standard_normal(n))
    response = np.exp(-(frequencies / lowpass) ** 4)
    if center:
        response *= np.exp(-((frequencies - center) / width) ** 2)
    spectrum *= response
    spectrum[0] = 0
    samples = np.fft.irfft(spectrum, n)
    return samples / max(np.std(samples), 1e-9)


def attack_release(samples, attack=.005, release=.025):
    samples = samples.copy()
    a, r = min(len(samples), round(attack * RATE)), min(len(samples), round(release * RATE))
    samples[:a] *= np.linspace(0, 1, a) ** 2
    samples[-r:] *= np.linspace(1, 0, r) ** 2
    return samples


def add_wrapped(target, samples, at, gain=1, pan=0):
    indices = (np.arange(len(samples)) + round(at * RATE)) % len(target)
    if target.ndim == 1:
        np.add.at(target, indices, samples * gain)
    else:
        angle = (pan + 1) * np.pi / 4
        np.add.at(target[:, 0], indices, samples * gain * np.cos(angle))
        np.add.at(target[:, 1], indices, samples * gain * np.sin(angle))


def note(midi, duration, metallic=False):
    t = time(duration)
    f = 440 * 2 ** ((midi - 69) / 12)
    v = sum(np.sin(TAU * f * k * t) / (k ** (1.4 if metallic else 2.0)) for k in range(1, 8))
    v += .12 * np.sin(TAU * (f * 1.004) * t)
    v *= np.exp(-t * (3.5 if metallic else 2.3))
    return attack_release(np.tanh(v * 1.25), .007, .065)


def percussion(kind):
    t = time(.32 if kind == "kick" else .22)
    if kind == "kick":
        phase = TAU * (47 * t + 2.8 * (1 - np.exp(-t * 30)))
        return attack_release(np.sin(phase) * np.exp(-t * 19), .001, .02)
    if kind == "snare":
        v = .68 * noise(.22, 1900, 1700) + .32 * np.sin(TAU * 175 * t)
        return attack_release(v * np.exp(-t * 26), .001, .02)
    return attack_release(noise(.22, 6500, 3000, 12000) * np.exp(-t * 62), .001, .025)


def music():
    # Eight bars / 120 BPM. Original D-minor motoric phrase, no melody quotation.
    song = np.zeros((RATE * 16, 2), dtype=np.float64)
    kick, snare, hat = (percussion(k) for k in ("kick", "snare", "hat"))
    roots = [38, 38, 34, 34, 41, 41, 36, 36]
    for bar, root in enumerate(roots):
        start = bar * 2
        for beat in (0, 1, 2, 3):
            add_wrapped(song, kick, start + beat * .5, .45)
        for beat in (1, 3):
            add_wrapped(song, snare, start + beat * .5, .20, .05)
        for pulse in range(8):
            add_wrapped(song, hat, start + pulse * .25, .042 if pulse % 2 else .055, -.28)
            bass_midi = root + ([0, 0, 12, 0, 7, 0, 12, 7][pulse])
            add_wrapped(song, note(bass_midi, .29), start + pulse * .25, .23)
        for offset, semitone in ((.0, 0), (.75, 7), (1.5, 12)):
            stab = note(root + 24 + semitone, .63, True)
            add_wrapped(song, stab, start + offset, .11, -.55 if offset == 0 else .55)
            add_wrapped(song, stab, start + offset + .375, .028, .65 if offset == 0 else -.65)
    return song


def library():
    t = time(1)
    low = sum(np.sin(TAU * 65 * k * t + k * .11) / k ** 1.15 for k in range(1, 11))
    high = sum(np.sin(TAU * 130 * k * t + k * .31) / k ** 1.12 for k in range(1, 13))
    yield "engine_low", np.tanh(low * 1.3), True, .68
    yield "engine_high", np.tanh(high * 1.15), True, .56
    yield "tire", noise(2, 1050, 720, 3500) * (.88 + .12 * np.sin(TAU * 13 * time(2))), True, .54
    gravel = noise(2, 0, 1, 4300) * (.33 + .67 * np.sin(TAU * 31 * time(2)) ** 8)
    yield "gravel", gravel, True, .66
    yield "wind", noise(4, 230, 240, 2000), True, .53
    ambience = noise(8, 450, 550, 1800) * (.65 + .12 * np.sin(TAU * .25 * time(8)))
    yield "ambient_canyon", ambience, True, .48
    yield "music_canyon_drive", music(), True, .72
    for name, length, base, decay, gain in (
        ("impact_body", .32, 95, 17, .83), ("impact_crash", .75, 67, 7, .88),
        ("weapon_club", .30, 240, 20, .78), ("weapon_fist", .19, 120, 28, .78),
        ("weapon_chain", .48, 2100, 13, .71), ("shift", .14, 380, 48, .55),
    ):
        t = time(length)
        signal = .55 * noise(length, base * 2, base * 2, min(9500, base * 8))
        signal += np.sin(TAU * base * t) + .24 * np.sin(TAU * base * 2.71 * t)
        yield name, attack_release(signal * np.exp(-decay * t), .0015, .035), False, gain
    t = time(.24)
    yield "weapon_swing", attack_release(noise(.24, 850, 650, 3400) * np.sin(np.pi * t / .24) ** 2), False, .64
    for name, notes, gain in (("ui_confirm", (74, 81), .59), ("ui_back", (69, 62), .52), ("finish", (62, 65, 69, 74), .72)):
        signal = np.zeros(round(RATE * (len(notes) * .1 + .5)))
        for index, midi in enumerate(notes):
            sound = note(midi, .49, True)
            start = round(index * .1 * RATE)
            signal[start:start + len(sound)] += sound * .5
        yield name, attack_release(signal), False, gain


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    records = []
    for name, signal, loop, peak in library():
        signal -= np.mean(signal, axis=0)
        signal = np.tanh(signal * .9)
        signal *= peak / max(np.max(np.abs(signal)), 1e-9)
        # One-shots must start/end at zero after DC compensation.
        if not loop:
            signal = attack_release(signal, .001, .003)
            correction = np.sin(np.linspace(0, np.pi, len(signal))) ** 2
            signal -= correction * np.mean(signal) / np.mean(correction)
        else:
            signal -= np.mean(signal, axis=0)
        signal *= peak / max(np.max(np.abs(signal)), 1e-9)
        pcm = np.rint(signal * 32767).astype("<i2")
        path = OUT / ("RB_" + name + ".wav")
        channels = 1 if pcm.ndim == 1 else pcm.shape[1]
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(channels)
            handle.setsampwidth(2)
            handle.setframerate(RATE)
            handle.writeframes(pcm.tobytes())
        decoded = pcm.astype(np.float64) / 32768
        seam = float(np.max(np.abs(decoded[0] - decoded[-1])))
        step99 = float(np.quantile(np.abs(np.diff(decoded, axis=0)), .99))
        records.append(dict(name=name, file=path.relative_to(ROOT).as_posix(), loop=loop,
            sampleRate=RATE, channels=channels, frames=len(pcm), seconds=len(pcm)/RATE,
            peak=float(np.max(np.abs(decoded))), rms=float(np.sqrt(np.mean(decoded ** 2))),
            dc=float(np.max(np.abs(np.mean(decoded, axis=0)))),
            clippedSamples=int(np.sum(np.abs(pcm.astype(np.int32)) >= 32767)),
            seamDelta=seam, adjacentDeltaP99=step99, seamLimit=max(.003, step99 * 1.5),
            bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    manifest = dict(schema=1, authoring="Original deterministic oscillators, filtered seeded noise and original note sequences; no sampled reference media.",
        seed=6068796, generator="tools/p06/audio/author_audio.py", numpy=np.__version__,
        generatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), clips=records,
        pcmBytes=sum(x["frames"] * x["channels"] * 2 for x in records))
    (REPORT / "audio-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(clips=len(records), pcmBytes=manifest["pcmBytes"], maxPeak=max(x["peak"] for x in records),
        maxLoopSeamRatio=max(x["seamDelta"]/x["seamLimit"] for x in records if x["loop"]))))


if __name__ == "__main__":
    main()
