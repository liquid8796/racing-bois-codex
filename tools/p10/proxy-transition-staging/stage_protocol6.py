"""Prepare protocol6 pedestrian prediction metadata outside production."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=HERE/'StageIntegration';OUT.mkdir(exist_ok=True)
files={}
def stage(path,replacements):
    text=files.get(path,(ROOT/path).read_text(encoding='utf8'))
    for old,new in replacements:
        if old not in text:raise RuntimeError('Missing expected pattern: '+path)
        text=text.replace(old,new,1)
    files[path]=text
stage('Packages/com.racingbois.foundation/Runtime/Protocol/MultiplayerMessages.cs',[
 ('Version = 5, TickRate','Version = 6, TickRate'),
 ('// Pedestrian rows: id,s(cm),d(cm),height(cm),speed(cm/s),mode,stateTicks,facingSide,isCrossing.', '// Pedestrian rows: id,s(cm),d(cm),height(cm),speed(cm/s),mode,stateTicks,facingSide,isCrossing,\n    // chosenWaitTicks(60..359),desiredWalkingSpeed(mm/s,1200..1600),motionRemainder(-59..59).')])
stage('src/Server/RacingBois.Server.Application/Multiplayer/MultiplayerProjection.cs',[
 ('var item = world.Pedestrians[i]; if (!Near(item.DistanceMillimeters, 80000, 260000)) continue;', 'var item = world.Pedestrians[i]; if (!Near(item.DistanceMillimeters, 80000, 260000)) continue;\n            var prediction = PedestrianCheckpoints.CapturePredictionContext(item);'),
 ('item.ModeAgeTicks, item.FacingSide, item.IsCrossing ? 1 : 0));','item.ModeAgeTicks, item.FacingSide, item.IsCrossing ? 1 : 0, prediction.WaitTicks, prediction.DesiredWalkingSpeed, prediction.MotionRemainder));')])
stage('Assets/RacingBois/Client/Application/MultiplayerSnapshotReadModel.cs',[
 ('using System.Collections.ObjectModel;', 'using System.Collections.ObjectModel;\nusing RacingBois.Simulation;'),
 ('public IReadOnlyDictionary<int, long> CollisionUntilByRider { get; }','public IReadOnlyDictionary<int, long> CollisionUntilByRider { get; }\n        public IReadOnlyDictionary<int, PedestrianPredictionContext> PedestrianContexts { get; }'),
 ('IDictionary<int, long> collisionUntilByRider)', 'IDictionary<int, long> collisionUntilByRider, IDictionary<int, PedestrianPredictionContext> pedestrianContexts)'),
 ('CollisionUntilByRider = new ReadOnlyDictionary<int, long>(new Dictionary<int, long>(collisionUntilByRider));', 'CollisionUntilByRider = new ReadOnlyDictionary<int, long>(new Dictionary<int, long>(collisionUntilByRider));\n            if (pedestrianContexts == null) throw new ArgumentNullException(nameof(pedestrianContexts));\n            PedestrianContexts = new ReadOnlyDictionary<int, PedestrianPredictionContext>(new Dictionary<int, PedestrianPredictionContext>(pedestrianContexts));')])
stage('Assets/RacingBois/Client/Application/MultiplayerProjection.cs',[
 ('using RacingBois.Protocol;', 'using RacingBois.Protocol;\nusing RacingBois.Simulation;'),
 ('var pedestrians = new RacePedestrianSnapshot[s.pedestrians.Length];', 'var pedestrians = new RacePedestrianSnapshot[s.pedestrians.Length];\n            var pedestrianContexts = new Dictionary<int, PedestrianPredictionContext>(s.pedestrians.Length);'),
 ('{ var v = Row(s.pedestrians[i], 9); pedestrians[i] = new RacePedestrianSnapshot', '''{
                var v = Row(s.pedestrians[i], 12); var context = new PedestrianPredictionContext(v[9], v[10], v[11]);
                Require(v[7] == -1 || v[7] == 1, "Invalid pedestrian facing");
                int expectedSpeed = v[5] == (int)PedestrianMode.Walking ? v[7] * context.DesiredWalkingSpeed : 0;
                Require(context.Matches((PedestrianMode)v[5], v[6], expectedSpeed, v[7], Bool(v[8])) && v[4] == expectedSpeed / 10, "Incoherent pedestrian prediction context");
                Require(!pedestrianContexts.ContainsKey(v[0]), "Duplicate pedestrian context"); pedestrianContexts.Add(v[0], context);
                pedestrians[i] = new RacePedestrianSnapshot'''),
 ('new MultiplayerSnapshotReadModel(Copy(projected, events), collisionUntil)', 'new MultiplayerSnapshotReadModel(Copy(projected, events), collisionUntil, pedestrianContexts)')])
stage('Assets/RacingBois/Client/Application/MultiplayerSession.Messages.cs',[
 ('projected.CollisionUntilByRider);', 'projected.CollisionUntilByRider, projected.PedestrianContexts);')])
stage('Assets/RacingBois/Client/Application/PredictionNeighborBuilder.cs',[
 ('IReadOnlyDictionary<int, long> collisionUntilByRider)', 'IReadOnlyDictionary<int, long> collisionUntilByRider, IReadOnlyDictionary<int, PedestrianPredictionContext> pedestrianContexts)'),
 ('            target.RiderCount = target.TrafficCount = target.PedestrianCount = 0;', '''            if (pedestrianContexts == null) throw new ArgumentNullException(nameof(pedestrianContexts));
            foreach (var pedestrian in current.Pedestrians)
                if (!pedestrianContexts.TryGetValue(pedestrian.Id, out var context) || !context.IsValid)
                    throw new ArgumentException("Pedestrian prediction context is missing or invalid.");
            target.RiderCount = target.TrafficCount = target.PedestrianCount = 0;'''),
 ('proxy.IsCrossing = p.IsCrossing; proxy.FacingSide = p.FacingSide;', 'proxy.IsCrossing = p.IsCrossing; proxy.FacingSide = p.FacingSide;\n                PedestrianCheckpoints.RestorePredictionContext(proxy, pedestrianContexts[p.Id]);')])
stage('Packages/com.racingbois.foundation/Runtime/Protocol/MultiplayerMessages.cs',[
 ('collisionProtectionTicksRemaining(0..90).','collisionProtectionTicksRemaining(0..90),\n    // endurance(500..1000),attackResolved(0/1),hitProtectionTicksRemaining(0..90),stealProtectionTicksRemaining(0..300).')])
stage('src/Server/RacingBois.Server.Application/Multiplayer/MultiplayerProjection.cs',[
 ('            riders.Add(Row(rider.Id,','            var prediction = RiderCheckpoints.Capture(rider, world.Tick).Data;\n            riders.Add(Row(rider.Id,'),
 ('CollisionProtectionRemaining(RiderCheckpoints.Capture(rider, world.Tick).Data.CollisionUntilTick, world.Tick)));',
 '''CollisionProtectionRemaining(prediction.CollisionUntilTick, world.Tick), prediction.Endurance, prediction.AttackResolved ? 1 : 0,
                CombatProtectionRemaining(prediction.HitUntilTick, world.Tick, RiderCombatPredictionContext.MaximumHitProtectionTicks),
                CombatProtectionRemaining(prediction.StealUntilTick, world.Tick, RiderCombatPredictionContext.MaximumStealProtectionTicks)));'''),
 ('    private static int Cm(long value)', '''    private static int CombatProtectionRemaining(long until, long tick, int maximum)
    {
        long remaining = until <= tick ? 0 : until - tick;
        if (remaining > maximum) throw new InvalidOperationException("Authoritative combat protection exceeds protocol bounds.");
        return (int)remaining;
    }
    private static int Cm(long value)''')])
stage('Assets/RacingBois/Client/Application/MultiplayerSnapshotReadModel.cs',[
 ('public IReadOnlyDictionary<int, PedestrianPredictionContext> PedestrianContexts { get; }','public IReadOnlyDictionary<int, PedestrianPredictionContext> PedestrianContexts { get; }\n        public IReadOnlyDictionary<int, RiderCombatPredictionContext> RiderCombatContexts { get; }'),
 ('IDictionary<int, PedestrianPredictionContext> pedestrianContexts)', 'IDictionary<int, PedestrianPredictionContext> pedestrianContexts, IDictionary<int, RiderCombatPredictionContext> riderCombatContexts)'),
 ('            PedestrianContexts = new ReadOnlyDictionary<int, PedestrianPredictionContext>(new Dictionary<int, PedestrianPredictionContext>(pedestrianContexts));',
 '''            PedestrianContexts = new ReadOnlyDictionary<int, PedestrianPredictionContext>(new Dictionary<int, PedestrianPredictionContext>(pedestrianContexts));
            if (riderCombatContexts == null) throw new ArgumentNullException(nameof(riderCombatContexts));
            RiderCombatContexts = new ReadOnlyDictionary<int, RiderCombatPredictionContext>(new Dictionary<int, RiderCombatPredictionContext>(riderCombatContexts));''')])
stage('Assets/RacingBois/Client/Application/MultiplayerProjection.cs',[
 ('            var collisionUntil = new Dictionary<int, long>(s.riders.Length);','            var collisionUntil = new Dictionary<int, long>(s.riders.Length);\n            var combatContexts = new Dictionary<int, RiderCombatPredictionContext>(s.riders.Length);'),
 ('var v = Row(row, 27);','var v = Row(row, 31);'),
 ('                collisionUntil.Add(v[0], s.tick + v[26]);','                collisionUntil.Add(v[0], s.tick + v[26]);\n                combatContexts.Add(v[0], new RiderCombatPredictionContext(s.tick, v[27], Bool(v[28]), v[29], v[30]));'),
 ('new MultiplayerSnapshotReadModel(Copy(projected, events), collisionUntil, pedestrianContexts)', 'new MultiplayerSnapshotReadModel(Copy(projected, events), collisionUntil, pedestrianContexts, combatContexts)')])
stage('Assets/RacingBois/Client/Application/MultiplayerSession.Messages.cs',[
 ('projected.CollisionUntilByRider, projected.PedestrianContexts);','projected.CollisionUntilByRider, projected.PedestrianContexts, projected.RiderCombatContexts);')])
stage('Assets/RacingBois/Client/Application/PredictionNeighborBuilder.cs',[
 ('IReadOnlyDictionary<int, PedestrianPredictionContext> pedestrianContexts)', 'IReadOnlyDictionary<int, PedestrianPredictionContext> pedestrianContexts, IReadOnlyDictionary<int, RiderCombatPredictionContext> riderCombatContexts)'),
 ('            if (pedestrianContexts == null)', '''            if (riderCombatContexts == null) throw new ArgumentNullException(nameof(riderCombatContexts));
            foreach (var rider in current.Riders)
                if (rider.Id != ownId && (!riderCombatContexts.TryGetValue(rider.Id, out var combat) || !combat.IsValidAt(current.Tick)))
                    throw new ArgumentException("Remote combat context is missing or invalid.");
            if (pedestrianContexts == null)'''),
 ('                int index = target.RiderCount++; var proxy = target.Riders[index];','                int index = target.RiderCount++; var proxy = target.Riders[index]; var combat = riderCombatContexts[r.Id];'),
 ('Endurance = GameplayRules.InitialEndurance,','Endurance = combat.Endurance, AttackResolved = combat.AttackResolved,'),
 ('HitUntilTick = -1, StealUntilTick = -1,','HitUntilTick = combat.HitUntilTick, StealUntilTick = combat.StealUntilTick,')])
stage('Assets/RacingBois/Client/Application/MultiplayerSession.cs',[
 ('remotes.Sample(sampleTick, LocalRider, visibleEvents.ToArray())','remotes.Sample(sampleTick, LocalRider, visibleEvents.ToArray(), predict ? predictor : null)')])
stage('Assets/RacingBois/Client/Application/RemoteMotionSampler.cs',[
 ('public RaceWorldReadModel Sample(double tick, RaceRiderReadModel own, RaceEventReadModel[] events)', 'public RaceWorldReadModel Sample(double tick, RaceRiderReadModel own, RaceEventReadModel[] events, RacingBois.Simulation.RiderPredictor predictor = null)'),
 ('                double actorExtra = EventBoundedExtra(b.Id, to.Tick, extra, events);','''                // Share only motion from a transition actually created in the
                // private deterministic sandbox, at the same requested tick.
                // The authoritative readmodel still owns health and outcomes.
                if (predictor != null && tick == Math.Truncate(tick) && predictor.TryGetForecastedNeighborMotion(b.Id, (long)tick, out var forecast))
                { riders[i] = WithMotion(b, forecast); continue; }
                double actorExtra = EventBoundedExtra(b.Id, to.Tick, extra, events);''')])
manifest=[]
for path,text in files.items():
    # Same short name appears in server and client; role prefix prevents collision.
    name=('Server-' if path.startswith('src/Server/') else 'Client-' if path.startswith('Assets/') else '')+Path(path).name
    out=OUT/name;out.write_text(text,encoding='utf8')
    manifest.append({'path':path,'before':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'staged':out.relative_to(ROOT).as_posix(),'after':hashlib.sha256(out.read_bytes()).hexdigest()})
(HERE/'integration-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
print('Staged protocol6 integration',len(manifest),'files; no production writes.')
