"""Bind audio source, compressed output, intended streaming groups and cutscenes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs/p08/media"
COURSES = ["rb-canyon-run", "rb-neon-district", "rb-ridge-pass", "rb-coastal-line", "rb-orchard-road"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((REPORT / "audio-manifest.json").read_text(encoding="utf-8"))
    audit = json.loads((REPORT / "audio-audit.json").read_text(encoding="utf-8"))
    storyboards = json.loads((REPORT / "cinematic-storyboards.json").read_text(encoding="utf-8"))
    if not audit["passed"] or audit["source_manifest_sha256"] != digest(REPORT / "audio-manifest.json"):
        raise RuntimeError("Audio audit missing, stale or failed")
    recipe = json.loads((ROOT / manifest["recipe"]).read_text(encoding="utf-8"))
    order = {row["id"]: index for index, row in enumerate(recipe["music"])}
    clips = []
    for clip in manifest["clips"]:
        music = clip["category"] == "music"
        full = music and clip["recipe"]["kind"] == "full-composition"
        course = order[clip["id"]] % 5 if full else None
        pack = "rb-p08-music-" + COURSES[course][3:] if full else "rb-p08-score-" + clip["id"] if music else "rb-p08-sfx"
        clips.append(dict(id=clip["id"], role=clip["recipe"].get("kind", clip["recipe"].get("family")),
                          title=clip["recipe"].get("title", clip["id"].replace("-", " ").title()),
                          sourceWav=clip["source"], oggPath=clip["runtime"], durationSeconds=clip["seconds"],
                          sourceSha256=clip["sourceSha256"], oggSha256=clip["runtimeSha256"],
                          loop=clip["loop"], category=clip["category"], gain=.18 if music else .3,
                          courseIndices=[course] if course is not None else [],
                          courseIds=[COURSES[course]] if course is not None else [],
                          intendedAssetBundle=pack, importPolicy="Import compressed; load only required bundle/clip. Do not serialize the whole library into the Race scene.",
                          signalAuditPassed=True, humanListeningAccepted=False, runtimeMixAccepted=False))
    ids = {c["id"] for c in clips}
    if any(d["music_id"] not in ids for d in storyboards["definitions"]):
        raise RuntimeError("Unknown cinematic music ID")
    delivery = dict(schema=1, audioManifest="docs/p08/media/audio-manifest.json", audioManifestSha256=digest(REPORT / "audio-manifest.json"),
                    audioAudit="docs/p08/media/audio-audit.json", audioAuditSha256=digest(REPORT / "audio-audit.json"), clips=clips,
                    cinematicBindings=[dict(cinematicId=d["id"], audioId=d["music_id"], role=d["role"], durationSeconds=d["duration_seconds"]) for d in storyboards["definitions"]],
                    sourceBytes=audit["source_bytes"], runtimeBytes=audit["runtime_bytes"],
                    maximumSingleClipFloatDecodeBytes=max(c["frames"] * c["channels"] * 4 for c in manifest["clips"]),
                    limits="Bundle assignments are intended integration data, not proof that Unity built/streamed them. A single long decoded stereo clip can be large; profile actual browser audio memory. Source WAV and runtime OGG are the same authored content unit.")
    (REPORT / "audio-delivery.json").write_text(json.dumps(delivery, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(clips=len(clips), cinematicBindings=len(delivery["cinematicBindings"]), runtimeBytes=delivery["runtimeBytes"], maxDecodedClipBytes=delivery["maximumSingleClipFloatDecodeBytes"])))


if __name__ == "__main__":
    main()
