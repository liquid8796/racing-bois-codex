"""Compare research MIDI event fingerprints without exporting notes to production."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


def main():
    rows = []
    for path in sorted((ROOT / "docs/p01/assets/media/midi").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        notes, pitches = [], []
        tempo, previous_tick, duration = 500000, 0, 0.0
        channels, programs = set(), set()
        for event in data["events"]:
            duration += (event["absolute_ticks"] - previous_tick) / data["division"] * tempo / 1000000
            previous_tick = event["absolute_ticks"]
            if event["type"] == "tempo":
                tempo = event["microseconds_per_quarter"]
                continue
            message = bytes.fromhex(event["message_hex"])
            kind, channel = message[0] >> 4, message[0] & 15
            channels.add(channel)
            if kind == 12:
                programs.add((channel, message[1]))
            elif kind in [8, 9]:
                quarter_ticks = [event["absolute_ticks"], data["division"]]
                notes.append((quarter_ticks, kind, channel, message[1], message[2]))
                if kind == 9 and message[2]:
                    pitches.append((quarter_ticks, message[1]))
        rows.append(dict(id=path.stem, research_json=path.relative_to(ROOT).as_posix(),
                         research_json_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                         division=data["division"], event_count=data["event_count"],
                         note_events=len(notes), positive_note_ons=len(pitches), duration_seconds=duration,
                         active_channels=len(channels), program_assignments=len(programs),
                         note_event_fingerprint=fingerprint(notes), onset_pitch_fingerprint=fingerprint(pitches)))
    assert len(rows) == 11
    pairs = []
    by_id = {row["id"]: row for row in rows}
    for number in range(1, 6):
        a, b = by_id[f"GRUNGE{number}"], by_id[f"SBKGRNG{number}"]
        pairs.append(dict(a=a["id"], b=b["id"], exact_note_event_match=a["note_event_fingerprint"] == b["note_event_fingerprint"],
                          exact_onset_pitch_match=a["onset_pitch_fingerprint"] == b["onset_pitch_fingerprint"],
                          interpretation="Different event streams do not prove different underlying compositions; arrangement equivalence remains unproven."))
    report = dict(schema=1, passed=True, file_count=11, total_events=sum(r["event_count"] for r in rows),
                  all_note_event_fingerprints_distinct=len({r["note_event_fingerprint"] for r in rows}) == 11,
                  pairs=pairs, files=rows, composition_equivalence="UNPROVEN",
                  production_decision="Author 11 additional distinct original short scores; none uses source note events, melodies, instruments or samples.",
                  limits="Metadata and exact event comparison only. SoundFont playback and perceptual/melodic arrangement equivalence are not inferred.")
    output = ROOT / "docs/p08/media/reference-mids-analysis.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ["files", "pairs"]}))


if __name__ == "__main__":
    main()
