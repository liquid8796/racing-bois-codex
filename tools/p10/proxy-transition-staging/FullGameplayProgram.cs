using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;

var results = new List<object>();
int failed = 0;
void Test(string name, Action test)
{
    try { test(); results.Add(new { name, passed = true }); Console.WriteLine("PASS " + name); }
    catch (Exception error) { failed++; results.Add(new { name, passed = false, error = error.Message }); Console.WriteLine("FAIL " + name + ": " + error.Message); }
}
void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
GameplayWorld Arena(int players = 1)
{
    var world = RaceSimulation.CreateDefault(1996, 0);
    RaceSimulation.FindRider(world, GameplayRules.PoliceId).Mode = RiderMode.Wrecked;
    for (int id = 1; id <= players; id++) { var rider = RaceSimulation.AddPlayer(world, id); rider.DistanceMillimeters = rider.BikeDistanceMillimeters = 0; rider.LateralMillimeters = rider.BikeLateralMillimeters = (id - 1) * 1200; }
    return world;
}
void Advance(GameplayWorld world, int count, RaceInput input = default)
{
    for (int tick = 0; tick < count; tick++) { RaceSimulation.SetInput(world, 1, input); RaceSimulation.Step(world); }
}
int Events(GameplayWorld world, RaceEventKind kind) { int count = 0; for (int i = 0; i < world.EventCount; i++) if (world.Events[i].Kind == kind) count++; return count; }

Test("track_geometry_continuity_and_sections", () =>
{
    var track = TrackDefinition.Default;
    Check(track.LengthMillimeters == 2200000, "Length changed without fixture update");
    bool straight = false, tight = false, broad = false, uphill = false, downhill = false;
    var previous = track.Sample(0);
    for (long s = 1000; s <= track.LengthMillimeters; s += 1000)
    {
        var sample = track.Sample(s);
        double distance = Math.Sqrt(Math.Pow(sample.CenterX - previous.CenterX, 2) + Math.Pow(sample.CenterZ - previous.CenterZ, 2));
        Check(distance > .998 && distance < 1.002, "Ribbon discontinuity at " + s);
        Check(Math.Abs(sample.CenterY * 1000 - track.HeightMillimetersAt(s)) < 1, "Physics and render road height disagree");
        Check(sample.RoadHalfWidthMillimeters == 6500, "Road width mismatch");
        straight |= sample.CurvatureMicroRadiansPerMeter == 0; tight |= Math.Abs(sample.CurvatureMicroRadiansPerMeter) > 6000;
        broad |= Math.Abs(sample.CurvatureMicroRadiansPerMeter) > 0 && Math.Abs(sample.CurvatureMicroRadiansPerMeter) < 5000;
        uphill |= sample.GradePermille > 0; downhill |= sample.GradePermille < 0; previous = sample;
    }
    Check(straight && tight && broad && uphill && downhill, "Missing route test condition");
});

Test("throttle_curve_braking_and_input_timeout", () =>
{
    var world = Arena(); var rider = RaceSimulation.FindRider(world, 1);
    int previous = 0;
    for (int i = 0; i < 240; i++) { Advance(world, 1, new RaceInput(1000, 0, 0)); Check(rider.SpeedMillimetersPerSecond >= previous, "Throttle not monotonic on straight"); previous = rider.SpeedMillimetersPerSecond; }
    Check(previous > 29000 && previous < 39000, "Authored four-second acceleration tolerance");
    long brakingStart = rider.DistanceMillimeters; Advance(world, 120, new RaceInput(0, 1000, 0));
    Check(rider.SpeedMillimetersPerSecond == 0 && rider.DistanceMillimeters - brakingStart < 35000, "Braking failed");
    RaceSimulation.SetInput(world, 1, new RaceInput(1000, 0, 0)); for (int i = 0; i < 120; i++) RaceSimulation.Step(world);
    Check(rider.SpeedMillimetersPerSecond < 6500, "Stale throttle did not time out");
});

Test("lane_change_offroad_drag_and_lean", () =>
{
    var road = Arena(); var dirt = Arena(); var a = RaceSimulation.FindRider(road, 1); var b = RaceSimulation.FindRider(dirt, 1);
    a.SpeedMillimetersPerSecond = b.SpeedMillimetersPerSecond = 30000; b.LateralMillimeters = 7100;
    Advance(road, 45, new RaceInput(1000, 0, 450)); Advance(dirt, 45, new RaceInput(1000, 0, 0));
    Check(a.LateralMillimeters > 1000 && a.LateralMillimeters < 4000, "Lane change magnitude");
    Check(a.LeanMillidegrees < -10000, "Lean absent"); Check(b.SpeedMillimetersPerSecond < a.SpeedMillimetersPerSecond - 2500, "Offroad has no resistance");
});

