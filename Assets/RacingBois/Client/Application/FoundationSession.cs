using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.Client.Application
{
    public interface IRealtimeTransport : IDisposable
    {
        event Action Opened;
        event Action<string> Message;
        event Action<string> Closed;
        void Connect(string endpoint);
        void Send(string text);
        void Close();
        void Poll();
    }

    public interface IWireCodec
    {
        string Encode(object message);
        T Decode<T>(string text) where T : class;
    }

    public enum SessionStatus { Offline, Connecting, Connected, Failed }

    [Serializable]
    public sealed class MessageEnvelope { public string kind; }

    /// <summary>Owns connection and prototype prediction. No Unity, render, storage or socket API dependency.</summary>
    public sealed class FoundationSession : IDisposable
    {
        private readonly IRealtimeTransport transport;
        private readonly IWireCodec codec;
        private readonly Queue<PendingInput> pending = new Queue<PendingInput>();
        private int sequence;
        private bool disposed;
        private struct PendingInput { public int Sequence; public RiderInput Input; }

        public event Action Changed;
        public SessionStatus Status { get; private set; }
        public string PlayerId { get; private set; } = "";
        public string Error { get; private set; } = "";
        public int TickRate { get; private set; } = PrototypeRules.TickRate;
        public int SentInputs { get { return sequence; } }
        public WorldReadModel LatestWorld { get; private set; }
        public RiderState PredictedState { get; private set; }
        public float LastCorrectionMeters { get; private set; }
        public int PendingCount { get { return pending.Count; } }

        public FoundationSession(IRealtimeTransport transport, IWireCodec codec)
        {
            this.transport = transport;
            this.codec = codec;
            transport.Opened += OnOpened;
            transport.Message += OnMessage;
            transport.Closed += OnClosed;
        }

        public void Connect(string endpoint)
        {
            if (disposed) throw new ObjectDisposedException(nameof(FoundationSession));
            transport.Close();
            pending.Clear(); sequence = 0; PlayerId = ""; LatestWorld = null;
            PredictedState = default(RiderState); Error = "";
            Status = SessionStatus.Connecting; Changed?.Invoke();
            transport.Connect(endpoint);
        }

        private void OnOpened()
        {
            if (!disposed && Status == SessionStatus.Connecting) transport.Send(codec.Encode(new HelloMessage()));
        }

        private void OnMessage(string text)
        {
            if (disposed || Status == SessionStatus.Offline || Status == SessionStatus.Failed) return;
            try
            {
                var envelope = codec.Decode<MessageEnvelope>(text);
                if (envelope == null) return;
                if (envelope.kind == "welcome")
                {
                    if (Status != SessionStatus.Connecting) return;
                    var welcome = codec.Decode<WelcomeMessage>(text);
                    if (welcome.protocolVersion != WireProtocol.Version ||
                        welcome.simulationRulesVersion != PrototypeRules.Version ||
                        welcome.contentHash != PrototypeRules.ContentHash ||
                        welcome.tickRate != PrototypeRules.TickRate || string.IsNullOrWhiteSpace(welcome.playerId))
                    {
                        Error = "Phiên bản máy chủ không tương thích.";
                        Status = SessionStatus.Failed; transport.Close(); Changed?.Invoke(); return;
                    }
                    PlayerId = welcome.playerId; TickRate = welcome.tickRate;
                    Status = SessionStatus.Connected; Changed?.Invoke();
                }
                else if (envelope.kind == "snapshot")
                {
                    if (Status != SessionStatus.Connected) return;
                    var snapshot = codec.Decode<SnapshotMessage>(text);
                    if (snapshot.protocolVersion != WireProtocol.Version || snapshot.playerId != PlayerId ||
                        (LatestWorld != null && snapshot.tick <= LatestWorld.Tick)) return;
                    if (snapshot.entities == null || snapshot.entities.Length == 0 || snapshot.entities.Length > PrototypeRules.MaxPlayers ||
                        snapshot.ackSequence < 0 || snapshot.ackSequence > sequence ||
                        (LatestWorld != null && snapshot.ackSequence < LatestWorld.AcknowledgedInputSequence))
                        throw new InvalidOperationException("Invalid snapshot envelope");
                    bool hasLocalPlayer = false;
                    var ids = new HashSet<string>();
                    foreach (var entity in snapshot.entities)
                    {
                        if (entity == null || string.IsNullOrWhiteSpace(entity.id) || !ids.Add(entity.id) ||
                            !Finite(entity.s) || !Finite(entity.d) || !Finite(entity.speed) || entity.s < 0 || entity.speed < 0 ||
                            entity.speed > PrototypeRules.MaximumSpeedMillimetersPerSecond / 1000f ||
                            Math.Abs(entity.d) > PrototypeRules.RoadHalfWidthMillimeters / 1000f)
                            throw new InvalidOperationException("Invalid entity snapshot");
                        hasLocalPlayer |= entity.id == PlayerId;
                    }
                    if (!hasLocalPlayer) throw new InvalidOperationException("Local player absent");
                    var riders = new RiderReadModel[snapshot.entities.Length];
                    for (int i = 0; i < riders.Length; i++)
                    {
                        var entity = snapshot.entities[i];
                        riders[i] = new RiderReadModel(entity.id, entity.s, entity.d, entity.speed);
                    }
                    LatestWorld = new WorldReadModel(snapshot.tick, snapshot.ackSequence, riders);
                    foreach (var entity in snapshot.entities)
                    {
                        if (entity.id != PlayerId) continue;
                        var corrected = new RiderState
                        {
                            DistanceMillimeters = (long)Math.Round(entity.s * 1000),
                            LateralMillimeters = (int)Math.Round(entity.d * 1000),
                            SpeedMillimetersPerSecond = (int)Math.Round(entity.speed * 1000)
                        };
                        while (pending.Count > 0 && pending.Peek().Sequence <= snapshot.ackSequence) pending.Dequeue();
                        foreach (var input in pending) corrected = RoadSpaceSimulation.Step(corrected, input.Input);
                        LastCorrectionMeters = (float)Math.Abs(corrected.DistanceMillimeters - PredictedState.DistanceMillimeters) / 1000;
                        PredictedState = corrected;
                        break;
                    }
                }
                else if (envelope.kind == "error")
                {
                    var error = codec.Decode<ErrorMessage>(text);
                    Error = "Máy chủ từ chối yêu cầu: " + error.code;
                    if (Status != SessionStatus.Connected) Status = SessionStatus.Failed;
                    Changed?.Invoke();
                }
            }
            catch (Exception) { Error = "Không đọc được phản hồi máy chủ."; Changed?.Invoke(); }
        }

        public void Step(float throttle, float brake, float steer)
        {
            if (disposed) return;
            if (Status != SessionStatus.Connected) return;
            if (pending.Count >= TickRate * 2)
            {
                Error = "Máy chủ không phản hồi. Hãy kết nối lại.";
                Status = SessionStatus.Failed; transport.Close(); Changed?.Invoke(); return;
            }
            var input = new RiderInput((int)Math.Round(throttle * 1000, MidpointRounding.AwayFromZero),
                (int)Math.Round(brake * 1000, MidpointRounding.AwayFromZero),
                (int)Math.Round(steer * 1000, MidpointRounding.AwayFromZero));
            PredictedState = RoadSpaceSimulation.Step(PredictedState, input);
            pending.Enqueue(new PendingInput { Sequence = ++sequence, Input = input });
            transport.Send(codec.Encode(new InputMessage { playerId = PlayerId, sequence = sequence,
                throttle = throttle, brake = brake, steer = steer }));
        }

        public void Disconnect()
        {
            if (disposed) return;
            Status = SessionStatus.Offline; Error = ""; PlayerId = ""; pending.Clear();
            LatestWorld = null; PredictedState = default(RiderState); LastCorrectionMeters = 0;
            transport.Close(); Changed?.Invoke();
        }

        private void OnClosed(string reason)
        {
            if (Status == SessionStatus.Offline || disposed) return;
            Status = SessionStatus.Failed;
            if (string.IsNullOrEmpty(Error)) Error = "Mất kết nối. Bạn có thể thử lại.";
            Changed?.Invoke();
        }

        public void Dispose()
        {
            if (disposed) return;
            disposed = true;
            Status = SessionStatus.Offline; pending.Clear(); PlayerId = ""; LatestWorld = null;
            transport.Opened -= OnOpened; transport.Message -= OnMessage; transport.Closed -= OnClosed;
            transport.Dispose();
        }

        private static bool Finite(float value) { return !float.IsNaN(value) && !float.IsInfinity(value); }
    }
}
