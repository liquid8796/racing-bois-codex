using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using UnityEngine;
using UnityEngine.Rendering;

namespace RacingBois.Client.Presentation
{
    /// <summary>Bounded cosmetic particles/trails driven only by immutable read models.</summary>
    public sealed class RaceEffectsView : MonoBehaviour
    {
        private const int RiderSlots = 16, ImpactSlots = 6;
        private readonly RiderEffect[] riders = new RiderEffect[RiderSlots];
        private readonly ParticleSystem[] impacts = new ParticleSystem[ImpactSlots];
        private TrackRibbonView road;
        private int impactCursor;
        private long lastEventId, lastTick;
        private bool initialized, wasActive, lowQuality, reduced;
        public int EmittedImpactCount { get; private set; }
        public int ActiveDustEmitters { get; private set; }
        public int MaximumParticleBudget => RiderSlots * 36 + ImpactSlots * 24;

        public void Initialize(TrackRibbonView track, Material softParticle, Material spark, Material skid)
        {
            if (initialized) return;
            if (track == null || softParticle == null || spark == null || skid == null)
                throw new System.ArgumentException("P06 effects require a road and three authored materials.");
            initialized = true; road = track;
            for (int i = 0; i < RiderSlots; i++)
            {
                var dust = CreateParticles("Wheel dust " + i, softParticle, true);
                var trailObject = new GameObject("Skid trail " + i);
                trailObject.transform.SetParent(transform, false);
                var trail = trailObject.AddComponent<TrailRenderer>();
                trail.sharedMaterial = skid; trail.time = 2.4f; trail.minVertexDistance = .32f;
                trail.widthMultiplier = .11f; trail.emitting = false; trail.autodestruct = false;
                trail.alignment = LineAlignment.TransformZ; trail.generateLightingData = false;
                trail.shadowCastingMode = ShadowCastingMode.Off; trail.receiveShadows = false;
                trail.textureMode = LineTextureMode.Stretch; trail.numCapVertices = 0; trail.numCornerVertices = 0;
                trail.startColor = new Color(.18f, .13f, .11f, .62f); trail.endColor = new Color(.18f, .13f, .11f, 0);
                riders[i] = new RiderEffect { Dust = dust, Trail = trail };
            }
            for (int i = 0; i < ImpactSlots; i++) impacts[i] = CreateParticles("Impact sparks " + i, spark, false);
        }

        public void SetQuality(bool low) { lowQuality = low; }

        public void ResetEvents()
        {
            if (!initialized) return;
            lastEventId = lastTick = 0;
            for (int i = 0; i < RiderSlots; i++) Retire(riders[i]);
            for (int i = 0; i < ImpactSlots; i++) impacts[i].Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        }

        public void Render(RaceWorldReadModel world, RaceRiderReadModel local, bool active, float dt, bool reducedMotion)
        {
            if (!initialized) return;
            dt = Mathf.Clamp(dt, 0, .1f);
            if (active != wasActive || (world != null && world.Tick < 60 && lastTick > 120))
                ResetEvents();
            // Reducing motion clears existing bursts without replaying the current event batch.
            if (reducedMotion && !reduced)
                for (int i = 0; i < ImpactSlots; i++) impacts[i].Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            wasActive = active; reduced = reducedMotion; ActiveDustEmitters = 0;
            for (int i = 0; i < RiderSlots; i++) riders[i].Seen = false;
            if (active && world != null)
            {
                lastTick = world.Tick;
                int maximum = lowQuality ? 8 : RiderSlots;
                for (int i = 0; i < world.Riders.Count; i++)
                {
                    var published = world.Riders[i];
                    var rider = published.Id == local.Id ? local : published;
                    if (Mathf.Abs(rider.LongitudinalMeters - local.LongitudinalMeters) > (lowQuality ? 45 : 75)) continue;
                    var slot = FindSlot(rider.Id, maximum);
                    if (slot != null) RenderRider(slot, rider, dt, reducedMotion);
                }
                for (int i = 0; i < world.Events.Count; i++) OnEvent(world.Events[i], world, local, reducedMotion);
            }
            for (int i = 0; i < RiderSlots; i++) if (!riders[i].Seen && riders[i].Id != 0) Retire(riders[i]);
        }

        private RiderEffect FindSlot(int id, int maximum)
        {
            for (int i = 0; i < maximum; i++) if (riders[i].Id == id) return riders[i];
            for (int i = 0; i < maximum; i++)
            {
                if (riders[i].Id != 0) continue;
                riders[i].Id = id; riders[i].Initialized = false; return riders[i];
            }
            return null;
        }