Test("crest_launch_landing_and_no_vertical_teleport", () =>
{
    var world = Arena(); var rider = RaceSimulation.FindRider(world, 1);
    rider.DistanceMillimeters = rider.BikeDistanceMillimeters = 669600; rider.SpeedMillimetersPerSecond = 50000;
    bool airborne = false, landed = false; int maximumHeight = 0;
    for (int i = 0; i < 140; i++)
    {
        int curve = world.Track.CurvatureAt(rider.DistanceMillimeters);
        int steer = (int)((long)rider.SpeedMillimetersPerSecond * curve / 100) / (1200 + rider.SpeedMillimetersPerSecond / 6);
        int before = rider.HeightMillimeters; Advance(world, 1, new RaceInput(0, 0, steer));
        airborne |= rider.Mode == RiderMode.Airborne; landed |= Events(world, RaceEventKind.Landed) > 0;
        maximumHeight = Math.Max(maximumHeight, rider.HeightMillimeters); Check(Math.Abs(rider.HeightMillimeters - before) < 250, "Height teleported");
    }
    Check(airborne && landed && maximumHeight > 1000, "Crest did not produce complete flight/landing");
});

Test("relative_sweep_stops_oncoming_tunneling", () =>
{
    var world = Arena(); var rider = RaceSimulation.FindRider(world, 1); rider.SpeedMillimetersPerSecond = 58000;
    var traffic = world.Traffic[0]; world.TrafficCount = 1; traffic.Active = true; traffic.Id = 3000;
    traffic.DistanceMillimeters = 10000; traffic.LateralMillimeters = 0; traffic.SpeedMillimetersPerSecond = -1200000;
    Advance(world, 1);
    Check(rider.Mode == RiderMode.Wrecked || rider.Mode == RiderMode.Falling, "Swept crossing was missed");
    Check(rider.DistanceMillimeters < 700, "Collision was resolved only after crossing");
});

Test("van_and_coupe_proxy_match_art_height_and_width", () =>
{
    foreach (bool van in new[] { false, true })
    {
        var world = Arena(); var rider = RaceSimulation.FindRider(world, 1); rider.Mode = RiderMode.Airborne;
        rider.HeightMillimeters = 2000; rider.SpeedMillimetersPerSecond = 20000;
        world.TrafficCount = 1; var traffic = world.Traffic[0]; traffic.Active = true;
        traffic.HeightMillimeters = van ? VehicleDimensions.VanHeight : VehicleDimensions.CoupeHeight;
        Advance(world, 1);
        Check(van ? rider.Mode == RiderMode.Falling : rider.Mode == RiderMode.Airborne, "Vertical art bounds mismatch " + van);
        world = Arena(); rider = RaceSimulation.FindRider(world, 1); rider.SpeedMillimetersPerSecond = 20000; rider.LateralMillimeters = 1580;
        world.TrafficCount = 1; traffic = world.Traffic[0]; traffic.Active = true;
        traffic.WidthMillimeters = van ? VehicleDimensions.VanWidth : VehicleDimensions.CoupeWidth;
        Advance(world, 1);
        Check(van ? rider.Mode == RiderMode.Falling : rider.Mode == RiderMode.Riding, "Side art bounds mismatch " + van);
    }
});

Test("airborne_crash_falls_to_ground_without_height_snap", () =>
{
    var world = Arena(); var rider = RaceSimulation.FindRider(world, 1);
    rider.Mode = RiderMode.Airborne; rider.HeightMillimeters = 2000; rider.BikeHeightMillimeters = 2000;
    rider.LateralMillimeters = 9300; rider.SpeedMillimetersPerSecond = 58000;
    Advance(world, 1, new RaceInput(0, 0, 1000));
    Check(rider.Mode == RiderMode.Falling && rider.HeightMillimeters > 1900, "Crash snapped airborne rider to ground");
    Advance(world, 120); Check(rider.HeightMillimeters == 0 && rider.BikeHeightMillimeters == 0, "Crash never landed");
});

Test("recovery_separation_running_remount_without_snap", () =>
{
    var world = Arena(); var rider = RaceSimulation.FindRider(world, 1);
    rider.Mode = RiderMode.Falling; rider.BikeDistanceMillimeters = 12000; rider.BikeLateralMillimeters = 900;
    bool detached = false, running = false, remounting = false, remounted = false;
    for (int i = 0; i < 400; i++)
    {
        var mode = rider.Mode; long before = rider.DistanceMillimeters; Advance(world, 1);
        detached |= rider.Mode == RiderMode.Detached; running |= rider.Mode == RiderMode.Running; remounting |= rider.Mode == RiderMode.Remounting;
        remounted |= Events(world, RaceEventKind.Remounted) > 0;
        if (mode == RiderMode.Running) Check(Math.Abs(rider.DistanceMillimeters - before) <= 75, "Running teleported to bike");
    }
    Check(detached && running && remounting && remounted && rider.Mode == RiderMode.Riding, "Recovery stuck or skipped states");
    Check(world.Tick >= 220 && rider.Health == GameplayRules.InitialHealth, "Recovery condition restore");
});

Test("wreck_cannot_remount_and_timeout_never_teleports", () =>
{
    var world = Arena(); var rider = RaceSimulation.FindRider(world, 1); rider.Mode = RiderMode.Running; rider.BikeCondition = 0;
    Advance(world, 100); Check(rider.Mode == RiderMode.Wrecked, "Broken bike remounted");
    world = Arena(); rider = RaceSimulation.FindRider(world, 1); rider.Mode = RiderMode.Running; rider.BikeDistanceMillimeters = 1000000;
    Advance(world, 1201); Check(rider.Mode == RiderMode.Wrecked && rider.DistanceMillimeters < 100000, "Timeout teleported instead of terminating");
});

