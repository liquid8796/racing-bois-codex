"""Stage contextual handling of retired in-flight inputs; preserve server and live client sources."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'Application';OUT.mkdir(exist_ok=True)
rows=[]
def stage(name,pairs):
    path='Assets/RacingBois/Client/Application/'+name;original=ROOT/path;text=original.read_text(encoding='utf8')
    for old,new in pairs:
        if old not in text:raise RuntimeError('Missing anchor '+name)
        text=text.replace(old,new,1)
    out=OUT/name;out.write_text(text,encoding='utf8');rows.append({'path':path,'before':hashlib.sha256(original.read_bytes()).hexdigest(),'staged':out.relative_to(ROOT).as_posix(),'after':hashlib.sha256(out.read_bytes()).hexdigest()})
stage('MultiplayerSession.cs',[
 ('        private void ClearRace()','        private void ClearRace(bool preserveRetiredInput = false)'),
 ('            pending.Clear(); events.Clear(); remotes.Clear(); Array.Clear(probes, 0, probes.Length);','            if (!preserveRetiredInput) retiredInputRange = default;\n            pending.Clear(); events.Clear(); remotes.Clear(); Array.Clear(probes, 0, probes.Length);')])
stage('MultiplayerSession.Messages.cs',[
 ('                if (Room == null || candidate.RoomId != Room.RoomId || candidate.RaceEpoch != Room.RaceEpoch ||', '''                if (Room != null && candidate.RoomId == Room.RoomId && candidate.RaceEpoch == Room.RaceEpoch && candidate.Phase == LobbyPhase.Results)
                    RetireRaceInputs();
                bool preserveRetired = Room != null && candidate.RoomId == Room.RoomId &&
                    ((Room.Phase == LobbyPhase.Results && candidate.Phase == LobbyPhase.Lobby && candidate.RaceEpoch == Room.RaceEpoch) ||
                     (Room.Phase == LobbyPhase.Lobby && candidate.Phase == LobbyPhase.Countdown && candidate.RaceEpoch == Room.RaceEpoch + 1));
                if (Room == null || candidate.RoomId != Room.RoomId || candidate.RaceEpoch != Room.RaceEpoch ||'''),
 ('                { ClearRace(); Result = null; }\n                Room = candidate;', '                { ClearRace(preserveRetired); Result = null; }\n                if (candidate.Phase == LobbyPhase.Racing) retiredInputRange = default;\n                Room = candidate;'),
 ('                string code = m.code ?? "unknown";','''                // A confirmed completed race may still have input frames in
                // flight. Consume/ack their reliable rejection without turning
                // expected turnover into a persistent user-facing error.
                if (IsRetiredInputError(m)) return;
                string code = m.code ?? "unknown";''')])
new=OUT/'MultiplayerSession.InputErrors.cs';path='Assets/RacingBois/Client/Application/'+new.name
assert not (ROOT/path).exists();rows.append({'path':path,'before':None,'staged':new.relative_to(ROOT).as_posix(),'after':hashlib.sha256(new.read_bytes()).hexdigest()})
(HERE/'manifest.json').write_text(json.dumps({'schema':1,'scope':'Contextual client presentation of retired input rejection only. No server/wire/policy change.','changes':rows},indent=2)+'\n');print('STAGED',len(rows),'client files; production unchanged.')
