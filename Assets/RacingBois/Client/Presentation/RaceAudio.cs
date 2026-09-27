using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using UnityEngine;

namespace RacingBois.Client.Presentation
{
    /// <summary>Read-only bounded mix; authority never depends on audio timing.</summary>
    public sealed class RaceAudio : MonoBehaviour
    {
        private const int VoiceCount = 8;
        private readonly AudioSource[] voices = new AudioSource[VoiceCount];
        private AudioSource engineLow, engineHigh, tire, gravel, wind, ambient, music, neighborEngine, policeSiren;
        private bool p08Content;
        private int activeBike=-1,stepBucket=-1;
        private RiderMode previousMode;
        private RaceAudioBank bank;
        private long lastEventId, lastTick;
        private int voiceCursor, previousGear, previousRider;
        private float previousSpeed, shiftEnvelope, duckEnvelope, filteredRpm;
        private bool initialized, muted, unlocked, wasActive;
        public bool Muted => muted;
        public bool Unlocked => unlocked;
        public bool HasBank => bank != null && bank.HasGameplayEffects;
        public float NormalizedRpm => filteredRpm;
        public float MusicDuck => duckEnvelope;
        public int PlayedEventCount { get; private set; }

        public void Initialize(RaceAudioBank audioBank = null)
        {
            if (initialized) return;
            initialized = true;
            bank = audioBank;
            engineLow = CreateSource("Engine low", bank != null ? bank.EngineLow : null, true);
            engineHigh = CreateSource("Engine high", bank != null ? bank.EngineHigh : null, true);
            tire = CreateSource("Tire", bank != null ? bank.Tire : null, true);
            gravel = CreateSource("Gravel", bank != null ? bank.Gravel : null, true);
            wind = CreateSource("Wind", bank != null ? bank.Wind : null, true);
            ambient = CreateSource("Canyon ambience", bank != null ? bank.Ambient : null, true);
            music = CreateSource("Canyon drive score", bank != null ? bank.Music : null, true);
            neighborEngine=CreateSource("Nearby engine",null,true);policeSiren=CreateSource("Police siren",null,true);
            for (int i = 0; i < VoiceCount; i++) voices[i] = CreateSource("Transient " + i, null, false);
#if !UNITY_WEBGL || UNITY_EDITOR
            unlocked = true;
#endif
        }

        public void ApplyContent(P08ContentLibrary library)
        {
            if (library == null || library.AudioBank == null || !library.AudioBank.HasGameplayEffects)
                throw new System.ArgumentException("Complete streamed audio content is required.");
            if (!initialized) Initialize(library.AudioBank);
            StopAllSources(); bank = library.AudioBank;p08Content=true;activeBike=-1;
            engineLow.clip=bank.EngineLow;engineHigh.clip=bank.EngineHigh;tire.clip=bank.Tire;gravel.clip=bank.Gravel;
            wind.clip=bank.Wind;ambient.clip=bank.Ambient;music.clip=null;ResetEvents();
        }
        public void BeforeContentUnload()
        {
            if (!initialized) return;
            music.Stop(); music.clip=null; music.volume=0;
            // Transients only reference the retained actor library. Route music is detached before its bundle unloads.
        }
        private AudioSource CreateSource(string label, AudioClip clip, bool loop)
        {
            var child = new GameObject(label);
            child.transform.SetParent(transform, false);
            var source = child.AddComponent<AudioSource>();
            source.clip = clip; source.loop = loop; source.playOnAwake = false;
            source.spatialBlend = 0; source.volume = 0; source.priority = loop ? 160 : 80; source.dopplerLevel = 0;
            return source;
        }

        /// <summary>Call from a user activation; Unity's Web runtime resumes its AudioContext.</summary>
        public void UnlockFromUserGesture() { unlocked = true; }

        public void SetMuted(bool value)
        {
            if (muted == value) return;
            muted = value;
            if (muted && initialized) { StopAllSources(); duckEnvelope = 0; }
        }

        public void ResetEvents()
        {
            lastEventId = lastTick = 0;
            previousGear = previousRider = 0;
            previousSpeed = shiftEnvelope = duckEnvelope = filteredRpm = 0;stepBucket=-1;
        }