Test("legacy_q8_damage_four_weapons", () =>
{
    int[] expected = { 7, 8, 10, 1 };
    for (int i = 0; i < 4; i++) Check(CombatRules.Damage(7, 1000, 1000, (WeaponKind)i) == expected[i], "Native fixture strength7 weapon" + i);
    Check(CombatRules.Damage(7, 1, 1000, WeaponKind.Fist) == 3, "Half-strength floor lost");
});

Test("wrong_side_range_height_and_fallen_miss", () =>
{
    var world = Arena(2); var attacker = RaceSimulation.FindRider(world, 1); var victim = RaceSimulation.FindRider(world, 2);
    Check(!CombatRules.InRange(attacker, victim, -1, WeaponKind.Fist), "Wrong side accepted");
    victim.LateralMillimeters = 1600; Check(!CombatRules.InRange(attacker, victim, 1, WeaponKind.Fist), "Reach equality accepted");
    victim.LateralMillimeters = 1200; victim.DistanceMillimeters = 1800; Check(!CombatRules.InRange(attacker, victim, 1, WeaponKind.Fist), "Longitudinal equality accepted");
    victim.DistanceMillimeters = 0; victim.HeightMillimeters = 1000; Check(!CombatRules.InRange(attacker, victim, 1, WeaponKind.Fist), "Height equality accepted");
    victim.HeightMillimeters = 0; attacker.Mode = RiderMode.Falling; Advance(world, 12, new RaceInput(0, 0, 0, 1));
    Check(victim.Health == GameplayRules.InitialHealth, "Fallen attacker dealt damage");
});

Test("live_hit_pool_cooldown_equality_and_kick_condition", () =>
{
    foreach (WeaponKind weapon in Enum.GetValues<WeaponKind>())
    {
        var world = Arena(2); var attacker = RaceSimulation.FindRider(world, 1); var victim = RaceSimulation.FindRider(world, 2);
        attacker.Weapon = weapon == WeaponKind.Kick ? WeaponKind.Fist : weapon;
        Advance(world, 9, new RaceInput(0, 0, 0, 1, weapon == WeaponKind.Kick));
        int damage = CombatRules.Damage(7, 1000, 1000, weapon);
        Check(victim.Health == GameplayRules.InitialHealth - damage * 64, "Live health delta " + weapon);
        Check(victim.Endurance == 1000 - damage * 4 && victim.BikeCondition == 100 - (weapon == WeaponKind.Kick ? 1 : 0), "Live pool delta " + weapon);
    }
    var equal = Arena(2); RaceSimulation.FindRider(equal, 2).HitUntilTick = 9; Advance(equal, 9, new RaceInput(0, 0, 0, 1));
    Check(RaceSimulation.FindRider(equal, 2).Health == GameplayRules.InitialHealth, "Strict cooldown equality failed");
    var expired = Arena(2); RaceSimulation.FindRider(expired, 2).HitUntilTick = 8; Advance(expired, 9, new RaceInput(0, 0, 0, 1));
    Check(RaceSimulation.FindRider(expired, 2).Health == GameplayRules.InitialHealth - 448, "Cooldown tick after expiry failed");
});

Test("simultaneous_fatal_hits_both_apply_before_finish", () =>
{
    var world = Arena(2); var a = RaceSimulation.FindRider(world, 1); var b = RaceSimulation.FindRider(world, 2);
    a.Health = b.Health = 400;
    for (int i = 0; i < 9; i++)
    {
        if (i == 8) { a.DistanceMillimeters = b.DistanceMillimeters = world.Track.LengthMillimeters - 1; a.SpeedMillimetersPerSecond = b.SpeedMillimetersPerSecond = 1000; }
        RaceSimulation.SetInput(world, 1, new RaceInput(0, 0, 0, 1)); RaceSimulation.SetInput(world, 2, new RaceInput(0, 0, 0, -1)); RaceSimulation.Step(world);
    }
    Check(a.Mode == RiderMode.Falling && b.Mode == RiderMode.Falling && a.Health == 0 && b.Health == 0, "Simultaneous hit order bias");
    Check(Events(world, RaceEventKind.Hit) == 2 && Events(world, RaceEventKind.Crash) == 2, "Missing simultaneous events");
    Check(world.FinishedCount == 0 && a.FinishTick == -1 && b.FinishTick == -1, "Fatal hit lost precedence to finish");
});

Test("held_attack_matches_strict_cooldown_without_alternate_misses", () =>
{
    var world = Arena(2); int hits = 0;
    for (int i = 0; i < 71; i++) { Advance(world, 1, new RaceInput(0, 0, 0, 1)); hits += Events(world, RaceEventKind.Hit); }
    Check(hits == 3 && RaceSimulation.FindRider(world, 2).Health == GameplayRules.InitialHealth - 3 * 448, "Held attack should hit ticks9/40/71 at level0");
});

