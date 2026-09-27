using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Client.Application
{
    /// <summary>Timestamp interpolation, then bounded extrapolation in road space. Discrete state changes never blend.</summary>
    internal sealed class RemoteMotionSampler
    {
        private readonly List<RaceWorldReadModel> history = new List<RaceWorldReadModel>(32);
        internal const int MaximumExtrapolationTicks = RacingBois.Simulation.PredictionNeighbors.MaximumAgeTicks;
        public int StaleActors { get; private set; }
        public double ExtrapolationMilliseconds { get; private set; }
        public int EventCappedActors { get; private set; }
        public void Clear() { history.Clear(); StaleActors = EventCappedActors = 0; ExtrapolationMilliseconds = 0; }
        public void Add(RaceWorldReadModel world)
        {
            if (history.Count > 0 && world.Tick <= history[history.Count - 1].Tick) return;
            if (history.Count == 32) history.RemoveAt(0); history.Add(world);
        }
        public RaceWorldReadModel Sample(double tick, RaceRiderReadModel own, RaceEventReadModel[] events, RacingBois.Simulation.RiderPredictor predictor = null)
        {
            if (history.Count == 0) return null;
            var latest = history[history.Count - 1]; var from = latest; var to = latest;
            for (int i = 1; i < history.Count; i++) if (tick <= history[i].Tick) { from = history[i - 1]; to = history[i]; break; }
            if (tick < history[0].Tick) from = to = history[0];
            double requestedExtra = Math.Max(0, tick - to.Tick), extra = Math.Min(MaximumExtrapolationTicks, requestedExtra);
            StaleActors = requestedExtra > MaximumExtrapolationTicks ? to.Riders.Count + to.Traffic.Count + to.Pedestrians.Count - 1 : 0;
            EventCappedActors = 0;
            ExtrapolationMilliseconds = extra * 1000 / 60;
            float alpha = from.Tick == to.Tick ? 1 : Clamp((float)((tick - from.Tick) / (to.Tick - from.Tick)), 0, 1);
            // Before a snapshot boundary its newly spawned actors do not exist yet; removals switch at the boundary.
            var topology = alpha < 1 ? from : to;
            var riders = new RaceRiderReadModel[topology.Riders.Count];
            var previous = history.Count > 1 && from == latest ? history[history.Count - 2] : from;
            for (int i = 0; i < riders.Length; i++)
            {
                var a = topology.Riders[i];
                if (a.Id == own.Id) { riders[i] = own; continue; }
                var b = Find(to.Riders, a.Id); var p = Find(previous.Riders, a.Id);
                if (b.Id == 0) b = a;
                // Share only motion from a transition actually created in the
                // private deterministic sandbox, at the same requested tick.
                // The authoritative readmodel still owns health and outcomes.
                if (predictor != null && tick == Math.Truncate(tick) && predictor.TryGetForecastedNeighborMotion(b.Id, (long)tick, out var forecast))
                { riders[i] = WithMotion(b, forecast); continue; }
                double actorExtra = EventBoundedExtra(b.Id, to.Tick, extra, events);
                if (actorExtra < extra) EventCappedActors++;
                riders[i] = Interpolate(a, b, alpha, actorExtra, p, to.Tick - previous.Tick);
            }
            var traffic = new RaceTrafficReadModel[topology.Traffic.Count];
            for (int i = 0; i < traffic.Length; i++)
            {
                var a = topology.Traffic[i]; var b = Find(to.Traffic, a.Id); if (b.Id == 0) b = a;
                traffic[i] = new RaceTrafficReadModel(b.Id, b.Kind, Lerp(a.LongitudinalMeters, b.LongitudinalMeters, alpha) + b.SpeedMetersPerSecond * (float)(extra / 60),
                    Lerp(a.LateralMeters, b.LateralMeters, alpha), b.SpeedMetersPerSecond, b.HalfLengthMeters, b.HalfWidthMeters, b.HeightMeters);
            }
            var pedestrians = new RacePedestrianReadModel[topology.Pedestrians.Count];
            for (int i = 0; i < pedestrians.Length; i++)
            {
                var a = topology.Pedestrians[i]; var b = Find(to.Pedestrians, a.Id) ?? a;
                if (a.Mode != b.Mode) a = alpha < 1 ? a : b;
                else a = new RacePedestrianReadModel(b.Id, Lerp(a.LongitudinalMeters, b.LongitudinalMeters, alpha), Lerp(a.LateralMeters, b.LateralMeters, alpha),
                    Lerp(a.HeightMeters, b.HeightMeters, alpha), b.WalkingSpeedMetersPerSecond, b.Mode,
                    (int)Lerp(a.StateTicks, b.StateTicks, alpha), b.FacingSide, b.IsCrossing);
                float seconds = a.Mode == PedestrianMode.Walking ? (float)(extra / 60) : 0;
                pedestrians[i] = new RacePedestrianReadModel(a.Id, a.LongitudinalMeters + a.LongitudinalSpeedMetersPerSecond * seconds,
                    Clamp(a.LateralMeters + a.LateralSpeedMetersPerSecond * seconds, -7.7f, 7.7f), a.HeightMeters,
                    a.WalkingSpeedMetersPerSecond, a.Mode, a.StateTicks + (int)extra, a.FacingSide, a.IsCrossing);
            }
            return new RaceWorldReadModel((long)Math.Max(0, tick), latest.AcknowledgedInputSequence, latest.TrackLengthMeters, latest.Level, riders, traffic, events, pedestrians, latest.CourseIndex);
        }
        private static double EventBoundedExtra(int actorId, long snapshotTick, double extra, RaceEventReadModel[] events)
        {
            double end = snapshotTick + extra;
            foreach (var e in events)
            {
                if (e.Tick <= snapshotTick || e.Tick >= end) continue;
                bool stopsTrajectory = e.Kind == RaceEventKind.Crash || e.Kind == RaceEventKind.Wrecked ||
                    e.Kind == RaceEventKind.Busted || e.Kind == RaceEventKind.Landed;
                int affected = e.Kind == RaceEventKind.Busted ? e.TargetId : e.SourceId;
                if (stopsTrajectory && affected == actorId) end = e.Tick;
            }
            // Confirmed discontinuity limits the old velocity model; a newer snapshot resumes normal interpolation.
            return Math.Max(0, end - snapshotTick);
        }
        public static RaceRiderReadModel WithMotion(RaceRiderReadModel authority, RacingBois.Simulation.RiderCheckpoint checkpoint)
        {
            var d = checkpoint.Data;
            var mode = d.Mode == RiderMode.Wrecked && authority.Mode != RiderMode.Wrecked ? RiderMode.Falling : d.Mode;
            return Make(authority, mode, d.DistanceMillimeters / 1000f, d.LateralMillimeters / 1000f, d.HeightMillimeters / 1000f,
                d.BikeDistanceMillimeters / 1000f, d.BikeLateralMillimeters / 1000f, d.BikeHeightMillimeters / 1000f,
                d.SpeedMillimetersPerSecond / 1000f, d.LeanMillidegrees / 1000f, d.AttackSide, d.AttackAgeTicks, d.ModeAgeTicks, d.Gear, d.AttackWeapon);
        }
        public static RaceRiderReadModel Offset(RaceRiderReadModel r, float s, float d)
            => Make(r, r.Mode, r.LongitudinalMeters + s, r.LateralMeters + d, r.HeightMeters, r.BikeLongitudinalMeters + s,
                r.BikeLateralMeters + d, r.BikeHeightMeters, r.SpeedMetersPerSecond, r.LeanDegrees, r.AttackSide, r.AttackAgeTicks, r.StateTicks, r.Gear);
        private static RaceRiderReadModel Interpolate(RaceRiderReadModel a, RaceRiderReadModel b, float alpha, double extra, RaceRiderReadModel previous, long gap)
        {
            if (a.Mode != b.Mode) return alpha < 1 ? a : Advance(b, previous, extra, gap);
            var blended = Make(b, b.Mode, Lerp(a.LongitudinalMeters, b.LongitudinalMeters, alpha), Lerp(a.LateralMeters, b.LateralMeters, alpha),
                Lerp(a.HeightMeters, b.HeightMeters, alpha), Lerp(a.BikeLongitudinalMeters, b.BikeLongitudinalMeters, alpha),
                Lerp(a.BikeLateralMeters, b.BikeLateralMeters, alpha), Lerp(a.BikeHeightMeters, b.BikeHeightMeters, alpha),
                Lerp(a.SpeedMetersPerSecond, b.SpeedMetersPerSecond, alpha), Lerp(a.LeanDegrees, b.LeanDegrees, alpha),
                b.AttackSide, (int)Lerp(a.AttackAgeTicks, b.AttackAgeTicks, alpha), (int)Lerp(a.StateTicks, b.StateTicks, alpha), b.Gear);
            return Advance(blended, previous, extra, gap);
        }
        private static RaceRiderReadModel Advance(RaceRiderReadModel r, RaceRiderReadModel previous, double ticks, long gap)
        {
            if (ticks <= 0 || GameplayRules.IsTerminal(r.Mode) || r.Mode == RiderMode.Detached || r.Mode == RiderMode.Remounting) return r;
            float seconds = (float)(ticks / 60), dVelocity = 0, hVelocity = 0;
            bool same = previous.Id == r.Id && previous.Mode == r.Mode && gap > 0;
            if (same) { dVelocity = Clamp((r.LateralMeters - previous.LateralMeters) * 60 / gap, -12, 12); hVelocity = Clamp((r.HeightMeters - previous.HeightMeters) * 60 / gap, -20, 20); }
            float s = r.LongitudinalMeters + r.SpeedMetersPerSecond * seconds, d = r.LateralMeters + dVelocity * seconds;
            float bs = r.BikeLongitudinalMeters, bd = r.BikeLateralMeters;
            if (r.Mode == RiderMode.Running)
            {
                float delta = bs - r.LongitudinalMeters, lateral = bd - r.LateralMeters, total = Math.Abs(delta) + Math.Abs(lateral);
                float ratio = total < .001f ? 1 : Math.Min(1, GameplayRules.RunSpeedMillimetersPerSecond / 1000f * seconds / total);
                s = r.LongitudinalMeters + delta * ratio; d = r.LateralMeters + lateral * ratio;
            }
            else if (GameplayRules.CanDrive(r.Mode)) { bs = s; bd = d; }
            else if (same && r.Mode == RiderMode.Falling)
            { bs += Clamp((r.BikeLongitudinalMeters - previous.BikeLongitudinalMeters) * 60 / gap, 0, 60) * seconds; }
            return Make(r, r.Mode, s, Clamp(d, -9.3f, 9.3f), Math.Max(0, r.HeightMeters + hVelocity * seconds), bs, bd,
                r.BikeHeightMeters, r.SpeedMetersPerSecond, r.LeanDegrees, r.AttackSide,
                Math.Min(GameplayRules.AttackDurationTicks - 1, r.AttackAgeTicks + (int)ticks), r.StateTicks + (int)ticks, r.Gear);
        }
        private static RaceRiderReadModel Make(RaceRiderReadModel r, RiderMode mode, float s, float d, float h, float bs, float bd, float bh, float speed, float lean, int side, int attackAge, int age, int gear, WeaponKind? attackWeapon = null)
            => new RaceRiderReadModel(r.Id, r.Kind, mode, r.Weapon, attackWeapon ?? r.AttackWeapon, s, d, speed, h, lean, bs, bd, bh,
                r.Health, r.MaxHealth, r.BikeCondition, r.MaxBikeCondition, r.Strength, r.Rank, r.FinishTick, r.Reward, r.Qualified, side, attackAge, age, gear, r.BikeCatalogIndex, r.CharacterCatalogIndex);
        internal static RaceRiderReadModel Find(IReadOnlyList<RaceRiderReadModel> riders, int id) { for (int i = 0; i < riders.Count; i++) if (riders[i].Id == id) return riders[i]; return default; }
        private static RaceTrafficReadModel Find(IReadOnlyList<RaceTrafficReadModel> actors, int id) { for (int i = 0; i < actors.Count; i++) if (actors[i].Id == id) return actors[i]; return default; }
        private static RacePedestrianReadModel Find(IReadOnlyList<RacePedestrianReadModel> actors, int id) { for (int i = 0; i < actors.Count; i++) if (actors[i].Id == id) return actors[i]; return null; }
        private static float Lerp(float a, float b, float t) => a + (b - a) * t;
        private static float Clamp(float value, float min, float max) => Math.Max(min, Math.Min(max, value));
    }
}
