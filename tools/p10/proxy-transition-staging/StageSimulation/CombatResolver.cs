using System;
using RacingBois.Gameplay.Definitions;

namespace RacingBois.Simulation
{
    /// <summary>Verified Q8 damage, strict target cooldown and CRT weapon-steal gate; authored world-unit reach/timing.</summary>
    public static class CombatRules
    {
        public static int Damage(int strength, int endurance, int maximumEndurance, WeaponKind weapon)
        {
            if (maximumEndurance <= 0 || strength <= 0) return 0;
            int ratio = (endurance << 8) / maximumEndurance;
            int effective = Math.Max(strength / 2, ratio * strength >> 8);
            int multiplier = weapon == WeaponKind.Club ? 320 : weapon == WeaponKind.Chain ? 384 : weapon == WeaponKind.Kick ? 64 : 256;
            return effective * multiplier / 256;
        }
        public static int ReachMillimeters(WeaponKind weapon) => weapon == WeaponKind.Chain ? 2600 : weapon == WeaponKind.Club ? 2200 : 1600;
        public static bool InRange(RaceRider attacker, RaceRider target, int side, WeaponKind weapon)
        {
            int lateral = target.LateralMillimeters - attacker.LateralMillimeters;
            return side != 0 && Math.Sign(lateral) == side && Math.Abs(lateral) < ReachMillimeters(weapon)
                && Math.Abs(target.DistanceMillimeters - attacker.DistanceMillimeters) < 1800
                && Math.Abs(target.HeightMillimeters - attacker.HeightMillimeters) < 1000;
        }
    }

    internal static class CombatResolver
    {
        internal static void Step(GameplayWorld world) => Resolve(world, false, 0);

        // Existing proxy attacks and supplied owner inputs may affect the local
        // pose. All state stays in the private sandbox; callers expose neither
        // speculative damage/rewards nor a terminal authority result.
        internal static void ForecastKnownAttacks(GameplayWorld world, int ownerId) => Resolve(world, true, ownerId);

        private static void Resolve(GameplayWorld world, bool forecast, int ownerId)
        {
            world.PendingHitCount = 0;
            for (int i = 0; i < world.RiderCount; i++)
            {
                var attacker = world.Riders[i];
                if (!forecast || attacker.Id == ownerId) BeginAttack(world, attacker);
            }
            // Collect from the same pre-damage world. A simultaneous fatal hit does not cancel its opponent's already valid hit.
            for (int i = 0; i < world.RiderCount; i++)
            {
                var attacker = world.Riders[i];
                if (attacker.Mode != RiderMode.Attacking || attacker.AttackResolved || attacker.AttackAgeTicks != GameplayRules.AttackImpactTick) continue;
                attacker.AttackResolved = true;
                int selected = -1; long nearest = long.MaxValue;
                for (int j = 0; j < world.RiderCount; j++)
                {
                    var target = world.Riders[j];
                    if (target == attacker || !GameplayRules.CanDrive(target.Mode) || world.Tick <= target.HitUntilTick || !CombatRules.InRange(attacker, target, attacker.AttackSide, attacker.AttackWeapon)) continue;
                    long distance = Math.Abs(target.DistanceMillimeters - attacker.DistanceMillimeters) + Math.Abs(target.LateralMillimeters - attacker.LateralMillimeters);
                    if (distance < nearest || (distance == nearest && (selected < 0 || target.Id < world.Riders[selected].Id))) { nearest = distance; selected = j; }
                }
                if (selected < 0) continue;
                var victim = world.Riders[selected];
                if (attacker.AttackWeapon == WeaponKind.Fist && attacker.Weapon == WeaponKind.Fist && victim.Weapon != WeaponKind.Fist
                    && victim.Weapon != WeaponKind.Kick && victim.Mode == RiderMode.Attacking && world.Tick > attacker.StealUntilTick)
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
                }
                int hit = world.PendingHitCount++;
                world.HitSource[hit] = i; world.HitTarget[hit] = selected; world.HitWeapon[hit] = attacker.AttackWeapon;
                world.HitDamage[hit] = CombatRules.Damage(attacker.Strength, attacker.Endurance, GameplayRules.InitialEndurance, attacker.AttackWeapon);
            }
            for (int i = 0; i < world.PendingHitCount; i++)
            {
                var attacker = world.Riders[world.HitSource[i]]; var victim = world.Riders[world.HitTarget[i]];
                // One accepted health hit per victim cooldown, deterministic lowest attacker-ID wins a same-tick group.
                if (world.Tick <= victim.HitUntilTick) continue;
                int damage = world.HitDamage[i];
                victim.HitUntilTick = world.Tick + GameplayRules.HitCooldownTicks(world.Level);
                victim.Health = Math.Max(0, victim.Health - 64 * damage);
                victim.Endurance = Math.Max(GameplayRules.InitialEndurance / 2, victim.Endurance - damage * 4);
                int secondary = world.HitWeapon[i] == WeaponKind.Kick ? damage / 4 + 1 : 0;
                victim.BikeCondition = Math.Max(0, victim.BikeCondition - secondary);
                if (world.HitWeapon[i] == WeaponKind.Kick) victim.LateralMillimeters += attacker.AttackSide * 500;
                RaceSimulation.Emit(world, RaceEventKind.Hit, attacker.Id, victim.Id, damage);
                if (victim.Health == 0 || victim.BikeCondition == 0) DrivingDynamics.Crash(world, victim, 0, 0);
                else if (victim.Mode != RiderMode.Airborne) { victim.Mode = RiderMode.Hit; victim.ModeAgeTicks = 0; victim.AttackSide = 0; }
            }
        }

        internal static void BeginAttack(GameplayWorld world, RaceRider attacker)
        {
            if (attacker.Mode != RiderMode.Riding || attacker.Input.AttackSide == 0 || world.Tick < attacker.NextAttackTick) return;
            attacker.Mode = RiderMode.Attacking; attacker.ModeAgeTicks = 0; attacker.AttackAgeTicks = 0;
            attacker.AttackSide = attacker.Input.AttackSide; attacker.AttackWeapon = attacker.Input.Kick ? WeaponKind.Kick : attacker.Weapon;
            attacker.AttackResolved = false;
            attacker.NextAttackTick = world.Tick + Math.Max(GameplayRules.AttackDurationTicks + 6, GameplayRules.HitCooldownTicks(world.Level) + 1);
            RaceSimulation.Emit(world, RaceEventKind.Attack, attacker.Id, 0, (int)attacker.AttackWeapon);
        }
    }
}