Test("natural_police_pursuit_reaches_and_busts_stopped_player", () =>
{
    var world = RaceSimulation.CreateDefault(1996, 0, 0); var rider = RaceSimulation.AddPlayer(world, 1);
    rider.DistanceMillimeters = rider.BikeDistanceMillimeters = 500000;
    for (int i = 0; i < 4200 && !GameplayRules.IsTerminal(rider.Mode); i++) Advance(world, 1);
    var cop = RaceSimulation.FindRider(world, GameplayRules.PoliceId);
    Check(rider.Mode == RiderMode.Busted, "Natural chase failed stopped target: " + rider.Mode + ", cop=" + cop.Mode + " s=" + cop.DistanceMillimeters + " d=" + cop.LateralMillimeters + " speed=" + cop.SpeedMillimetersPerSecond);
});

Test("weapon_steal_deterministic_gate_and_protection", () =>
{
    bool stolen = false;
    for (int seed = 0; seed < 20 && !stolen; seed++)
    {
        var world = Arena(2); world.RandomState = (uint)seed; var a = RaceSimulation.FindRider(world, 1); var b = RaceSimulation.FindRider(world, 2); b.Weapon = WeaponKind.Chain;
        for (int i = 0; i < 9; i++) { RaceSimulation.SetInput(world, 1, new RaceInput(0, 0, 0, 1)); RaceSimulation.SetInput(world, 2, new RaceInput(0, 0, 0, -1)); RaceSimulation.Step(world); }
        if (a.Weapon == WeaponKind.Chain) { stolen = true; Check(b.Weapon == WeaponKind.Fist && a.StealUntilTick == world.Tick + 300 && Events(world, RaceEventKind.WeaponStolen) == 1, "Invalid weapon transfer"); }
    }
    Check(stolen, "CRT gate never produces steal");
});

Test("finish_tie_ranks_rewards_and_idempotence", () =>
{
    var world = Arena(4);
    for (int i = 1; i <= 4; i++) { var r = RaceSimulation.FindRider(world, i); r.DistanceMillimeters = world.Track.LengthMillimeters - 1; r.SpeedMillimetersPerSecond = 1000; }
    Advance(world, 1); Check(world.FinishedCount == 4, "Finish count");
    for (int i = 1; i <= 4; i++) { var r = RaceSimulation.FindRider(world, i); Check(r.Mode == RiderMode.Finished && r.Rank == i && r.Qualified == (i <= 3), "Stable ID tie or qualification"); }
    Check(RaceSimulation.FindRider(world, 1).Reward == 1000 && RaceSimulation.FindRider(world, 4).Reward == 400 && RaceSimulation.RewardForRank(14, 4) == 100, "Reward table");
    Advance(world, 100); Check(world.FinishedCount == 4 && Events(world, RaceEventKind.Finished) == 0, "Finish awarded twice");
});

Test("police_three_second_contact_bust_and_fine", () =>
{
    var world = RaceSimulation.CreateDefault(1996, 0, 2); var rider = RaceSimulation.AddPlayer(world, 1); var cop = RaceSimulation.FindRider(world, GameplayRules.PoliceId);
    rider.DistanceMillimeters = 400000; rider.LateralMillimeters = 0;
    bool busted = false;
    for (int i = 0; i < 240; i++)
    {
        // Controlled contact arena measures bust timer, not natural pursuit success.
        cop.DistanceMillimeters = rider.DistanceMillimeters; cop.LateralMillimeters = 2000; cop.SpeedMillimetersPerSecond = 0;
        Advance(world, 1); if (rider.Mode == RiderMode.Busted) { Check(i + 1 == 180, "Bust timer differs"); busted = true; break; }
    }
    Check(busted && rider.Reward == -1200 && Events(world, RaceEventKind.Busted) == 1, "Bust outcome");
});

Test("human_capacity_ownership_and_slot_removal", () =>
{
    var world = RaceSimulation.CreateDefault();
    for (int i = 1; i <= 8; i++) Check(RaceSimulation.AddPlayer(world, i) != null, "Valid player rejected");
    Check(RaceSimulation.AddPlayer(world, 9) == null && RaceSimulation.AddPlayer(world, 1) == null && RaceSimulation.AddPlayer(world, 1001) == null, "Capacity or identity failure");
    Check(!RaceSimulation.SetInput(world, 1001, new RaceInput(0, 1000, 0)), "Player input controlled bot");
    Check(RaceSimulation.RemovePlayer(world, 4) && RaceSimulation.AddPlayer(world, 9) != null, "Slot not reusable");
});

Test("local_campaign_five_courses_five_levels_no_double_reward", () =>
{
    var campaign = new LocalCampaignProgress(); long run = 0;
    Check(campaign.TryApplyResult(run++, 0, 4) && campaign.Credits == 400 && campaign.QualifiedCourseMask == 0, "Nonqualification reward");
    Check(!campaign.TryApplyResult(0, 0, 1) && campaign.Credits == 400, "Replay duplicated credits");
    Check(campaign.TryApplyResult(run++, 0, 0, true) && campaign.Credits == 0, "Fine clamping");
    for (int level = 0; level < 5; level++) for (int course = 0; course < 5; course++)
        Check(campaign.TryApplyResult(run++, course, 1), "Valid qualification rejected");
    Check(campaign.Completed && campaign.Level == 4 && campaign.QualifiedCourseMask == 31 && campaign.Credits == 75000, "Five-level campaign progression");
    Check(!campaign.TryApplyResult(run++, 0, 1), "Completed campaign awarded more credits");
});

