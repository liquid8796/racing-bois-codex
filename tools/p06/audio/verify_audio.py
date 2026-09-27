"""Independent PCM/manifest validation, including continuity and true-peak sampling."""
from pathlib import Path
import hashlib
import importlib.util
import json
import wave
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs/p06/audio-vfx"


def main():
    manifest = json.loads((REPORT / "audio-manifest.json").read_text(encoding="utf-8"))
    checks = []
    for item in manifest["clips"]:
        path = ROOT / item["file"]
        with wave.open(str(path), "rb") as stream:
            channels, rate, width, frames = stream.getnchannels(), stream.getframerate(), stream.getsampwidth(), stream.getnframes()
            pcm = np.frombuffer(stream.readframes(frames), dtype="<i2").reshape(-1, channels)
        signal = pcm.astype(np.float64) / 32768
        spectrum = np.fft.rfft(signal, axis=0)
        # Four-times bandlimited oversampling catches inter-sample peaks missed by PCM maxima.
        upsampled = np.fft.irfft(spectrum, n=len(signal) * 4, axis=0) * 4
        true_peak = float(np.max(np.abs(upsampled)))
        seam = float(np.max(np.abs(signal[0] - signal[-1])))
        adjacent = float(np.quantile(np.abs(np.diff(signal, axis=0)), .99))
        dc = float(np.max(np.abs(np.mean(signal, axis=0))))
        rms = float(np.sqrt(np.mean(signal * signal)))
        issues = []
        if (channels, rate, width, frames) != (item["channels"], item["sampleRate"], 2, item["frames"]): issues.append("format")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]: issues.append("hash")
        if np.max(np.abs(pcm.astype(np.int32))) >= 32767 or true_peak >= .995: issues.append("clipping")
        if dc > .001 or rms < .005: issues.append("dc_or_silence")
        if item["loop"] and seam > max(.003, adjacent * 1.5): issues.append("loop_seam")
        if not item["loop"] and max(np.max(np.abs(signal[0])), np.max(np.abs(signal[-1]))) > .001: issues.append("one_shot_edge")
        checks.append(dict(name=item["name"], passed=not issues, issues=issues, truePeak4x=true_peak, rms=rms, dc=dc,
            loop=item["loop"], seamDelta=seam, seamLimit=max(.003, adjacent*1.5), channels=channels, rate=rate, frames=frames))
    source_match = hashlib.sha256((ROOT / manifest["generator"]).read_bytes()).hexdigest() == manifest["generatorSha256"]
    spec = importlib.util.spec_from_file_location("p06_original_audio", ROOT / manifest["generator"])
    author = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(author)
    first_pass = [(name, hashlib.sha256(signal.tobytes()).hexdigest()) for name, signal, _, _ in author.library()]
    author.RNG = np.random.default_rng(manifest["seed"])
    second_pass = [(name, hashlib.sha256(signal.tobytes()).hexdigest()) for name, signal, _, _ in author.library()]
    reproducible = first_pass == second_pass
    source_peaks = {x["name"]: x["truePeak4x"] for x in checks}
    loop_maxima = dict(engine_low=.105, engine_high=.105*.83, tire=.058, gravel=.075,
        wind=.048, ambient_canyon=.027, music_canyon_drive=.077)
    conservative_peak = sum(loop_maxima[name]*source_peaks[name] for name in loop_maxima) + 8*.24*.35*max(source_peaks.values())
    result = dict(passed=all(x["passed"] for x in checks) and source_match and reproducible and conservative_peak < .90,
        sourceHashMatches=source_match, generatorReproducibleInCurrentEnvironment=reproducible,
        conservativePreCodecMixPeak=conservative_peak,
        clipCount=len(checks), pcmBytes=manifest["pcmBytes"], estimatedFloatDecodedBytes=manifest["pcmBytes"]*2,
        loopCount=sum(x["loop"] for x in checks), checks=checks,
        limits="PCM and 4x true peak measured, not a subjective audition or browser AudioContext acceptance.")
    (REPORT / "audio-validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "checks"}))
    if not result["passed"]: raise SystemExit(1)


if __name__ == "__main__": main()
