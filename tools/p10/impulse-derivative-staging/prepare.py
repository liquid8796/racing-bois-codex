"""Stage the client-only contact-impulse derivative guard; no live source edits."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'Application';OUT.mkdir(parents=True,exist_ok=True)
changes=[]
def stage(name,pairs):
    path='Assets/RacingBois/Client/Application/'+name;source=ROOT/path;text=source.read_text(encoding='utf8')
    for old,new in pairs:
        if old not in text:raise RuntimeError('Missing source anchor '+name)
        text=text.replace(old,new,1)
    out=OUT/name;out.write_text(text,encoding='utf8')
    changes.append({'path':path,'before':hashlib.sha256(source.read_bytes()).hexdigest(),'staged':out.relative_to(ROOT).as_posix(),'after':hashlib.sha256(out.read_bytes()).hexdigest()})
stage('MultiplayerSession.cs',[
 ('        private RiderPredictor predictor;','        private RiderPredictor predictor;\n        private MultiplayerSnapshotReadModel latestPredictionSnapshot;'),
 ('            LatestAuthoritativeWorld = null; LocalRider = default; LastCorrectionMeters = 0;','            LatestAuthoritativeWorld = null; latestPredictionSnapshot = null; LocalRider = default; LastCorrectionMeters = 0;')])
stage('MultiplayerSession.Messages.cs',[
 ('PredictionNeighborBuilder.Fill(predictionNeighbors, candidate, LatestAuthoritativeWorld, m.riderId, projected.CollisionUntilByRider, projected.PedestrianContexts, projected.RiderCombatContexts);',
  'PredictionNeighborBuilder.Fill(predictionNeighbors, projected, latestPredictionSnapshot, m.riderId);'),
 ('RiderId = m.riderId; MeasureRenderResidual(candidate); LatestAuthoritativeWorld = candidate;','RiderId = m.riderId; MeasureRenderResidual(candidate); LatestAuthoritativeWorld = candidate; latestPredictionSnapshot = projected;')])
stage('PredictionNeighborBuilder.cs',[
 ('        public static void Fill(PredictionNeighbors target, RaceWorldReadModel current,', '''        public static void Fill(PredictionNeighbors target, MultiplayerSnapshotReadModel current, MultiplayerSnapshotReadModel previous, int ownId)
        {
            if (current == null) throw new ArgumentNullException(nameof(current));
            Fill(target, current.World, previous == null ? null : previous.World, ownId,
                current.CollisionUntilByRider, current.PedestrianContexts, current.RiderCombatContexts,
                previous == null ? null : previous.CollisionUntilByRider);
        }
        public static void Fill(PredictionNeighbors target, RaceWorldReadModel current,'''),
 ('IReadOnlyDictionary<int, RiderCombatPredictionContext> riderCombatContexts)', 'IReadOnlyDictionary<int, RiderCombatPredictionContext> riderCombatContexts, IReadOnlyDictionary<int, long> previousCollisionUntilByRider = null)'),
 ('                if (before.Id != r.Id || before.Mode != r.Mode) continue;','''                if (before.Id != r.Id || before.Mode != r.Mode) continue;
                // A newly granted protection interval marks an instantaneous
                // contact impulse. Its snapshot delta is not continuous motion.
                // Expired protection is encoded as the current tick, so require
                // a genuinely active interval before detecting a new grant.
                if (previousCollisionUntilByRider == null || !previousCollisionUntilByRider.TryGetValue(r.Id, out long previousUntil)) continue;
                long currentUntil = collisionUntilByRider[r.Id];
                if (currentUntil > current.Tick && currentUntil > previousUntil) continue;''')])
(HERE/'manifest.json').write_text(json.dumps({'schema':1,'scope':'Client-only staged derivative guard; no protocol/server/simulation changes or production writes.','changes':changes},indent=2)+'\n',encoding='utf8')
print('STAGED',len(changes),'client files; production untouched.')