Test("pedestrian_pool_spawns_ahead_and_retains_roadside_lane", () =>
{
    var world = Arena(); bool crossing = false, roadside = false; int spawns = 0;
    for (int tick = 0; tick < 6000; tick++)
    {
        Advance(world, 1);
        Check(world.PedestrianCount <= GameplayRules.MaxPedestrians, "Pedestrian budget exceeded");
        for (int e = 0; e < world.EventCount; e++) if (world.Events[e].Kind == RaceEventKind.PedestrianSpawned)
        {
            spawns++;
            for (int i = 0; i < world.PedestrianCount; i++) if (world.Pedestrians[i].Id == world.Events[e].ActorId)
                Check(world.Pedestrians[i].DistanceMillimeters >= 150000 && world.Pedestrians[i].DistanceMillimeters < 220000, "Pedestrian popped into near view");
        }
        for (int i = 0; i < world.PedestrianCount; i++)
        {
            var p = world.Pedestrians[i]; crossing |= p.IsCrossing; roadside |= !p.IsCrossing;
            if (!p.IsCrossing) Check(Math.Abs(p.LateralMillimeters) == 7700, "Roadside walker drifted into traffic");
        }
    }
    Check(spawns == 6 && crossing && roadside, "Pedestrian population or crossing mix absent");
    RaceSimulation.FindRider(world, 1).DistanceMillimeters = 900000; Advance(world, 1);
    Check(world.PedestrianCount == 1 && world.Pedestrians[0].Id > 4006, "Pedestrian despawn/reuse failed");
});

Test("pedestrian_crosswalk_is_continuous_and_waits_at_shoulder", () =>
{
    var world = Arena(); world.PedestrianCount = 1; var p = world.Pedestrians[0];
    p.Id = 4999; p.DistanceMillimeters = 20000; p.LateralMillimeters = 7700; p.IsCrossing = true; p.FacingSide = -1; p.Mode = PedestrianMode.Walking;
    bool crossedCenter = false, arrived = false;
    for (int i = 0; i < 700; i++)
    {
        int before = p.LateralMillimeters; Advance(world, 1);
        Check(Math.Abs(before - p.LateralMillimeters) <= 24, "Crosswalk teleported"); crossedCenter |= p.LateralMillimeters < 0;
        if (p.Mode == PedestrianMode.Waiting && p.LateralMillimeters == -7700) { arrived = true; break; }
    }
    Check(crossedCenter && arrived && p.FacingSide == 1, "Crosswalk arrival and next direction");
});

Test("pedestrian_swept_crash_and_non_graphic_recovery", () =>
{
    var world = Arena(); var rider = RaceSimulation.FindRider(world, 1); rider.SpeedMillimetersPerSecond = 58000;
    world.PedestrianCount = 1; var p = world.Pedestrians[0]; p.Id = 4999; p.DistanceMillimeters = 1800; p.Mode = PedestrianMode.Waiting;
    Advance(world, 1);
    Check(rider.Mode == RiderMode.Falling && p.Mode == PedestrianMode.Stumbled, "Bike failed swept pedestrian contact");
    Check(rider.DistanceMillimeters < 500 && rider.BikeCondition == 92 && Events(world, RaceEventKind.PedestrianStumbled) == 1, "Pedestrian contact resolved too late or wrong cost");
    Advance(world, 180); Check(p.Mode == PedestrianMode.Waiting && p.ModeAgeTicks == 0, "Pedestrian did not recover after180ticks");
    Advance(world, 120); Check(p.Mode == PedestrianMode.Walking, "Recovered pedestrian stayed stuck");
});

Test("pedestrian_low_speed_bump_stops_bike_without_crash", () =>
{
    var world = Arena(); var rider = RaceSimulation.FindRider(world, 1); rider.SpeedMillimetersPerSecond = 6000;
    world.PedestrianCount = 1; var p = world.Pedestrians[0]; p.Id = 4999; p.DistanceMillimeters = 1450; p.Mode = PedestrianMode.Waiting;
    Advance(world, 3);
    Check(rider.Mode == RiderMode.Hit && rider.SpeedMillimetersPerSecond == 0 && p.Mode == PedestrianMode.Stumbled, "Slow contact outcome");
    Check(rider.BikeCondition == 100 && rider.Health >= GameplayRules.InitialHealth - 60, "Slow contact excessive penalty");
});

Test("pedestrian_on_shoulder_uses_same_collision_rules", () =>
{
    var world = Arena(); var rider = RaceSimulation.FindRider(world, 1); rider.SpeedMillimetersPerSecond = 25000; rider.LateralMillimeters = 7700;
    world.PedestrianCount = 1; var p = world.Pedestrians[0]; p.Id = 4999; p.DistanceMillimeters = 1600; p.LateralMillimeters = 7700; p.Mode = PedestrianMode.Waiting;
    Advance(world, 1);
    Check(p.Mode == PedestrianMode.Stumbled && rider.Mode == RiderMode.Falling, "Offroad bypassed pedestrian collision");
});