        public void Render(RaceWorldReadModel world, RaceRiderReadModel rider, bool active, bool audioEnabled, float dt)
        {
            if (!initialized) return;
            SetMuted(!audioEnabled);
            dt = Mathf.Clamp(dt, 0, .1f);
            if (wasActive != active || previousRider != rider.Id ||
                (world != null && world.Tick < 60 && lastTick > 120)) ResetEvents();
            wasActive = active; previousRider = rider.Id;
            bool audible = unlocked && !muted && HasBank;
            bool driving = active && GameplayRules.CanDrive(rider.Mode);
            bool ground = driving && rider.Mode != RiderMode.Airborne;
            float speed = Mathf.Max(0, rider.SpeedMetersPerSecond), speed01 = Mathf.Clamp01(speed / (BikeHandlingCatalog.GetAt(rider.BikeCatalogIndex).MaximumSpeedMillimetersPerSecond / 1000f));
            float acceleration = dt > 0 ? Mathf.Clamp((speed - previousSpeed) / dt, -24, 12) : 0;
            previousSpeed = speed;
            int gear = Mathf.Clamp(rider.Gear, 1, 6);
            float rpm = Mathf.Clamp01(.23f + (speed - (gear - 1) * 9.3f) / 11.5f * .77f);
            if (driving && previousGear != 0 && previousGear != gear)
            {
                shiftEnvelope = 1;
                if (audible) Play(bank.Shift, .11f, 1, 0);
            }
            previousGear = driving ? gear : 0;
            shiftEnvelope = Mathf.MoveTowards(shiftEnvelope, 0, dt * 6);
            filteredRpm = Mathf.Lerp(filteredRpm, rpm, 1 - Mathf.Exp(-dt * 12));
            if(p08Content&&activeBike!=rider.BikeCatalogIndex)
            {activeBike=rider.BikeCatalogIndex;SetClip(engineLow,Sfx(P08AudioRoles.Engine(activeBike),bank.EngineLow));SetClip(engineHigh,Sfx("boost-pressure",bank.EngineHigh));}
            float engineGain = driving ? .105f * (1 - shiftEnvelope * .58f) : 0;
            float drivePitch = .73f + filteredRpm * 1.25f;
            SetLoop(engineLow, audible ? engineGain * (1 - filteredRpm * .55f) : 0, drivePitch, dt);
            SetLoop(engineHigh, audible ? engineGain * (.16f + filteredRpm * .67f) : 0, drivePitch, dt);
            bool offroad = Mathf.Abs(rider.LateralMeters) > (world == null ? TrackDefinition.Default : world.Track).RoadHalfWidthMillimeters / 1000f;
            float skid = ground && !offroad ? Mathf.Clamp01((-acceleration - 5) / 17 + (Mathf.Abs(rider.LeanDegrees) - 25) / 42) : 0;
            SetLoop(tire, audible && ground && !offroad ? (.012f * speed01 + skid * .046f) : 0, .85f + speed01 * .48f, dt);
            SetLoop(gravel, audible && ground && offroad ? .075f * speed01 : 0, .75f + speed01 * .7f, dt);
            SetLoop(wind, audible && driving ? .048f * speed01 * speed01 : 0, .82f + speed01 * .38f, dt);
            SetLoop(ambient, audible ? (active ? .018f : .027f) : 0, 1, dt);
            duckEnvelope = Mathf.MoveTowards(duckEnvelope, 0, dt * 2.3f);
            if(!p08Content)SetLoop(music, audible ? (active ? .063f : .077f) * (1 - duckEnvelope * .7f) : 0, 1, dt);
            else RenderContentLayers(world,rider,active,audible,dt);
            if (world == null) return;
            lastTick = world.Tick;
            for (int i = 0; i < world.Events.Count; i++)
            {
                var item = world.Events[i];
                OnEvent(item, rider, active && world.Tick - item.Tick <= 45);
            }
        }

        private static void SetLoop(AudioSource source, float target, float pitch, float dt)
        {
            source.volume = Mathf.MoveTowards(source.volume, target, dt * .6f);
            source.pitch = Mathf.Clamp(pitch, .5f, 2.2f);
            if (source.clip == null) return;
            if (target > .0001f && !source.isPlaying) source.Play();
            if (target <= 0 && source.volume <= 0 && source.isPlaying) source.Stop();
        }

        /// <summary>Render also calls this; event IDs suppress reliable/snapshot duplicates.</summary>
        public void OnEvent(RaceEventReadModel item, RaceRiderReadModel rider, bool active)
        {
            if (item.Id <= lastEventId) return;
            lastEventId = item.Id;
            if (!active || muted || !unlocked || !HasBank ||
                (item.SourceId != rider.Id && item.TargetId != rider.Id)) return;
            AudioClip clip; float gain = .18f;
            switch (item.Kind)
            {
                case RaceEventKind.Attack: clip = p08Content?Sfx(P08AudioRoles.Attack(rider.AttackWeapon),bank.WeaponSwing):bank.WeaponSwing; gain = .095f; break;
                case RaceEventKind.Hit:
                    // A victim cannot infer the attacker's weapon from their own loadout.
                    clip = p08Content?Sfx(P08AudioRoles.Hit(item.SourceId==rider.Id?rider.AttackWeapon:WeaponKind.Fist,item.Id),bank.Impact):item.SourceId == rider.Id ? WeaponClip(rider.AttackWeapon) : bank.Impact;
                    duckEnvelope = Mathf.Max(duckEnvelope, .7f); break;
                case RaceEventKind.Crash: case RaceEventKind.Wrecked:
                    clip = p08Content?Sfx(P08AudioRoles.Crash(item.Value,item.Kind==RaceEventKind.Wrecked),bank.Crash):bank.Crash; gain = .24f; duckEnvelope = 1; break;
                case RaceEventKind.Landed: clip = p08Content?Sfx("suspension-bottom",bank.Impact):bank.Impact; gain = .12f; duckEnvelope = Mathf.Max(duckEnvelope, .4f); break;
                case RaceEventKind.WeaponStolen: case RaceEventKind.Remounted: clip = bank.UiConfirm; gain = .1f; break;
                case RaceEventKind.Finished: clip = bank.Finish; gain = .2f; duckEnvelope = 1; break;
                case RaceEventKind.Busted: clip = bank.UiBack; gain = .16f; duckEnvelope = 1; break;
                default: return;
            }
            Play(clip, gain, .97f + (item.Id % 7) * .01f, rider.AttackSide * .22f);
            if(p08Content)
            {
                string reaction=P08AudioRoles.Reaction(rider.CharacterCatalogIndex,item.Kind);
                if(reaction.Length>0&&ContentRegistry.Voices.TryGetValue(reaction,out var voice))Play(voice,.10f,1,0);
            }
            PlayedEventCount++;
        }

