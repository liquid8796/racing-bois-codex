using System.Diagnostics;
using System.Reflection;
using System.Text.Json;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;

internal static class ProxyBehaviorTests
{
    internal static void Run(Action<string,Action> test, Action<bool,string> check, List<object> details, JsonSerializerOptions json)
    {
        RiderCheckpointData Read(JsonElement x) => x.Deserialize<RiderCheckpointData>(json);
        PredictionNeighbors Neighbors(JsonElement x)
        {
            var n = new PredictionNeighbors();
            foreach (var row in x.GetProperty("Riders").EnumerateArray())
            {
                int i = n.RiderCount++; RiderCheckpoints.Restore(n.Riders[i], new RiderCheckpoint(Read(row.GetProperty("State"))));
                n.Acceleration[i] = I(row,"Acceleration"); n.LateralVelocity[i] = I(row,"LateralVelocity"); n.VerticalVelocity[i] = I(row,"VerticalVelocity");
            }
            foreach (var row in x.GetProperty("Traffic").EnumerateArray())
            {
                var t = n.Traffic[n.TrafficCount++]; t.Id = I(row,"Id"); t.Active = true;
                t.DistanceMillimeters = L(row,"DistanceMillimeters"); t.LateralMillimeters = I(row,"LateralMillimeters");
                t.SpeedMillimetersPerSecond = I(row,"SpeedMillimetersPerSecond"); t.WidthMillimeters = I(row,"WidthMillimeters");
                t.LengthMillimeters = I(row,"LengthMillimeters"); t.HeightMillimeters = I(row,"HeightMillimeters"); t.Oncoming = row.GetProperty("Oncoming").GetBoolean();
            }
            foreach (var row in x.GetProperty("Pedestrians").EnumerateArray())
            {
                var p = n.Pedestrians[n.PedestrianCount++]; p.Id = I(row,"Id"); p.DistanceMillimeters = L(row,"DistanceMillimeters");
                p.LateralMillimeters = I(row,"LateralMillimeters"); p.HeightMillimeters = I(row,"HeightMillimeters");
                p.Mode = (PedestrianMode)I(row,"Mode"); p.ModeAgeTicks = I(row,"ModeAgeTicks"); p.FacingSide = I(row,"FacingSide");
                p.IsCrossing = row.GetProperty("IsCrossing").GetBoolean(); p.WalkingSpeedMillimetersPerSecond = I(row,"WalkingSpeedMillimetersPerSecond");
                // These protocol5 recordings predate explicit pedestrian context.
                // Neither tested owner has a waiting pedestrian within its swept path.
                p.WaitTicks = 359; p.DesiredWalkingSpeed = Math.Max(1200, Math.Abs(p.WalkingSpeedMillimetersPerSecond));
            }
            return n;
        }
        RiderCheckpointData Replay(JsonElement x, PredictionNeighbors n, Action<RiderCheckpointData> observe = null)
        {
            var p = new RiderPredictor(I(x,"Level"), I(x,"Course")); p.SetNeighbors(n);
            var authority = Read(x.GetProperty("Authority")); p.Restore(new RiderCheckpoint(authority));
            var frames = x.GetProperty("Pending").EnumerateArray().ToArray(); int index = 0;
            var held = x.GetProperty("HeldAnalog").Deserialize<RaceInput>(json); long applied = L(x,"LastAppliedTick");
            for (long tick = authority.Tick + 1; tick <= L(x.GetProperty("Predicted"),"Tick"); tick++)
            {
                RaceInput input;
                if (index < frames.Length && L(frames[index],"Tick") == tick)
                { input = frames[index++].GetProperty("Input").Deserialize<RaceInput>(json); held = new RaceInput(input.ThrottlePermille,input.BrakePermille,input.SteerPermille); applied = tick; }
                else input = applied >= 0 && tick - applied <= 6 ? held : default;
                p.Advance(tick,input); observe?.Invoke(p.Checkpoint.Data);
            }
            check(Sandbox(p).EventCount == 0, "Forecast leaked an event.");
            return p.Checkpoint.Data;
        }
        test("retained_traffic3001_contact_order_matches_later_authority", () =>
        {
            using var doc = JsonDocument.Parse(File.ReadAllText("src/Tests/RacingBois.Prediction.Tests/Fixtures/speculative-neighbor-episode.json"));
            var episode = doc.RootElement.GetProperty("episode"); var before = episode.GetProperty("Before");
            var expected = Read(episode.GetProperty("After").GetProperty("Predicted")); var legacy = Read(before.GetProperty("Predicted"));
            var n = Neighbors(before); check(n.Traffic.Take(n.TrafficCount).Any(t => t.Id == 3001), "Fixture lost the retained car.");
            var timeline = new List<RiderCheckpointData>(); var actual = Replay(before,n,d => { if(d.Tick <= 295) timeline.Add(d); });
            var differences = typeof(RiderCheckpointData).GetFields().Where(f => !Equals(f.GetValue(actual),f.GetValue(expected))).Select(f => f.Name).ToArray();
            check(actual.Mode == RiderMode.Riding && Distance(actual,expected) == 0, "Owner still crashes under the wrong contact ordering.");
            check(differences.All(name => name == "Rank"), "Physical checkpoint differs: " + string.Join(",",differences));
            check(legacy.Mode == RiderMode.Falling && Distance(legacy,expected) > 9, "Captured negative control no longer demonstrates the defect.");
            var removed = Neighbors(before); int at = Array.FindIndex(removed.Traffic,0,removed.TrafficCount,t => t.Id == 3001);
            for(int i=at;i<removed.TrafficCount-1;i++) removed.Traffic[i]=removed.Traffic[i+1]; removed.TrafficCount--;
            check(Replay(before,removed).Mode == RiderMode.Riding, "Traffic isolation control changed.");
            details.Add(new { kind="retainedTrafficContactOrder",actual,expected,differences,timeline,legacyResidualMeters=Distance(legacy,expected),candidateResidualMeters=Distance(actual,expected) });
        });
        test("known_police_attack_impact8_replays_captured_fatal_crash", () =>
        {
            using var doc = JsonDocument.Parse(File.ReadAllText("src/Tests/RacingBois.Prediction.Tests/Fixtures/maximum-correction-episode.json"));
            var episode = doc.RootElement.GetProperty("episode"); var before = episode.GetProperty("Before");
            var expected = Read(episode.GetProperty("After").GetProperty("Predicted")); var n = Neighbors(before);
            var police = n.Riders.Take(n.RiderCount).Single(r => r.Id == 2001);
            check(police.Mode == RiderMode.Attacking && police.AttackAgeTicks == 7 && police.Strength == 7 && police.AttackWeapon == WeaponKind.Club,"Wrong active attack fixture.");
            // Exact legacy metadata inference is recorded, not misrepresented as wire data:
            // only endurance1000 yields the observed club damage8 at strength7.
            var consistent = Enumerable.Range(500,501).Where(e => CombatRules.Damage(7,e,1000,WeaponKind.Club)==8).ToArray();
            check(consistent.SequenceEqual(new[]{1000}),"Observed damage no longer uniquely fixes endurance.");
            police.Endurance = consistent[0]; police.AttackResolved = false;
            var timeline = new List<RiderCheckpointData>(); var actual = Replay(before,n,d => { if(d.Tick <= 4736) timeline.Add(d); });
            check(timeline[0].Tick == 4734 && timeline[0].Mode == RiderMode.Falling && timeline[0].Health == 0,"Known impact was not forecast at authority tick4734.");
            check(actual.Mode == expected.Mode && actual.ModeAgeTicks == expected.ModeAgeTicks && actual.Health == expected.Health,"Known attack result/timing differs.");
            check(Distance(actual,expected) < .03, "Residual exceeds bounded fixture quantization: " + Distance(actual,expected));
            var suppressed = Neighbors(before); suppressed.Riders.Take(suppressed.RiderCount).Single(r=>r.Id==2001).AttackResolved=true;
            check(Replay(before,suppressed).Mode == RiderMode.Riding,"Resolved attack fired again.");
            details.Add(new {kind="knownPoliceAttack", actual,expected,timeline,candidateResidualMeters=Distance(actual,expected),enduranceEvidence="Derived uniquely from actual strength7/club damage8 within authority endurance500..1000; not directly transmitted by protocol5."});
        });
        test("known_combat_boundaries_unknown_inputs_and_random_steal", () =>
        {
            RiderPredictor Setup(int age=7,bool resolved=false,long targetProtected=0,int side=1,RiderMode mode=RiderMode.Attacking)
            {
                var owner = new RaceRider{Id=4,Kind=RiderKind.Player,DistanceMillimeters=100000,BikeDistanceMillimeters=100000,LateralMillimeters=1500,BikeLateralMillimeters=1500,Health=512,HitUntilTick=targetProtected};
                var n = new PredictionNeighbors{RiderCount=1}; var attacker=n.Riders[0]; attacker.Id=2001;attacker.Kind=RiderKind.Police;attacker.DistanceMillimeters=attacker.BikeDistanceMillimeters=100000;
                attacker.Mode=mode;attacker.AttackAgeTicks=age;attacker.AttackSide=side;attacker.AttackWeapon=attacker.Weapon=WeaponKind.Club;attacker.AttackResolved=resolved;attacker.CollisionUntilTick=200;
                attacker.Input=new RaceInput(1000,0,0,1); // Must never cause a new remote attack.
                var p=new RiderPredictor(0);p.SetNeighbors(n);p.Restore(RiderCheckpoints.Capture(owner,100));return p;
            }
            check(Setup().Advance(101,default).Data.Mode==RiderMode.Falling,"Known windup missed impact.");
            check(Setup(resolved:true).Advance(101,default).Data.Mode==RiderMode.Riding,"Resolved impact repeated.");
            check(Setup(targetProtected:101).Advance(101,default).Data.Mode==RiderMode.Riding,"Inclusive hit cooldown boundary violated.");
            check(Setup(side:-1).Advance(101,default).Data.Mode==RiderMode.Riding,"Out-of-range side hit.");
            var early=Setup(age:6);check(early.Advance(101,default).Data.Mode==RiderMode.Riding && early.Advance(102,default).Data.Mode==RiderMode.Falling,"Impact age boundary shifted.");
            var unknown=Setup(mode:RiderMode.Riding);for(int t=101;t<=125;t++)unknown.Advance(t,default);check(unknown.Checkpoint.Data.Mode==RiderMode.Riding,"Predicted an unknown future remote input.");
            var world=new GameplayWorld(1996,0);world.Tick=101;world.RiderCount=2;
            world.Riders[0]=new RaceRider{Id=1,Mode=RiderMode.Attacking,AttackAgeTicks=8,AttackSide=1,Weapon=WeaponKind.Fist,AttackWeapon=WeaponKind.Fist,StealUntilTick=0};
            world.Riders[1]=new RaceRider{Id=2,Mode=RiderMode.Attacking,AttackAgeTicks=2,Weapon=WeaponKind.Club,LateralMillimeters=1500};
            uint rng=world.RandomState;CombatResolver.ForecastKnownAttacks(world,999);
            check(world.RandomState==rng && world.Riders[1].Health==4096 && world.Riders[1].Weapon==WeaponKind.Club,"Forecast consumed RNG or picked an unknown steal branch.");
        });
        test("owner_identity_survives_sorted_roster_restore_and_proxy_expiry", () =>
        {
            foreach(int ownerId in new[]{1,8,999})
            {
                var n=new PredictionNeighbors{RiderCount=2};n.Riders[0].Id=2001;n.Riders[1].Id=ownerId==1?2:1;
                n.Riders[0].DistanceMillimeters=200000;n.Riders[1].DistanceMillimeters=100000;
                n.Riders[0].SpeedMillimetersPerSecond=1000;n.Riders[1].SpeedMillimetersPerSecond=2000;
                n.Acceleration[0]=6000;n.Acceleration[1]=-6000;
                var owner=new RaceRider{Id=ownerId,Kind=RiderKind.Player};var checkpoint=RiderCheckpoints.Capture(owner,100);
                var p=new RiderPredictor(0);p.SetNeighbors(n);p.Restore(checkpoint);p.Advance(101,default);var w=Sandbox(p);
                check(RaceSimulation.FindRider(w,2001).SpeedMillimetersPerSecond==1100 && RaceSimulation.FindRider(w,n.Riders[1].Id).SpeedMillimetersPerSecond==1900,"Sorted roster changed proxy kinematics indexing.");
                for(int t=102;t<=131;t++)p.Advance(t,default);
                check(w.RiderCount==1&&w.Riders[0].Id==ownerId&&p.Checkpoint.Data.Id==ownerId,"Expired proxies replaced owner.");
                p.Restore(checkpoint);check(w.RiderCount==3&&p.Checkpoint.Data.Id==ownerId,"Restore after expiry changed owner.");
            }
        });
        test("bounded_maximum_proxy_prediction_allocates_zero_after_warmup", () =>
        {
            var n=new PredictionNeighbors{RiderCount=15,TrafficCount=12,PedestrianCount=6};
            for(int i=0;i<n.RiderCount;i++){var r=n.Riders[i];r.Id=i+1;r.DistanceMillimeters=r.BikeDistanceMillimeters=100000L*(i+1);r.Kind=RiderKind.Player;r.SpeedMillimetersPerSecond=30000;}
            for(int i=0;i<n.TrafficCount;i++){var t=n.Traffic[i];t.Id=3000+i;t.Active=true;t.DistanceMillimeters=4000000+i*100000;t.WidthMillimeters=2160;t.LengthMillimeters=4540;}
            for(int i=0;i<n.PedestrianCount;i++){var ped=n.Pedestrians[i];ped.Id=4000+i;ped.DistanceMillimeters=5000000+i*100000;ped.WaitTicks=359;ped.DesiredWalkingSpeed=1400;ped.FacingSide=1;}
            var p=new RiderPredictor(0);p.SetNeighbors(n);var checkpoint=RiderCheckpoints.Capture(new RaceRider{Id=999,Kind=RiderKind.Player},100);
            void Batch(){p.Restore(checkpoint);for(int tick=101;tick<=130;tick++)p.Advance(tick,default);}
            for(int i=0;i<100;i++)Batch();var stopwatch=new Stopwatch();long start=GC.GetAllocatedBytesForCurrentThread();stopwatch.Start();for(int i=0;i<1000;i++)Batch();stopwatch.Stop();long allocated=GC.GetAllocatedBytesForCurrentThread()-start;
            check(allocated==0,"Prediction allocated "+allocated+" bytes after warmup.");
            details.Add(new {kind="predictionCapacityPerformance",riders=16,traffic=12,pedestrians=6,ticks=30000,allocatedBytes=allocated,elapsedMilliseconds=stopwatch.Elapsed.TotalMilliseconds,microsecondsPerTick=stopwatch.Elapsed.TotalMilliseconds/30});
        });
    }
    private static GameplayWorld Sandbox(RiderPredictor p) => (GameplayWorld)typeof(RiderPredictor).GetField("sandbox",BindingFlags.Instance|BindingFlags.NonPublic)!.GetValue(p)!;
    private static double Distance(RiderCheckpointData a,RiderCheckpointData b) => Math.Sqrt(Math.Pow((a.DistanceMillimeters-b.DistanceMillimeters)/1000d,2)+Math.Pow((a.LateralMillimeters-b.LateralMillimeters)/1000d,2));
    private static int I(JsonElement e,string p)=>e.GetProperty(p).GetInt32();
    private static long L(JsonElement e,string p)=>e.GetProperty(p).GetInt64();
}