Test("long_session_actor_ids_wrap_without_namespace_or_active_alias", () =>
{
    var world = Arena(); int trafficSpawns = 0, pedestrianSpawns = 0; int maximumTraffic = 0, maximumPedestrian = 0;
    bool trafficWrapped = false, pedestrianWrapped = false;
    for (int tick = 0; tick < 301000; tick++)
    {
        // Preserve the first active ID through allocator wrap; retire others to accelerate a long-running spawn/despawn soak.
        for (int i = 0; i < world.TrafficCount; i++) world.Traffic[i].DistanceMillimeters = world.Traffic[i].Id == 3001 ? 200000 : -200000;
        for (int i = 0; i < world.PedestrianCount; i++) world.Pedestrians[i].DistanceMillimeters = world.Pedestrians[i].Id == 4001 ? 200000 : -200000;
        Advance(world, 1);
        for (int i = 0; i < world.EventCount; i++)
        {
            var e = world.Events[i];
            if (e.Kind == RaceEventKind.TrafficSpawned) { trafficSpawns++; trafficWrapped |= trafficSpawns > 999 && e.ActorId < 3500; maximumTraffic = Math.Max(maximumTraffic, e.ActorId); }
            if (e.Kind == RaceEventKind.PedestrianSpawned) { pedestrianSpawns++; pedestrianWrapped |= pedestrianSpawns > 999 && e.ActorId < 4500; maximumPedestrian = Math.Max(maximumPedestrian, e.ActorId); }
        }
        for (int i = 0; i < world.TrafficCount; i++)
        { Check(world.Traffic[i].Id >= 3001 && world.Traffic[i].Id <= 3999, "Traffic crossed ID namespace"); for (int j = i + 1; j < world.TrafficCount; j++) Check(world.Traffic[i].Id != world.Traffic[j].Id, "Traffic active ID reused"); }
        for (int i = 0; i < world.PedestrianCount; i++)
        { Check(world.Pedestrians[i].Id >= 4001 && world.Pedestrians[i].Id <= 4999, "Pedestrian crossed ID namespace"); for (int j = i + 1; j < world.PedestrianCount; j++) Check(world.Pedestrians[i].Id != world.Pedestrians[j].Id, "Pedestrian active ID reused"); }
    }
    Check(trafficWrapped && pedestrianWrapped && maximumTraffic == 3999 && maximumPedestrian == 4999, "Allocator wrap not exercised");
});

