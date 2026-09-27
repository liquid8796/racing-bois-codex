using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.Client.Application
{
    public enum RaceSessionMode { None, Local, Online }

    /// <summary>Local practice and the server use the same pure gameplay core. Online views interpolate authority snapshots.</summary>
    public sealed class RaceSession : IDisposable
    {
        private readonly IRealtimeTransport transport;
        private readonly IWireCodec codec;
        private readonly List<RaceEventReadModel> recentEvents = new List<RaceEventReadModel>(RaceProtocol.MaxEvents);
        private GameplayWorld localWorld;
        private readonly LocalCampaignProgress campaign = new LocalCampaignProgress();
        private long localRunId;
        private int sequence, ackSequence, seed = 1996, botCount = 5, level, courseIndex, bikeCatalogIndex, characterCatalogIndex;
        private bool disposed;
        public event Action Changed;
        public SessionStatus Status { get; private set; }
        public RaceSessionMode Mode { get; private set; }
        public string PlayerId { get; private set; } = "";
        public int RiderId { get; private set; }
        public string Error { get; private set; } = "";
        public int TickRate { get { return RaceProtocol.TickRate; } }
        public int SentInputs { get { return sequence; } }
        public int PendingCount { get { return Mode == RaceSessionMode.Online ? sequence - ackSequence : 0; } }
        public float LastCorrectionMeters { get { return 0; } }
        public RaceWorldReadModel LatestWorld { get; private set; }
        public RaceRiderReadModel LocalRider { get; private set; }
        public LocalCampaignReadModel LocalCampaign { get; private set; }

        public RaceSession(IRealtimeTransport transport, IWireCodec codec)
        {
            this.transport = transport ?? throw new ArgumentNullException(nameof(transport));
            this.codec = codec ?? throw new ArgumentNullException(nameof(codec));
            transport.Opened += OnOpened; transport.Message += OnMessage; transport.Closed += OnClosed;
        }

        public void StartLocal(int seed = 1996, int botCount = 5, int level = 0, int courseIndex = 0, int bikeCatalogIndex = 0, int characterCatalogIndex = 0)
        {
            ThrowIfDisposed();
            if (!CampaignCatalog.IsPlayableRoute(courseIndex)) throw new ArgumentException("Course production content is unavailable.", nameof(courseIndex));
            BikeCatalog.GetAt(bikeCatalogIndex); CharacterCatalog.GetAt(characterCatalogIndex); CampaignCatalog.ValidateLevel(level);
            Reset(); this.courseIndex = courseIndex; this.bikeCatalogIndex = bikeCatalogIndex; this.characterCatalogIndex = characterCatalogIndex;
            this.seed = seed; this.botCount = Math.Max(0, Math.Min(6, botCount)); this.level = Math.Max(0, Math.Min(4, level));
            localWorld = RaceSimulation.CreateDefault(seed, this.botCount, this.level, courseIndex);
            localRunId++;
            PublishCampaign();
            RiderId = 1; PlayerId = "local";
            var rider = RaceSimulation.AddPlayer(localWorld, RiderId);
            if (rider == null) throw new InvalidOperationException("Local rider could not be created.");
            rider.BikeCatalogIndex = bikeCatalogIndex; rider.CharacterCatalogIndex = characterCatalogIndex;
            Mode = RaceSessionMode.Local; Status = SessionStatus.Connected;
            LocalRider = RaceStateProjection.Rider(rider);
            LatestWorld = RaceStateProjection.World(localWorld, 0, Array.Empty<RaceEventReadModel>());
            Changed?.Invoke();
        }

        public void RestartLocal() { StartLocal(seed, botCount, level, courseIndex, bikeCatalogIndex, characterCatalogIndex); }

        public void Connect(string endpoint)
        {
            ThrowIfDisposed();
            if (!Uri.TryCreate(endpoint, UriKind.Absolute, out var uri) || (uri.Scheme != "ws" && uri.Scheme != "wss"))
                throw new ArgumentException("A ws:// or wss:// endpoint is required.", nameof(endpoint));
            Reset(); Mode = RaceSessionMode.Online; Status = SessionStatus.Connecting;
            Changed?.Invoke(); transport.Connect(endpoint);
        }

        public void Step(float throttle, float brake, float steer, int attackSide = 0, bool kick = false)
        {
            if (disposed || Status != SessionStatus.Connected) return;
            if (!Finite(throttle) || !Finite(brake) || !Finite(steer)) return;
            throttle = Clamp(throttle, 0, 1); brake = Clamp(brake, 0, 1); steer = Clamp(steer, -1, 1);
            attackSide = Math.Max(-1, Math.Min(1, attackSide));
            if (Mode == RaceSessionMode.Local)
            {
                RaceSimulation.SetInput(localWorld, RiderId, new RaceInput(Quantize(throttle), Quantize(brake), Quantize(steer), attackSide, kick));
                RaceSimulation.Step(localWorld); sequence++;
                LocalRider = RaceStateProjection.Rider(RaceSimulation.FindRider(localWorld, RiderId));
                // Only the current campaign level earns progress; custom-level practice cannot manufacture unlocks.
                if (level == campaign.Level && (LocalRider.Mode == RiderMode.Finished || LocalRider.Mode == RiderMode.Busted) &&
                    campaign.TryApplyResult(localRunId, courseIndex, LocalRider.Rank, LocalRider.Mode == RiderMode.Busted))
                    PublishCampaign();
                for (int i = 0; i < localWorld.EventCount; i++)
                {
                    var item = localWorld.Events[i];
                    if (recentEvents.Count == RaceProtocol.MaxEvents) recentEvents.RemoveAt(0);
                    recentEvents.Add(new RaceEventReadModel(item.Id, item.Tick, item.Kind, item.ActorId, item.TargetId, item.Value));
                }
                while (recentEvents.Count > 0 && recentEvents[0].Tick < localWorld.Tick - 120) recentEvents.RemoveAt(0);
                if (localWorld.Tick % (RaceProtocol.TickRate / RaceProtocol.SnapshotRate) == 0)
                    LatestWorld = RaceStateProjection.World(localWorld, sequence, recentEvents.ToArray());
                return;
            }
            if (PendingCount >= TickRate * 2) { Fail("Máy chủ không phản hồi. Hãy kết nối lại."); return; }
            if (sequence == int.MaxValue) { Fail("Phiên chạy đã hết giới hạn. Hãy kết nối lại."); return; }
            transport.Send(codec.Encode(new RaceInputMessage { playerId = PlayerId, sequence = ++sequence,
                throttle = throttle, brake = brake, steer = steer, attackSide = attackSide, kick = kick }));
        }

        public void Poll() { if (!disposed) transport.Poll(); }
        public void Disconnect() { if (disposed) return; Reset(); Changed?.Invoke(); }

        private void Reset()
        {
            Status = SessionStatus.Offline; Mode = RaceSessionMode.None; PlayerId = ""; RiderId = 0;
            sequence = ackSequence = 0; Error = ""; localWorld = null; LatestWorld = null; LocalRider = default;
            recentEvents.Clear(); transport.Close();
        }
        private void OnOpened()
        {
            if (!disposed && Mode == RaceSessionMode.Online && Status == SessionStatus.Connecting)
                transport.Send(codec.Encode(new RaceHelloMessage()));
        }
        private void OnMessage(string text)
        {
            if (disposed || Mode != RaceSessionMode.Online || Status == SessionStatus.Offline || Status == SessionStatus.Failed) return;
            if (text == null || text.Length > 32768) { Fail("Phản hồi máy chủ vượt giới hạn."); return; }
            try
            {
                var envelope = codec.Decode<MessageEnvelope>(text);
                if (envelope == null) return;
                if (envelope.kind == "raceWelcome" && Status == SessionStatus.Connecting)
                {
                    var welcome = codec.Decode<RaceWelcomeMessage>(text);
                    if (welcome.protocolVersion != RaceProtocol.Version || welcome.simulationRulesVersion != RaceProtocol.SimulationRulesVersion ||
                        welcome.contentHash != RaceProtocol.ContentHash || welcome.tickRate != RaceProtocol.TickRate ||
                        welcome.snapshotRate != RaceProtocol.SnapshotRate || welcome.maxPlayers != RaceProtocol.MaxPlayers ||
                        string.IsNullOrWhiteSpace(welcome.playerId) || welcome.playerId.Length > 32 || welcome.riderId < 1 || welcome.riderId > 999)
                    { Fail("Phiên bản máy chủ không tương thích."); return; }
                    PlayerId = welcome.playerId; RiderId = welcome.riderId; Status = SessionStatus.Connected; Changed?.Invoke();
                }
                else if (envelope.kind == "raceSnapshot" && Status == SessionStatus.Connected)
                {
                    var snapshot = codec.Decode<RaceSnapshotMessage>(text);
                    if (snapshot.protocolVersion != RaceProtocol.Version || snapshot.playerId != PlayerId || snapshot.riderId != RiderId ||
                        (LatestWorld != null && snapshot.tick <= LatestWorld.Tick)) return;
                    RaceSnapshotValidator.Validate(snapshot, RiderId, sequence, ackSequence);
                    var world = RaceStateProjection.World(snapshot);
                    RaceRiderReadModel own = default;
                    for (int i = 0; i < world.Riders.Count; i++) if (world.Riders[i].Id == RiderId) own = world.Riders[i];
                    LatestWorld = world; LocalRider = own; ackSequence = snapshot.ackSequence;
                }
                else if (envelope.kind == "error")
                {
                    var error = codec.Decode<ErrorMessage>(text);
                    if (Status == SessionStatus.Connecting) Fail("Máy chủ từ chối kết nối: " + error.code);
                    else { Error = "Máy chủ từ chối yêu cầu: " + error.code; Changed?.Invoke(); }
                }
            }
            catch (Exception) { Error = "Không đọc được phản hồi máy chủ."; Changed?.Invoke(); }
        }
        private void OnClosed(string reason)
        {
            if (!disposed && Mode == RaceSessionMode.Online && Status != SessionStatus.Offline && Status != SessionStatus.Failed)
            { Status = SessionStatus.Failed; Error = "Mất kết nối. Bạn có thể thử lại."; Changed?.Invoke(); }
        }
        private void Fail(string error)
        { Status = SessionStatus.Failed; Error = error; transport.Close(); Changed?.Invoke(); }
        public void Dispose()
        {
            if (disposed) return;
            Reset(); disposed = true;
            transport.Opened -= OnOpened; transport.Message -= OnMessage; transport.Closed -= OnClosed; transport.Dispose();
        }
        private void ThrowIfDisposed() { if (disposed) throw new ObjectDisposedException(nameof(RaceSession)); }
        private void PublishCampaign()
        { LocalCampaign = new LocalCampaignReadModel(campaign.Level, campaign.QualifiedCourseMask, campaign.Credits, campaign.Completed, campaign.LastAppliedRunId); }
        private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static int Quantize(float value) => (int)Math.Round(value * 1000, MidpointRounding.AwayFromZero);
        private static float Clamp(float value, float min, float max) => value < min ? min : value > max ? max : value;
    }
}
