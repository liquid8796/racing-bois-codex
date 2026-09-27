"""Stage a simulation-only candidate without writing any production source."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
folder=ROOT/'Packages/com.racingbois.foundation/Runtime/Simulation'
authority=(folder/'PedestrianSimulation.cs').read_text(encoding='utf8')
start=authority.index('                if (pedestrian.Mode == PedestrianMode.Stumbled)')
end=authority.index('\n            }\n            if (front == long.MinValue',start)
authority=authority[:start]+'''                var ended = PedestrianMotion.AdvanceKnownState(pedestrian, world.Track.RoadHalfWidthMillimeters + 1200);
                if (ended == PedestrianWalkEnd.Recovered) RaceSimulation.Emit(world, RaceEventKind.PedestrianRecovered, pedestrian.Id, 0, 0);
                if (ended == PedestrianWalkEnd.Crossing) pedestrian.WaitTicks = 180 + NextRandom(world) % 180;
                else if (ended == PedestrianWalkEnd.AlongRoad) pedestrian.WaitTicks = 120 + NextRandom(world) % 180;'''+authority[end:]
prediction=(folder/'RiderPrediction.cs').read_text(encoding='utf8')
old='''                if (p.Mode != PedestrianMode.Walking) continue;
                p.MotionRemainder += p.WalkingSpeedMillimetersPerSecond; int step = p.MotionRemainder / 60; p.MotionRemainder %= 60;
                if (p.IsCrossing) p.LateralMillimeters = RaceSimulation.Clamp(p.LateralMillimeters + step, -7700, 7700);
                else p.DistanceMillimeters += step;'''
new='''                p.ModeAgeTicks++;
                var ended = PedestrianMotion.AdvanceKnownState(p, sandbox.Track.RoadHalfWidthMillimeters + 1200);
                // The next random wait is chosen later by authority. Its known
                // minimum already exceeds the remaining30tick proxy horizon;
                // use that lower bound without drawing RNG or claiming events.
                if (ended == PedestrianWalkEnd.Crossing) p.WaitTicks = 180;
                else if (ended == PedestrianWalkEnd.AlongRoad) p.WaitTicks = 120;'''
assert old in prediction;prediction=prediction.replace(old,new)
prediction=prediction.replace('b.WalkingSpeedMillimetersPerSecond = a.WalkingSpeedMillimetersPerSecond; b.MotionRemainder = 0; sandbox.PedestrianCount++;','b.WalkingSpeedMillimetersPerSecond = a.WalkingSpeedMillimetersPerSecond;\n                b.WaitTicks = a.WaitTicks; b.DesiredWalkingSpeed = a.DesiredWalkingSpeed; b.MotionRemainder = a.MotionRemainder; sandbox.PedestrianCount++;')
prediction=prediction.replace('private readonly RaceRider rider = new RaceRider();','private readonly RaceRider rider = new RaceRider();\n        private readonly RaceRider[] proxyRiders = new RaceRider[GameplayRules.MaxRiders - 1];')
prediction=prediction.replace('for (int i = 1; i < sandbox.Riders.Length; i++) sandbox.Riders[i] = new RaceRider();','for (int i = 0; i < proxyRiders.Length; i++) proxyRiders[i] = new RaceRider();')
prediction=prediction.replace('sandbox.RiderCount = 1; sandbox.TrafficCount = sandbox.PedestrianCount = 0;', 'sandbox.Riders[0] = rider; sandbox.RiderCount = 1; sandbox.TrafficCount = sandbox.PedestrianCount = 0;')
prediction=prediction.replace('RiderCheckpoints.Restore(sandbox.Riders[i + 1], RiderCheckpoints.Capture(neighbors.Riders[i], checkpoint.Tick));\n                proxyVerticalVelocity[i] = neighbors.VerticalVelocity[i]; sandbox.RiderCount++;','RiderCheckpoints.Restore(proxyRiders[i], RiderCheckpoints.Capture(neighbors.Riders[i], checkpoint.Tick));\n                proxyVerticalVelocity[i] = neighbors.VerticalVelocity[i]; sandbox.Riders[sandbox.RiderCount++] = proxyRiders[i];')
anchor='            for (int i = 0; i < neighbors.TrafficCount; i++)'
sort='''            // Authority visits riders in ascending ID order. Earlier pairs can
            // apply protection before a later rider's traffic/pedestrian pass.
            // Keep stable proxy references for kinematics; sort this bounded
            // contact roster once on restore without allocating per tick.
            for (int i = 1; i < sandbox.RiderCount; i++)
            {
                var value = sandbox.Riders[i]; int at = i;
                while (at > 0 && sandbox.Riders[at - 1].Id > value.Id)
                { sandbox.Riders[at] = sandbox.Riders[at - 1]; at--; }
                sandbox.Riders[at] = value;
            }
'''
assert anchor in prediction;prediction=prediction.replace(anchor,sort+anchor,1)
prediction=prediction.replace('AdvanceNeighbors(); DrivingDynamics.ResolveContacts(sandbox, rider.Id);','AdvanceNeighbors(); DrivingDynamics.ResolveContacts(sandbox);')
prediction=prediction.replace('for (int i = 1; i < sandbox.RiderCount; i++)\n            {\n                var r = sandbox.Riders[i]; RiderCheckpoints.SetPrevious(r);','for (int i = 0; i < neighbors.RiderCount; i++)\n            {\n                var r = proxyRiders[i]; RiderCheckpoints.SetPrevious(r);')
prediction=prediction.replace('neighbors.Acceleration[i - 1]','neighbors.Acceleration[i]').replace('neighbors.LateralVelocity[i - 1]','neighbors.LateralVelocity[i]').replace('proxyVerticalVelocity[i - 1]','proxyVerticalVelocity[i]')
prediction=prediction.replace('                r.SpeedRemainder += neighbors.Acceleration[i];','                r.ModeAgeTicks++; RiderModeClock.AdvanceDrivingMode(r);\n                r.SpeedRemainder += neighbors.Acceleration[i];')
prediction=prediction.replace('''            CombatResolver.BeginAttack(sandbox, rider);
            if (rider.Mode == RiderMode.Attacking && rider.AttackAgeTicks == GameplayRules.AttackImpactTick) rider.AttackResolved = true;''','''            CombatResolver.ForecastKnownAttacks(sandbox, rider.Id);''')
prediction=prediction.replace('private readonly RaceRider[] proxyRiders = new RaceRider[GameplayRules.MaxRiders - 1];','''private readonly RaceRider[] proxyRiders = new RaceRider[GameplayRules.MaxRiders - 1];
        private readonly bool[] proxyMotionTransitionCreated = new bool[GameplayRules.MaxRiders - 1];''')
prediction=prediction.replace('proxyVerticalVelocity[i] = neighbors.VerticalVelocity[i]; sandbox.Riders[sandbox.RiderCount++] = proxyRiders[i];','proxyVerticalVelocity[i] = neighbors.VerticalVelocity[i]; proxyMotionTransitionCreated[i] = false; sandbox.Riders[sandbox.RiderCount++] = proxyRiders[i];')
prediction=prediction.replace('''            CombatResolver.ForecastKnownAttacks(sandbox, rider.Id);
            sandbox.EventCount = 0; return Checkpoint;''','''            CombatResolver.ForecastKnownAttacks(sandbox, rider.Id);
            if (neighbors != null && sandbox.Tick - baseTick <= PredictionNeighbors.MaximumAgeTicks)
                for (int i = 0; i < neighbors.RiderCount; i++)
                    if (GameplayRules.CanDrive(neighbors.Riders[i].Mode) && !GameplayRules.CanDrive(proxyRiders[i].Mode))
                        proxyMotionTransitionCreated[i] = true;
            sandbox.EventCount = 0; return Checkpoint;''')
prediction=prediction.replace('''                if (!GameplayRules.CanDrive(r.Mode)) continue;
                r.ModeAgeTicks++;''','''                if (!GameplayRules.CanDrive(r.Mode))
                {
                    // Only a crash created inside this sandbox has its complete
                    // recovery initialization. Old non-driving snapshot proxies
                    // lack those private fields and are not claimed exact.
                    if (proxyMotionTransitionCreated[i]) DrivingDynamics.Step(sandbox, r);
                    continue;
                }
                r.ModeAgeTicks++;''')
prediction=prediction.replace('''        private void AdvanceNeighbors()
        {''','''        /// <summary>Pose-only value for a transition created by this bounded forecast at exactly the requested tick.</summary>
        public bool TryGetForecastedNeighborMotion(int id, long sampleTick, out RiderCheckpoint checkpoint)
        {
            checkpoint = default;
            if (neighbors == null || sampleTick != sandbox.Tick || sampleTick - baseTick > PredictionNeighbors.MaximumAgeTicks) return false;
            for (int i = 0; i < neighbors.RiderCount; i++)
                if (proxyMotionTransitionCreated[i] && proxyRiders[i].Id == id)
                { checkpoint = RiderCheckpoints.Capture(proxyRiders[i], sampleTick); return true; }
            return false;
        }
        private void AdvanceNeighbors()
        {''')
driving=(folder/'DrivingDynamics.cs').read_text(encoding='utf8')
start=driving.index('            if (rider.Mode == RiderMode.Hit && rider.ModeAgeTicks >= 12)')
end=driving.index('\n\n            RaceInput input',start)
driving=driving[:start]+'            RiderModeClock.AdvanceDrivingMode(rider);'+driving[end:]
combat=(folder/'CombatResolver.cs').read_text(encoding='utf8')
combat=combat.replace('''        internal static void Step(GameplayWorld world)
        {''','''        internal static void Step(GameplayWorld world) => Resolve(world, false, 0);

        // Existing proxy attacks and supplied owner inputs may affect the local
        // pose. All state stays in the private sandbox; callers expose neither
        // speculative damage/rewards nor a terminal authority result.
        internal static void ForecastKnownAttacks(GameplayWorld world, int ownerId) => Resolve(world, true, ownerId);

        private static void Resolve(GameplayWorld world, bool forecast, int ownerId)
        {''')
combat=combat.replace('                BeginAttack(world, attacker);','                if (!forecast || attacker.Id == ownerId) BeginAttack(world, attacker);',1)
old='''                    && victim.Weapon != WeaponKind.Kick && victim.Mode == RiderMode.Attacking && world.Tick > attacker.StealUntilTick
                    && (RaceSimulation.NextRandom(world) & 3) == 3)
                {
                    attacker.Weapon = victim.Weapon; victim.Weapon = WeaponKind.Fist; attacker.StealUntilTick = world.Tick + 300;
                    RaceSimulation.Emit(world, RaceEventKind.WeaponStolen, attacker.Id, victim.Id, (int)attacker.Weapon);
                    continue;
                }'''
new='''                    && victim.Weapon != WeaponKind.Kick && victim.Mode == RiderMode.Attacking && world.Tick > attacker.StealUntilTick)
                {
                    // The steal gate consumes authoritative RNG. Its alternative
                    // is a normal hit, so neither branch is known to prediction.
                    if (forecast) continue;
                    if ((RaceSimulation.NextRandom(world) & 3) == 3)
                    {
                        attacker.Weapon = victim.Weapon; victim.Weapon = WeaponKind.Fist; attacker.StealUntilTick = world.Tick + 300;
                        RaceSimulation.Emit(world, RaceEventKind.WeaponStolen, attacker.Id, victim.Id, (int)attacker.Weapon);
                        continue;
                    }
                }'''
assert old in combat;combat=combat.replace(old,new)
(HERE/'StageSimulation/PedestrianSimulation.cs').write_text(authority,encoding='utf8')
(HERE/'StageSimulation/RiderPrediction.cs').write_text(prediction,encoding='utf8')
(HERE/'StageSimulation/DrivingDynamics.cs').write_text(driving,encoding='utf8')
(HERE/'StageSimulation/CombatResolver.cs').write_text(combat,encoding='utf8')
paths=[folder/name for name in ['PedestrianSimulation.cs','RiderPrediction.cs','DrivingDynamics.cs','CombatResolver.cs']]
(HERE/'production-before.json').write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n',encoding='utf8')
print('Staged shared deterministic transitions; production files untouched.')