ulong Hash(GameplayWorld world, ulong hash)
{
    void Mix(long value) { hash = unchecked((hash ^ (ulong)value) * 1099511628211UL); }
    Mix(world.Tick); Mix(world.RandomState); Mix(world.PedestrianRandomState); Mix(world.FinishedCount); Mix(world.TrafficCount); Mix(world.PedestrianCount);
    for (int i = 0; i < world.RiderCount; i++)
    {
        var r = world.Riders[i]; Mix(r.Id); Mix((int)r.Mode); Mix((int)r.Weapon); Mix(r.DistanceMillimeters); Mix(r.LateralMillimeters); Mix(r.HeightMillimeters);
        Mix(r.SpeedMillimetersPerSecond); Mix(r.Health); Mix(r.BikeCondition); Mix(r.Endurance); Mix(r.Rank); Mix(r.FinishTick); Mix(r.Reward); Mix(r.BikeDistanceMillimeters); Mix(r.BikeLateralMillimeters);
    }
    for (int i = 0; i < world.TrafficCount; i++) { var t = world.Traffic[i]; Mix(t.Id); Mix(t.DistanceMillimeters); Mix(t.LateralMillimeters); Mix(t.SpeedMillimetersPerSecond); Mix(t.WidthMillimeters); Mix(t.LengthMillimeters); Mix(t.HeightMillimeters); }
    for (int i = 0; i < world.EventCount; i++) { var e = world.Events[i]; Mix(e.Id); Mix(e.Tick); Mix((int)e.Kind); Mix(e.ActorId); Mix(e.TargetId); Mix(e.Value); }
    for (int i = 0; i < world.PedestrianCount; i++) { var p = world.Pedestrians[i]; Mix(p.Id); Mix(p.DistanceMillimeters); Mix(p.LateralMillimeters); Mix((int)p.Mode); Mix(p.ModeAgeTicks); Mix(p.WalkingSpeedMillimetersPerSecond); Mix(p.FacingSide); Mix(p.IsCrossing ? 1 : 0); }
    return hash;
}
RaceInput ReplayInput(GameplayWorld world)
{
    var rider = RaceSimulation.FindRider(world, 1);
    int desired = (int)(world.Tick / 180 % 3 - 1) * 2200;
    int curve = world.Track.CurvatureAt(rider.DistanceMillimeters + rider.SpeedMillimetersPerSecond / 8);
    int drift = (int)((long)rider.SpeedMillimetersPerSecond * curve / 100000);
    int steer = Math.Clamp(((desired - rider.LateralMillimeters) * 2 + drift) * 1000 / (1200 + rider.SpeedMillimetersPerSecond / 6), -1000, 1000);
    return new RaceInput(1000, world.Tick % 900 > 810 ? 400 : 0, steer, world.Tick % 200 < 40 ? 1 : world.Tick % 200 > 150 ? -1 : 0, world.Tick % 500 < 100);
}
ulong replayHash = 0;
object replayOutcomes = null;
int peakTraffic = 0;
Test("twenty_thousand_tick_seeded_replay_and_ai_budget", () =>
{
    var first = RaceSimulation.CreateDefault(1996, 5, 2); var second = RaceSimulation.CreateDefault(1996, 5, 2);
    RaceSimulation.AddPlayer(first, 1); RaceSimulation.AddPlayer(second, 1);
    ulong hashA = 14695981039346656037UL, hashB = hashA;
    bool sawTraffic = false, sawAttack = false, sawFinish = false;
    for (int tick = 0; tick < 20000; tick++)
    {
        RaceSimulation.SetInput(first, 1, ReplayInput(first)); RaceSimulation.SetInput(second, 1, ReplayInput(second));
        RaceSimulation.Step(first); RaceSimulation.Step(second); hashA = Hash(first, hashA); hashB = Hash(second, hashB);
        Check(hashA == hashB, "Replay diverged tick " + tick);
        Check(first.RiderCount <= GameplayRules.MaxRiders && first.TrafficCount <= GameplayRules.MaxTraffic && first.PedestrianCount <= GameplayRules.MaxPedestrians && first.EventCount <= GameplayRules.MaxEventsPerTick, "Spawn/event budget exceeded");
        peakTraffic = Math.Max(peakTraffic, first.TrafficCount); sawTraffic |= first.TrafficCount > 0; sawAttack |= Events(first, RaceEventKind.Attack) > 0; sawFinish |= Events(first, RaceEventKind.Finished) > 0;
        for (int i = 0; i < first.RiderCount; i++) Check(Math.Abs(first.Riders[i].LateralMillimeters) < 11000, "AI escaped world");
    }
    Check(sawTraffic && sawAttack && sawFinish, "Replay did not exercise traffic/combat/finish"); replayHash = hashA;
    // P08 explicitly changes level2 route geometry and NPC equipment/tuning. P06/P07 historical receipt hashes remain preserved.
    Check(replayHash == 0xBA1786522D59B2D7UL, "Golden replay changed: review tuning and update explicitly");
    var outcomes = new List<object>();
    for (int i = 0; i < first.RiderCount; i++) { var r = first.Riders[i]; outcomes.Add(new { r.Id, mode = r.Mode.ToString(), r.Rank, r.FinishTick, r.DistanceMillimeters, r.Health, r.BikeCondition }); }
    replayOutcomes = outcomes;
    Console.WriteLine("Replay hash " + replayHash.ToString("X16"));
});

object routeCompletion = null;
Test("player_can_finish_authored_route_with_curve_compensation", () =>
{
    var world = RaceSimulation.CreateDefault(1996, 5, 0); var player = RaceSimulation.AddPlayer(world, 1);
    int crashes = 0, jumps = 0;
    for (int tick = 0; tick < 9000 && !GameplayRules.IsTerminal(player.Mode); tick++)
    {
        int curve = world.Track.CurvatureAt(player.DistanceMillimeters + player.SpeedMillimetersPerSecond / 8);
        int drift = (int)((long)player.SpeedMillimetersPerSecond * curve / 100000);
        int steer = Math.Clamp((-player.LateralMillimeters * 2 + drift) * 1000 / (1200 + player.SpeedMillimetersPerSecond / 6), -1000, 1000);
        Advance(world, 1, new RaceInput(1000, 0, steer));
        crashes += Events(world, RaceEventKind.Crash); jumps += Events(world, RaceEventKind.Landed);
    }
    Check(player.Mode == RiderMode.Finished, "Player failed controlled route completion: " + player.Mode);
    Check(player.FinishTick > 2400 && player.FinishTick < 9000, "Authored completion tolerance 40-150seconds");
    routeCompletion = new { ticks = player.FinishTick, seconds = player.FinishTick / 60.0, player.Rank, player.Health, player.BikeCondition,
        allRiderCrashEvents = crashes, allRiderLandingEvents = jumps, note = "Controller fixture compensates curves and stays center. Not a human playtest or original game timing parity." };
});

var velocityCurve = new List<object>(); int stoppingTicks = 0; long stoppingDistance = 0;
Test("record_authored_straight_velocity_and_brake_curve", () =>
{
    var world = Arena(); var rider = RaceSimulation.FindRider(world, 1);
    velocityCurve.Add(new { tick = 0, speedMmPerSecond = 0, distanceMm = 0L });
    for (int second = 1; second <= 6; second++)
    { Advance(world, 60, new RaceInput(1000, 0, 0)); velocityCurve.Add(new { tick = second * 60, speedMmPerSecond = rider.SpeedMillimetersPerSecond, distanceMm = rider.DistanceMillimeters }); }
    long before = rider.DistanceMillimeters;
    while (rider.SpeedMillimetersPerSecond > 0 && stoppingTicks < 300) { Advance(world, 1, new RaceInput(0, 1000, 0)); stoppingTicks++; }
    stoppingDistance = rider.DistanceMillimeters - before;
    Check(stoppingTicks > 60 && stoppingTicks < 130, "Full brake tolerance");
});