        private void RenderRider(RiderEffect slot, RaceRiderReadModel rider, float dt, bool reducedMotion)
        {
            slot.Seen = true;
            bool ground = GameplayRules.CanDrive(rider.Mode) && rider.Mode != RiderMode.Airborne && rider.HeightMeters < .08f;
            bool offroad = Mathf.Abs(rider.LateralMeters) > TrackDefinition.Default.RoadHalfWidthMillimeters / 1000f;
            var rear = road.Point(rider.LongitudinalMeters - .88f, rider.LateralMeters, .045f);
            bool jumped = slot.Initialized && (rear - slot.Position).sqrMagnitude > 36;
            float acceleration = slot.Initialized && dt > 0 && !jumped ? (rider.SpeedMetersPerSecond - slot.Speed) / dt : 0;
            if (!slot.Initialized || jumped) { slot.Trail.Clear(); slot.Dust.Clear(true); }
            slot.Dust.transform.position = rear;
            slot.Dust.transform.rotation = road.Heading(rider.LongitudinalMeters) * Quaternion.Euler(-70, 180, 0);
            float dustRate = ground && offroad && rider.SpeedMetersPerSecond > 3 ? Mathf.Lerp(4, 24, Mathf.Clamp01(rider.SpeedMetersPerSecond / 42)) : 0;
            if (lowQuality) dustRate *= .55f;
            if (reducedMotion) dustRate *= .25f;
            var emission = slot.Dust.emission; emission.rateOverTime = dustRate;
            if (dustRate > 0)
            {
                ActiveDustEmitters++;
                if (!slot.Dust.isPlaying) slot.Dust.Play();
            }
            else if (slot.Dust.isPlaying) slot.Dust.Stop(true, ParticleSystemStopBehavior.StopEmitting);
            slot.Trail.transform.SetPositionAndRotation(rear, road.Heading(rider.LongitudinalMeters) * Quaternion.Euler(-90, 0, 0));
            slot.Trail.emitting = !jumped && ground && !offroad && rider.SpeedMetersPerSecond > 7 &&
                (acceleration < -9 || (Mathf.Abs(rider.LeanDegrees) > 35 && rider.SpeedMetersPerSecond > 25));
            slot.Position = rear; slot.Speed = rider.SpeedMetersPerSecond; slot.Initialized = true;
        }

        /// <summary>IDs deduplicate repeated reliable events; stale reconnect history never bursts at the camera.</summary>
        public void OnEvent(RaceEventReadModel item, RaceWorldReadModel world, RaceRiderReadModel local, bool reducedMotion)
        {
            if (!initialized || item.Id <= lastEventId) return;
            lastEventId = item.Id;
            if (world == null || world.Tick - item.Tick > 24 || world.Tick < item.Tick) return;
            if (item.Kind != RaceEventKind.Hit && item.Kind != RaceEventKind.Crash && item.Kind != RaceEventKind.Landed) return;
            int id = item.TargetId > 0 ? item.TargetId : item.SourceId;
            RaceRiderReadModel target = local;
            bool found = id == local.Id;
            if (!found) for (int i = 0; i < world.Riders.Count; i++)
            {
                if (world.Riders[i].Id != id) continue;
                target = world.Riders[i]; found = true; break;
            }
            if (!found || Mathf.Abs(target.LongitudinalMeters - local.LongitudinalMeters) > (lowQuality ? 35 : 65)) return;
            var fx = impacts[impactCursor++ % ImpactSlots];
            fx.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            float height = item.Kind == RaceEventKind.Hit ? .9f : .18f;
            fx.transform.position = road.Point(target.LongitudinalMeters, target.LateralMeters, target.HeightMeters + height);
            int count = item.Kind == RaceEventKind.Crash ? 20 : item.Kind == RaceEventKind.Hit ? 10 : 7;
            if (lowQuality) count = (count + 1) / 2;
            if (reducedMotion) count = Mathf.Max(2, count / 4);
            fx.Play(); fx.Emit(count);
            EmittedImpactCount++;
        }

        private ParticleSystem CreateParticles(string label, Material material, bool dust)
        {
            var obj = new GameObject(label); obj.transform.SetParent(transform, false);
            var particles = obj.AddComponent<ParticleSystem>();
            particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = particles.main;
            main.playOnAwake = false; main.loop = dust; main.duration = dust ? 1 : .6f;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = dust ? 36 : 24;
            main.startLifetime = new ParticleSystem.MinMaxCurve(dust ? .35f : .1f, dust ? .85f : .38f);
            main.startSize = new ParticleSystem.MinMaxCurve(dust ? .25f : .025f, dust ? .72f : .055f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(dust ? .35f : 1.7f, dust ? 1.3f : 4.3f);
            main.startColor = dust ? new Color(.68f, .46f, .25f, .22f) : new Color(1, .61f, .2f, .9f);
            main.gravityModifier = dust ? -.025f : .7f;
            var shape = particles.shape; shape.shapeType = dust ? ParticleSystemShapeType.Cone : ParticleSystemShapeType.Sphere;
            shape.radius = dust ? .16f : .12f; if (dust) shape.angle = 23;
            var emission = particles.emission; emission.rateOverTime = 0;
            var color = particles.colorOverLifetime; color.enabled = true;
            var gradient = new Gradient();
            gradient.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, .12f), new GradientAlphaKey(0, 1) });
            color.color = gradient;
            var size = particles.sizeOverLifetime; size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, dust ? .35f : 1, 1, dust ? 1.4f : .1f));
            var renderer = obj.GetComponent<ParticleSystemRenderer>();
            renderer.sharedMaterial = material; renderer.shadowCastingMode = ShadowCastingMode.Off; renderer.receiveShadows = false;
            renderer.renderMode = dust ? ParticleSystemRenderMode.Billboard : ParticleSystemRenderMode.Stretch;
            if (!dust) { renderer.velocityScale = .025f; renderer.lengthScale = 1.5f; }
            return particles;
        }

        private static void Retire(RiderEffect slot)
        {
            slot.Id = 0; slot.Initialized = false; slot.Trail.emitting = false; slot.Trail.Clear();
            slot.Dust.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        }

        private void OnDisable() { ResetEvents(); }

        private sealed class RiderEffect
        {
            public int Id; public bool Seen, Initialized; public float Speed; public Vector3 Position;
            public ParticleSystem Dust; public TrailRenderer Trail;
        }
    }
}
