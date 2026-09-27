"""Prepare reviewable source text outside Unity; --apply requires root's idle handoff."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
STAGE=HERE/'staged';STAGE.mkdir(exist_ok=True)
files={}
def replace(path,changes):
    original=(ROOT/path).read_text(encoding='utf8');text=original
    for old,new in changes:
        if old not in text:raise RuntimeError('Expected source pattern absent in '+path)
        text=text.replace(old,new,1)
    files[path]=text
replace('Packages/com.racingbois.foundation/Runtime/Protocol/MultiplayerMessages.cs',[
    ('Version = 4, TickRate','Version = 5, TickRate'),
    ('public const int RulesVersion', '/// <summary>Maximum remaining contact protection emitted by current authoritative driving rules.</summary>\n        public const int MaximumCollisionProtectionTicks = 90;\n        public const int RulesVersion'),
    ('modeAge,gear,bikeCatalogIndex,characterCatalogIndex.', 'modeAge,gear,bikeCatalogIndex,characterCatalogIndex,collisionProtectionTicksRemaining(0..90).')])
replace('src/Server/RacingBois.Server.Application/Multiplayer/MultiplayerProjection.cs',[
    ('rider.Gear, rider.BikeCatalogIndex, rider.CharacterCatalogIndex));', 'rider.Gear, rider.BikeCatalogIndex, rider.CharacterCatalogIndex, CollisionProtectionRemaining(rider.CollisionUntilTick, world.Tick)));'),
    ('    private static int Cm(long value)', '''    private static int CollisionProtectionRemaining(long until, long tick)
    {
        long remaining = until <= tick ? 0 : until - tick;
        if (remaining > MultiplayerProtocol.MaximumCollisionProtectionTicks)
            throw new InvalidOperationException("Authoritative collision protection exceeds protocol bounds.");
        return (int)remaining;
    }
    private static int Cm(long value)''')])
replace('Assets/RacingBois/Client/Application/MultiplayerProjection.cs',[
    ('public static RaceWorldReadModel World(', 'public static MultiplayerSnapshotReadModel World('),
    ('var riders = new List<RaceEntitySnapshot>(s.riders.Length + 1); var ids = new HashSet<int>();', 'var riders = new List<RaceEntitySnapshot>(s.riders.Length + 1); var ids = new HashSet<int>();\n            var collisionUntil = new Dictionary<int, long>(s.riders.Length);'),
    ('var v = Row(row, 26); Require(ids.Add(v[0]), "Duplicate actor");', 'var v = Row(row, 27); Require(ids.Add(v[0]), "Duplicate actor");\n                Require(v[26] >= 0 && v[26] <= MultiplayerProtocol.MaximumCollisionProtectionTicks && s.tick <= long.MaxValue - v[26], "Invalid remote collision protection");\n                collisionUntil.Add(v[0], s.tick + v[26]);'),
    ('return Copy(projected, events);','return new MultiplayerSnapshotReadModel(Copy(projected, events), collisionUntil);')])
replace('Assets/RacingBois/Client/Application/MultiplayerSession.Messages.cs',[
    ('var candidate = MultiplayerProjection.World(m, sequence, processedSequence, events.ToArray());', 'var projected = MultiplayerProjection.World(m, sequence, processedSequence, events.ToArray());\n            var candidate = projected.World;'),
    ('PredictionNeighborBuilder.Fill(predictionNeighbors, candidate, LatestAuthoritativeWorld, m.riderId);', 'PredictionNeighborBuilder.Fill(predictionNeighbors, candidate, LatestAuthoritativeWorld, m.riderId, projected.CollisionUntilByRider);')])
replace('Assets/RacingBois/Client/Application/PredictionNeighborBuilder.cs',[
    ('using System;','using System;\nusing System.Collections.Generic;'),
    ('RaceWorldReadModel previous, int ownId)', 'RaceWorldReadModel previous, int ownId, IReadOnlyDictionary<int, long> collisionUntilByRider)'),
    ('            target.RiderCount = target.TrafficCount = target.PedestrianCount = 0;', '''            if (collisionUntilByRider == null) throw new ArgumentNullException(nameof(collisionUntilByRider));
            foreach (var rider in current.Riders)
                if (rider.Id != ownId && (!collisionUntilByRider.TryGetValue(rider.Id, out long until) || until < current.Tick || until - current.Tick > MultiplayerProtocol.MaximumCollisionProtectionTicks))
                    throw new ArgumentException("Remote collision protection is missing or outside snapshot bounds.");
            target.RiderCount = target.TrafficCount = target.PedestrianCount = 0;'''),
    ('using RacingBois.Simulation;', 'using RacingBois.Simulation;\nusing RacingBois.Protocol;'),
    ('Gear = r.Gear, HitUntilTick = -1, StealUntilTick = -1', 'Gear = r.Gear, HitUntilTick = -1, StealUntilTick = -1,\n                    CollisionUntilTick = collisionUntilByRider[r.Id]')])
files['Assets/RacingBois/Client/Application/MultiplayerSnapshotReadModel.cs']='''using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;

namespace RacingBois.Client.Application
{
    /// <summary>Validated visual state and immutable private prediction context from one snapshot.</summary>
    internal sealed class MultiplayerSnapshotReadModel
    {
        public RaceWorldReadModel World { get; }
        public IReadOnlyDictionary<int, long> CollisionUntilByRider { get; }
        public MultiplayerSnapshotReadModel(RaceWorldReadModel world, IDictionary<int, long> collisionUntilByRider)
        {
            World = world ?? throw new ArgumentNullException(nameof(world));
            if (collisionUntilByRider == null) throw new ArgumentNullException(nameof(collisionUntilByRider));
            CollisionUntilByRider = new ReadOnlyDictionary<int, long>(new Dictionary<int, long>(collisionUntilByRider));
        }
    }
}
'''
manifest=[]
for index,(path,text) in enumerate(files.items()):
    dest=STAGE/(str(index)+'-'+Path(path).name+'.txt');dest.write_text(text,encoding='utf8')
    original=ROOT/path
    manifest.append({'path':path,'before':hashlib.sha256(original.read_bytes()).hexdigest() if original.exists() else None,'staged':dest.relative_to(ROOT).as_posix(),'after':hashlib.sha256(dest.read_bytes()).hexdigest()})
(STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
print('Staged',len(manifest),'production files outside Unity; none applied.')