double microsecondsPerTick = 0; long allocated = 0;
Test("fixed_capacity_tick_no_managed_allocations", () =>
{
    var worlds = new GameplayWorld[12];
    for (int batch = 0; batch < worlds.Length; batch++)
    { worlds[batch] = RaceSimulation.CreateDefault(1996 + batch, 6, 4); for (int i = 1; i <= 8; i++) RaceSimulation.AddPlayer(worlds[batch], i); }
    var warmup = RaceSimulation.CreateDefault(1996, 6, 4); for (int i = 0; i < 500; i++) RaceSimulation.Step(warmup);
    long before = GC.GetAllocatedBytesForCurrentThread(); long start = Stopwatch.GetTimestamp();
    for (int batch = 0; batch < worlds.Length; batch++) for (int tick = 0; tick < 1000; tick++)
    {
        var world = worlds[batch];
        for (int i = 1; i <= 8; i++) RaceSimulation.SetInput(world, i, new RaceInput(1000, 0, 0, tick % 2 == 0 ? 1 : -1));
        RaceSimulation.Step(world);
    }
    long elapsed = Stopwatch.GetTimestamp() - start; allocated = GC.GetAllocatedBytesForCurrentThread() - before;
    microsecondsPerTick = elapsed * 1000000.0 / Stopwatch.Frequency / 12000;
    Check(allocated == 0, "Core allocated " + allocated + " bytes");
});

GameplayVerificationResult startupVerification = default;
Test("bounded_cross_runtime_startup_golden", () =>
{
    var timeline = new List<GameplayVerificationFrame>(GameplayVerification.ReplayTicks);
    startupVerification = GameplayVerification.Run(frame => timeline.Add(frame));
    string timelinePath = args.Length > 0 ? Path.Combine(Path.GetDirectoryName(Path.GetFullPath(args[0])), "gameplay-replay-timeline.json") : "docs/p10/proxy-transition-staging/full-gameplay/gameplay-replay-timeline.json";
    Directory.CreateDirectory(Path.GetDirectoryName(timelinePath));
    File.WriteAllText(timelinePath, JsonSerializer.Serialize(new
    {
        seed = 1996, botCount = 5, level = 2, ticks = startupVerification.Ticks, hash = startupVerification.Hash,
        expectedHash = startupVerification.ExpectedHash, note = "Per-tick generated input and resulting state/hash for the isolated startup replay.", frames = timeline
    }, new JsonSerializerOptions { IncludeFields = true }));
    Console.WriteLine("Startup replay hash " + startupVerification.Hash);
    Check(startupVerification.Passed, "Startup golden changed: " + startupVerification.Hash);
});

string output = args.Length > 0 ? args[0] : "docs/p10/proxy-transition-staging/full-gameplay/gameplay-validation.json";
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
var sourceFiles = new List<object>();
var sourcePaths = new List<string>();
sourcePaths.AddRange(Directory.GetFiles("Packages/com.racingbois.foundation/Runtime/Definitions", "*.cs"));
foreach (string path in Directory.GetFiles("Packages/com.racingbois.foundation/Runtime/Simulation", "*.cs"))
    if (Path.GetFileName(path) != "PedestrianSimulation.cs" && Path.GetFileName(path) != "RiderPrediction.cs") sourcePaths.Add(path);
sourcePaths.AddRange(Directory.GetFiles("tools/p10/proxy-transition-staging/StageSimulation", "*.cs"));
sourcePaths.Add("tools/p10/proxy-transition-staging/FullGameplayProgram.cs");
sourcePaths.Add("tools/p10/proxy-transition-staging/FullGameplayTests.csproj");
sourcePaths.Add("src/Tests/RacingBois.Gameplay.Tests/Program.cs"); sourcePaths.Sort(StringComparer.Ordinal);
foreach (string path in sourcePaths) sourceFiles.Add(new { path = path.Replace('\\', '/'), sha256 = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() });
File.WriteAllText(output, JsonSerializer.Serialize(new { generatedAtUtc = DateTimeOffset.UtcNow, passed = failed == 0, tests = results.Count,
    runtime = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription, sourceFiles,
    failures = failed, replayTicks = 20000, replayHash = replayHash.ToString("X16"), replayOutcomes, peakTraffic, routeCompletion,
    authoredVelocityCurve = velocityCurve, fullBrake = new { stoppingTicks, stoppingDistanceMm = stoppingDistance },
    startupVerification = new { startupVerification.Passed, startupVerification.Hash, startupVerification.ExpectedHash, startupVerification.Ticks },
    performance = new { microsecondsPerTick, managedAllocatedBytes = allocated,
    note = "Native .NET release/host-specific core time, not browser frame time or GPU acceptance." }, results }, new JsonSerializerOptions { WriteIndented = true }));
return failed == 0 ? 0 : 1;