        private AudioClip Sfx(string id,AudioClip fallback=null)=>ContentRegistry.Sfx.TryGetValue(id,out var clip)?clip:fallback;
        private static void SetClip(AudioSource source,AudioClip clip){if(source.clip==clip)return;source.Stop();source.clip=clip;}
        private void RenderContentLayers(RaceWorldReadModel world,RaceRiderReadModel rider,bool active,bool audible,float dt)
        {
            float opponent=200,traffic=200,police=200;
            if(world!=null&&active)
            {
                foreach(var other in world.Riders)if(other.Id!=rider.Id)
                {float separation=Mathf.Abs(other.LongitudinalMeters-rider.LongitudinalMeters);if(other.Kind==RiderKind.Police)police=Mathf.Min(police,separation);else opponent=Mathf.Min(opponent,separation);}
                foreach(var other in world.Traffic)traffic=Mathf.Min(traffic,Mathf.Abs(other.LongitudinalMeters-rider.LongitudinalMeters));
            }
            SetClip(neighborEngine,Sfx(opponent<traffic?"opponent-engine":"traffic-four-cylinder"));
            SetLoop(neighborEngine,audible&&active?.026f*Mathf.Clamp01(1-Mathf.Min(opponent,traffic)/42):0,1,dt);
            SetClip(policeSiren,Sfx(police<32?"patrol-long-call":"patrol-short-call"));
            SetLoop(policeSiren,audible&&active?.033f*Mathf.Clamp01(1-police/80):0,1,dt);
            float tunnelDistance=Mathf.Abs(Mathf.Repeat(rider.LongitudinalMeters+55+320,640)-320);
            SetClip(music,Sfx("tunnel-engine-resonance"));
            SetLoop(music,audible&&active&&world!=null&&world.CourseIndex==2?.028f*Mathf.Clamp01(1-tunnelDistance/22):0,.8f+Mathf.Clamp01(rider.SpeedMetersPerSecond/60)*.4f,dt);
            int bucket=rider.StateTicks/12;
            if(audible&&active&&rider.Mode==RiderMode.Running&&(previousMode!=rider.Mode||stepBucket!=bucket))Play(Sfx("boot-asphalt-step"),.10f,1,0);
            if(audible&&active&&rider.Mode==RiderMode.Falling&&previousMode!=rider.Mode)Play(Sfx("leather-road-slide"),.12f,1,0);
            previousMode=rider.Mode;stepBucket=bucket;
        }
        private AudioClip WeaponClip(WeaponKind weapon)
        {
            switch (weapon)
            {
                case WeaponKind.Club: return bank.WeaponClub;
                case WeaponKind.Chain: return bank.WeaponChain;
                default: return bank.WeaponFist;
            }
        }

        public void PlayUi(bool confirm = true)
        {
            if (muted || !unlocked || !HasBank || !initialized) return;
            Play(confirm ? bank.UiConfirm : bank.UiBack, .095f, 1, 0);
        }

        private void Play(AudioClip clip, float gain, float pitch, float pan)
        {
            if (clip == null) return;
            int chosen = voiceCursor;
            for (int i = 0; i < VoiceCount; i++)
            {
                int index = (voiceCursor + i) % VoiceCount;
                if (!voices[index].isPlaying) { chosen = index; break; }
            }
            var voice = voices[chosen];
            // Fixed transient headroom: even eight simultaneous maximum-gain hits stay below full scale.
            voice.Stop(); voice.clip = clip; voice.volume = gain * .35f; voice.pitch = pitch;
            voice.panStereo = Mathf.Clamp(pan, -.4f, .4f); voice.Play();
            voiceCursor = (chosen + 1) % VoiceCount;
        }

        private void StopAllSources()
        {
            engineLow.Stop(); engineHigh.Stop(); tire.Stop(); gravel.Stop(); wind.Stop(); ambient.Stop(); music.Stop();neighborEngine.Stop();policeSiren.Stop();
            engineLow.volume = engineHigh.volume = tire.volume = gravel.volume = wind.volume = ambient.volume = music.volume = neighborEngine.volume = policeSiren.volume = 0;
            for (int i = 0; i < VoiceCount; i++) voices[i].Stop();
        }

        private void OnDisable() { if (initialized) StopAllSources(); }
    }
}
