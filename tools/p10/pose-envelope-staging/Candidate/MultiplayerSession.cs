using System;
using System.Collections.Generic;
using RacingBois.Gameplay.Definitions;
using RacingBois.NetworkMapping;
using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.Client.Application
{
    /// <summary>One v3 lease, exact-tick input history, isolated prediction and immutable UI projections.</summary>
    public sealed partial class MultiplayerSession : IDisposable
    {
        private readonly IRealtimeTransport transport;
        private readonly IWireCodec codec;
        private readonly IMonotonicClock clock;
        private readonly IResumeReceiptStore resumeStore;
        private readonly IProfileCredentialStore credentials;
        private readonly List<InputFrame> pending = new List<InputFrame>(120);
        private readonly List<RaceEventReadModel> events = new List<RaceEventReadModel>(128);
        private readonly RemoteMotionSampler remotes = new RemoteMotionSampler();
        private readonly RenderProbe[] probes = new RenderProbe[120];
        private readonly PredictionNeighbors predictionNeighbors = new PredictionNeighbors();
        private readonly RiderCheckpoint[] predictedHistory = new RiderCheckpoint[121];
        private LocalPlayerProfile profile;
        private ProfileCredential credential;
        private ResumeReceipt receipt;
        private RiderPredictor predictor;
        private MultiplayerSnapshotReadModel latestPredictionSnapshot;
        private RiderCheckpoint authoritative;
        private RaceInput heldAnalog;
        private bool hasCheckpoint, disposed, closingTransport, freshGuest, waitingWelcome;
        private string endpoint = "", helloNonce = "", pingNonce = "", welcomeProfileToken = "", realmId = "", serverProfileId = "", displayName = "";
        private int sessionEpoch, raceEpoch, sequence, processedSequence, requestId, leaveRequest, logoutRequest, reconnectAttempt;
        private double logoutDeadline;
        private long reliableSequence, lastTargetTick, lastAppliedInputTick, pingMicros, lastServiceStamp = -1;
        private double clockAnchorTick, clockAnchorAt, lastReceiveAt, lastSnapshotAt, connectAt, reconnectAt, nextPingAt, rtt, jitter, stableSince;
        private int snapshotRevision, eventRevision, cachedSnapshotRevision = -1, cachedEventRevision = -1;
        private long cachedSampleTick = -1, cachedSmoothingFrame = -1;
        private bool cachedPrediction;
        private RaceWorldReadModel cachedPresentation;
        private RaceRiderReadModel predictedRider;
        private float correctionS, correctionD;
        private double correctionAt;
        public event Action Changed;
        public SessionStatus Status { get; private set; }
        public string Error { get; private set; } = "";
        public string PlayerId { get; private set; } = "";
        public string SessionId => PlayerId;
        /// <summary>Lease identity for resetting renderer-only continuity; grants no authority.</summary>
        public int PresentationSessionEpoch => sessionEpoch;
        public int RiderId { get; private set; }
        public int CurrentCredits { get; private set; }
        public bool IsGuest { get; private set; }
        public bool ResultsPending { get; private set; }
        public bool IsReconnecting { get; private set; }
        public bool IsSuspended { get; private set; }
        public bool IsDisconnecting => logoutRequest != 0;
        public bool PresentationFrozen { get; private set; }
        public bool ActorsAlreadyInterpolated => true;
        public bool IsHost => Room != null && Room.HostPlayerId == PlayerId;
        public LobbyReadModel Room { get; private set; }
        public IReadOnlyList<LobbySummaryReadModel> Lobbies { get; private set; } = Array.AsReadOnly(new LobbySummaryReadModel[0]);
        public MultiplayerResultReadModel Result { get; private set; }
        public IReadOnlyList<MultiplayerStandingReadModel> Standings { get; private set; } = Array.AsReadOnly(new MultiplayerStandingReadModel[0]);
        public int RacingParticipantCount => Standings.Count;
        public RaceWorldReadModel LatestAuthoritativeWorld { get; private set; }
        public RaceWorldReadModel LatestWorld => LatestAuthoritativeWorld;
        public RaceRiderReadModel LocalRider { get; private set; }
        public int PendingInputCount => pending.Count;
        public int SentInputs => sequence;
        public long LastResolvedTick => hasCheckpoint ? authoritative.Tick : 0;
        public float LastCorrectionMeters { get; private set; }
        /// <summary>Changes only for a measured equal-target prediction correction, not ordinary snapshots.</summary>
        public long PresentationCorrectionRevision { get; private set; }
        public float MaximumCorrectionMeters { get; private set; }
        public double RttMs => rtt * 1000;
        public double RttMilliseconds => RttMs;
        public int InputLeadTicks => Math.Max(2, Math.Min(16, (int)Math.Ceiling((rtt * .5 + jitter) * 60) + 2));
        public double CountdownSeconds => Room == null || Room.Phase != LobbyPhase.Countdown ? 0 : Math.Max(0, (Room.StartServiceTick - EstimatedServiceTick) / 60);
        public int StaleRemoteCount => remotes.StaleActors;
        public double RemoteExtrapolationMs => remotes.ExtrapolationMilliseconds;
        public int EventCappedRemoteCount => remotes.EventCappedActors;
        public int InvalidSnapshots { get; private set; }
        public int LateInputs { get; private set; }
        public int FutureInputs { get; private set; }
        public int MissingInputs { get; private set; }
        public int NearCombatResidualSamples { get; private set; }
        public float NearCombatResidualMeters { get; private set; }
        public float MaximumNearCombatResidualMeters { get; private set; }
        public int SteadyResidualSamples { get; private set; }
        public float MaximumSteadyResidualMeters { get; private set; }
        public int ContactResidualSamples { get; private set; }
        public float MaximumContactResidualMeters { get; private set; }
        public bool PredictionEnabled => hasCheckpoint && Status == SessionStatus.Connected && !IsSuspended &&
            !ResultsPending && !GameplayRules.IsTerminal(authoritative.Data.Mode) && Room != null &&
            (Room.Phase == LobbyPhase.Countdown || Room.Phase == LobbyPhase.Racing) && clock.NowSeconds - lastSnapshotAt < 1;
        private double EstimatedServiceTick => clockAnchorTick + Math.Max(0, clock.NowSeconds - clockAnchorAt) * 60;

        private readonly struct InputFrame
        {
            public readonly long Tick; public readonly int Sequence; public readonly RaceInput Input;
            public InputFrame(long tick, int sequence, RaceInput input) { Tick = tick; Sequence = sequence; Input = input; }
        }
        private struct RenderProbe { public long Tick; public int Other; public float DeltaS, DeltaD; public bool Valid; public RiderMode OwnMode, OtherMode; }

        public MultiplayerSession(IRealtimeTransport transport, IWireCodec codec, IMonotonicClock clock,
            IResumeReceiptStore resumeStore, IProfileCredentialStore credentialStore = null)
        {
            this.transport = transport ?? throw new ArgumentNullException(nameof(transport)); this.codec = codec ?? throw new ArgumentNullException(nameof(codec));
            this.clock = clock ?? throw new ArgumentNullException(nameof(clock)); this.resumeStore = resumeStore; credentials = credentialStore;
            transport.Opened += OnOpened; transport.Message += OnMessage; transport.Closed += OnClosed;
        }
        public void Connect(string endpoint, LocalPlayerProfile profile, bool newGuest = false)
        {
            ThrowDisposed();
            if (!Uri.TryCreate(endpoint, UriKind.Absolute, out var uri) || (uri.Scheme != "ws" && uri.Scheme != "wss") || !string.IsNullOrEmpty(uri.UserInfo) || !string.IsNullOrEmpty(uri.Fragment))
                throw new ArgumentException("Cần địa chỉ ws:// hoặc wss:// hợp lệ.", nameof(endpoint));
            if (profile == null || !ValidName(profile.DisplayName, 24)) throw new ArgumentException("Tên người chơi cần 1–24 ký tự, không chứa mã định dạng.");
            CloseTransport(); ClearRace(); Room = null; Result = null; PlayerId = ""; sessionEpoch = 0; reliableSequence = 0;
            this.endpoint = uri.AbsoluteUri; this.profile = profile; freshGuest = newGuest; Error = "";
            receipt = newGuest ? null : resumeStore?.Load(this.endpoint); credential = newGuest ? null : credentials?.Load(this.endpoint);
            if (newGuest) resumeStore?.Clear(this.endpoint);
            helloNonce = Guid.NewGuid().ToString("N"); reconnectAttempt = 0; IsSuspended = false; IsReconnecting = false;
            rtt = jitter = 0; lastServiceStamp = -1; BeginConnection();
        }
        public void CreateLobby(LobbyOptions options)
        {
            if (options == null || !ValidName(options.Name, 40) || options.BotCount < 0 || options.BotCount > 6) throw new ArgumentException("Tên phòng hoặc số đối thủ không hợp lệ.");
            if (!CampaignCatalog.IsPlayableRoute(options.CourseIndex) || options.LevelIndex < 0 || options.LevelIndex >= CampaignCatalog.LevelCount)
                throw new ArgumentException("Chặng đua chưa mở hoặc cấp không hợp lệ.");
            SendCommand(new MpCreateRoom { name = options.Name.Trim(), botCount = options.BotCount,
                publicRoom = options.PublicRoom, courseIndex = options.CourseIndex, levelIndex = options.LevelIndex });
        }
        public void CreateLobby(string name, int botCount = 5) => CreateLobby(new LobbyOptions(name, botCount));
        public void JoinLobby(string code)
        {
            code = (code ?? "").Trim().ToUpperInvariant();
            if (code.Length < 4 || code.Length > 16) throw new ArgumentException("Mã phòng không hợp lệ.");
            foreach (char c in code) if (!char.IsLetterOrDigit(c)) throw new ArgumentException("Mã phòng không hợp lệ.");
            SendCommand(new MpJoinRoom { code = code });
        }
        public void SetReady(bool ready) { NeedRoom(); SendCommand(new MpSetReady { roomId = Room.RoomId, ready = ready }); }
        public void StartRace() { NeedRoom(); SendCommand(new MpStartRace { roomId = Room.RoomId }); }
        public void LeaveLobby() { NeedRoom(); leaveRequest = SendCommand(new MpLeaveRoom { roomId = Room.RoomId }); }
        public void ReturnToLobby() { NeedRoom(); SendCommand(new MpReturnToLobby { roomId = Room.RoomId }); }
        public void BackToLobby() => ReturnToLobby();
        public void RequestLobbyList() => SendCommand(new MpListRooms());

        public void Step(float throttle, float brake, float steer, int attackSide = 0, bool kick = false)
        {
            if (disposed || Status != SessionStatus.Connected || IsSuspended || IsDisconnecting || leaveRequest != 0 || !hasCheckpoint || ResultsPending ||
                GameplayRules.IsTerminal(authoritative.Data.Mode) || Room == null ||
                (Room.Phase != LobbyPhase.Racing && Room.Phase != LobbyPhase.Countdown)) return;
            if (!Finite(throttle) || !Finite(brake) || !Finite(steer)) return;
            if (EstimatedServiceTick + InputLeadTicks < Room.StartServiceTick) return;
            if (pending.Count >= 120 || sequence == int.MaxValue || clock.NowSeconds - lastSnapshotAt > 2) { ScheduleReconnect("Mất xác nhận từ máy chủ."); return; }
            long timelineNow = (long)Math.Floor(EstimatedServiceTick - Room.StartServiceTick) + 1;
            // "Still in the future" is insufficient: delivery also needs one-way transit, jitter and owner-queue margin.
            // Keep contiguous buffered ticks only while they remain beyond this arrival floor.
            long arrivalFloor = Math.Max(1, timelineNow + InputLeadTicks);
            long target = Math.Max(Math.Max(authoritative.Tick + 1, lastTargetTick + 1), arrivalFloor);
            // A20Hz Update may submit three samples together. Permit that bounded batch instead of a fixed+2-tick ceiling.
            long futureCeiling = Math.Max(1, timelineNow + MultiplayerProtocol.FutureInputTicks - 1);
            if (target > futureCeiling) return;
            if (target - authoritative.Tick > 120) { ScheduleReconnect("Dòng thời gian cần đồng bộ lại."); return; }
            var input = new RaceInput(Quantize(throttle, 0, 1), Quantize(brake, 0, 1), Quantize(steer, -1, 1), attackSide, kick);
            var frame = new InputFrame(target, ++sequence, input); pending.Add(frame); lastTargetTick = target;
            transport.Send(codec.Encode(new MpInput { sessionEpoch = sessionEpoch, roomId = Room.RoomId, raceEpoch = raceEpoch,
                sequence = sequence, targetTick = target, reliableAck = reliableSequence, throttlePermille = input.ThrottlePermille,
                brakePermille = input.BrakePermille, steerPermille = input.SteerPermille, attackSide = input.AttackSide, kick = input.Kick }));
            ReplayPrediction();
        }
        private void ReplayPrediction()
        {
            if (!hasCheckpoint || predictor == null) return;
            predictor.Restore(authoritative); long target = pending.Count == 0 ? authoritative.Tick : pending[pending.Count - 1].Tick;
            predictedHistory[(int)(authoritative.Tick % predictedHistory.Length)] = authoritative;
            if (target - authoritative.Tick > 120) throw new InvalidOperationException("Prediction history exceeded its bound.");
            int index = 0; RaceInput analog = heldAnalog; long appliedTick = lastAppliedInputTick;
            for (long tick = authoritative.Tick + 1; tick <= target; tick++)
            {
                RaceInput input;
                if (index < pending.Count && pending[index].Tick == tick)
                { input = pending[index++].Input; analog = new RaceInput(input.ThrottlePermille, input.BrakePermille, input.SteerPermille); appliedTick = tick; }
                else input = appliedTick >= 0 && tick - appliedTick <= MultiplayerProtocol.AnalogHoldTicks ? analog : default;
                predictedHistory[(int)(tick % predictedHistory.Length)] = predictor.Advance(tick, input);
            }
            var own = RemoteMotionSampler.Find(LatestAuthoritativeWorld.Riders, RiderId);
            predictedRider = RemoteMotionSampler.WithMotion(own, predictor.Checkpoint); LocalRider = predictedRider;
        }
        public RaceWorldReadModel SamplePresentation()
        {
            if (!hasCheckpoint || LatestAuthoritativeWorld == null) return null;
            bool started = Room != null && EstimatedServiceTick >= Room.StartServiceTick;
            bool beyondProxyHorizon = predictor != null && predictor.Checkpoint.Tick - authoritative.Tick > PredictionNeighbors.MaximumAgeTicks;
            PresentationFrozen = Status == SessionStatus.Connected && !ResultsPending && started && beyondProxyHorizon;
            if (PresentationFrozen && cachedPresentation != null)
            { LocalRider = RemoteMotionSampler.Find(cachedPresentation.Riders, RiderId); return cachedPresentation; }
            bool predict = PredictionEnabled && started && predictor != null;
            long sampleTick = predict ? predictor.Checkpoint.Tick : authoritative.Tick;
            float remaining = Math.Max(0, 1 - (float)((clock.NowSeconds - correctionAt) / .12));
            long smoothingFrame = remaining > 0 && (correctionS != 0 || correctionD != 0) ? (long)(clock.NowSeconds * 60) : 0;
            if (cachedPresentation != null && cachedSampleTick == sampleTick && cachedSnapshotRevision == snapshotRevision &&
                cachedEventRevision == eventRevision && cachedPrediction == predict && cachedSmoothingFrame == smoothingFrame) return cachedPresentation;
            var localPose = predictedRider;
            if (predict)
            {
                // A confirmed local discontinuity may precede its20Hz checkpoint (for example a simultaneous fatal melee hit).
                // Hold the already-computed pose at that tick instead of tearing local/remote presentation apart.
                long cap = sampleTick;
                foreach (var e in events)
                {
                    if (e.Tick <= authoritative.Tick || e.Tick >= cap) continue;
                    bool affected = e.Kind == RaceEventKind.Busted ? e.TargetId == RiderId : e.SourceId == RiderId;
                    bool unreflected = ((e.Kind == RaceEventKind.Crash || e.Kind == RaceEventKind.Wrecked || e.Kind == RaceEventKind.Busted) && GameplayRules.CanDrive(predictedRider.Mode)) ||
                        (e.Kind == RaceEventKind.Landed && predictedRider.Mode == RiderMode.Airborne);
                    if (affected && unreflected) cap = e.Tick;
                }
                var saved = predictedHistory[(int)(cap % predictedHistory.Length)];
                if (cap < sampleTick && saved.Tick == cap && saved.Data.Id == RiderId)
                    localPose = RemoteMotionSampler.WithMotion(RemoteMotionSampler.Find(LatestAuthoritativeWorld.Riders, RiderId), saved);
            }
            LocalRider = predict ? RemoteMotionSampler.Offset(localPose, correctionS * remaining, correctionD * remaining) :
                RemoteMotionSampler.Find(LatestAuthoritativeWorld.Riders, RiderId);
            var visibleEvents = new List<RaceEventReadModel>(events.Count);
            foreach (var item in events) if (item.Tick <= sampleTick) visibleEvents.Add(item);
            var sampled = remotes.Sample(sampleTick, LocalRider, visibleEvents.ToArray(), predict ? predictor : null);
            if (sampled != null) RecordRenderProbe(sampled, sampleTick);
            cachedPresentation = sampled; cachedSampleTick = sampleTick; cachedSnapshotRevision = snapshotRevision; cachedEventRevision = eventRevision;
            cachedPrediction = predict; cachedSmoothingFrame = smoothingFrame;
            return sampled;
        }
        private void RecordRenderProbe(RaceWorldReadModel world, long tick)
        {
            RaceRiderReadModel closest = default; float minimum = 10;
            foreach (var rider in world.Riders)
            {
                if (rider.Id == RiderId) continue;
                float distance = Math.Abs(rider.LongitudinalMeters - LocalRider.LongitudinalMeters);
                if (distance < minimum) { minimum = distance; closest = rider; }
            }
            if (closest.Id == 0) return;
            probes[(int)(tick % probes.Length)] = new RenderProbe { Valid = true, Tick = tick, Other = closest.Id,
                DeltaS = closest.LongitudinalMeters - LocalRider.LongitudinalMeters, DeltaD = closest.LateralMeters - LocalRider.LateralMeters,
                OwnMode = LocalRider.Mode, OtherMode = closest.Mode };
        }
        private void MeasureRenderResidual(RaceWorldReadModel world)
        {
            var probe = probes[(int)(world.Tick % probes.Length)]; if (!probe.Valid || probe.Tick != world.Tick) return;
            var a = RemoteMotionSampler.Find(world.Riders, RiderId); var b = RemoteMotionSampler.Find(world.Riders, probe.Other);
            if (a.Id == 0 || b.Id == 0) return;
            float s = b.LongitudinalMeters - a.LongitudinalMeters - probe.DeltaS, d = b.LateralMeters - a.LateralMeters - probe.DeltaD;
            NearCombatResidualMeters = (float)Math.Sqrt(s * s + d * d); MaximumNearCombatResidualMeters = Math.Max(MaximumNearCombatResidualMeters, NearCombatResidualMeters);
            NearCombatResidualSamples++;
            bool contact = a.Mode != probe.OwnMode || b.Mode != probe.OtherMode || !GameplayRules.CanDrive(a.Mode) || !GameplayRules.CanDrive(b.Mode) || a.Mode == RiderMode.Hit || b.Mode == RiderMode.Hit;
            foreach (var e in events) if (e.Tick >= world.Tick - 3 && e.Tick <= world.Tick &&
                (e.SourceId == RiderId || e.TargetId == RiderId || e.SourceId == probe.Other || e.TargetId == probe.Other) &&
                (e.Kind == RaceEventKind.Hit || e.Kind == RaceEventKind.Crash || e.Kind == RaceEventKind.Landed)) contact = true;
            if (contact) { ContactResidualSamples++; MaximumContactResidualMeters = Math.Max(MaximumContactResidualMeters, NearCombatResidualMeters); }
            else { SteadyResidualSamples++; MaximumSteadyResidualMeters = Math.Max(MaximumSteadyResidualMeters, NearCombatResidualMeters); }
        }
        public void Poll()
        {
            if (disposed) return; transport.Poll(); double now = clock.NowSeconds;
            if (logoutRequest != 0)
            {
                if (now >= logoutDeadline) { FinishDisconnect(true); Error = "Đã đóng kết nối; máy chủ chưa xác nhận thoát phiên."; Changed?.Invoke(); }
                return;
            }
            if (IsSuspended) return;
            if (waitingWelcome && now - connectAt > 6) { ScheduleReconnect("Kết nối quá thời gian chờ."); return; }
            if (IsReconnecting && !waitingWelcome && now >= reconnectAt) { BeginConnection(); return; }
            if (Status != SessionStatus.Connected) return;
            if (reconnectAttempt > 0 && now - stableSince >= 2 && now - lastReceiveAt < 1) reconnectAttempt = 0;
            if (now - lastReceiveAt > 5) { ScheduleReconnect("Máy chủ không phản hồi."); return; }
            if (now >= nextPingAt)
            {
                pingNonce = Guid.NewGuid().ToString("N"); pingMicros = (long)(now * 1000000); nextPingAt = now + 1;
                transport.Send(codec.Encode(new MpPing { sessionEpoch = sessionEpoch, nonce = pingNonce, clientMicroseconds = pingMicros, reliableAck = reliableSequence }));
            }
        }
        public void NotifyVisibility(bool visible)
        {
            if (disposed || string.IsNullOrEmpty(endpoint)) return;
            if (!visible)
            {
                if (IsSuspended) return;
                if (Status == SessionStatus.Connected && hasCheckpoint && Room != null)
                {
                    long target = Math.Max(lastTargetTick + 1, authoritative.Tick + 1);
                    transport.Send(codec.Encode(new MpInput { sessionEpoch = sessionEpoch, roomId = Room.RoomId, raceEpoch = raceEpoch,
                        sequence = ++sequence, targetTick = target, reliableAck = reliableSequence }));
                }
                IsSuspended = true; IsReconnecting = false; waitingWelcome = false; pending.Clear(); cachedPresentation = null; CloseTransport(); Status = SessionStatus.Offline; Changed?.Invoke();
            }
            else if (IsSuspended)
            {
                IsSuspended = false; reconnectAttempt = 0;
                if (receipt == null || string.IsNullOrEmpty(receipt.ResumeToken)) { Fail("Phiên đã tạm dừng trước khi nhận thông tin kết nối."); return; }
                ScheduleReconnect("Đang khôi phục phiên…"); reconnectAt = clock.NowSeconds;
            }
        }
        public void Disconnect(bool clearLease = true)
        {
            if (disposed) return;
            if (clearLease && Status == SessionStatus.Connected)
            {
                if (logoutRequest != 0) return;
                logoutRequest = SendCommand(new MpGoodbye()); logoutDeadline = clock.NowSeconds + 1; pending.Clear(); Changed?.Invoke(); return;
            }
            FinishDisconnect(clearLease);
        }
        private void FinishDisconnect(bool clearLease)
        {
            CloseTransport(); waitingWelcome = IsSuspended = IsReconnecting = false; Status = SessionStatus.Offline;
            logoutRequest = 0;
            if (clearLease) { if (!string.IsNullOrEmpty(endpoint)) resumeStore?.Clear(endpoint); receipt = null; reliableSequence = 0; }
            ClearRace(); Room = null; Result = null; PlayerId = ""; Error = ""; Changed?.Invoke();
        }
        private void BeginConnection()
        { Status = SessionStatus.Connecting; waitingWelcome = true; connectAt = lastReceiveAt = clock.NowSeconds; Changed?.Invoke(); transport.Connect(endpoint); }
        private void OnOpened()
        {
            if (disposed || !waitingWelcome || IsSuspended) return;
            transport.Send(codec.Encode(new MpHello { requestNonce = helloNonce, displayName = profile.DisplayName.Trim(), freshGuest = freshGuest,
                profileToken = freshGuest ? "" : credential?.ProfileToken ?? "", resumeToken = receipt?.ResumeToken ?? "", lastReliableSequence = reliableSequence }));
        }
        private void OnClosed(string reason)
        {
            if (disposed || closingTransport || IsSuspended) return;
            if (reason != null && reason.IndexOf("session_replaced", StringComparison.Ordinal) >= 0)
            { Fail("Phiên đã được mở ở thẻ khác. Chọn Khách mới để chơi thêm một người."); return; }
            if (logoutRequest != 0) { FinishDisconnect(true); Error = "Máy chủ chưa xác nhận thoát phiên."; Changed?.Invoke(); return; }
            if (Status == SessionStatus.Connected || waitingWelcome) ScheduleReconnect("Kết nối bị gián đoạn.");
        }
        private void ScheduleReconnect(string message)
        {
            if (disposed || IsSuspended) return;
            CloseTransport(); waitingWelcome = false; pending.Clear(); hasCheckpoint = false; predictor = null; remotes.Clear();
            if (++reconnectAttempt > 3) { Fail("Không khôi phục được phiên. Hãy kết nối lại."); return; }
            IsReconnecting = true; Status = SessionStatus.Connecting; Error = message;
            reconnectAt = clock.NowSeconds + .5 * (1 << (reconnectAttempt - 1)); Changed?.Invoke();
        }
        private void CloseTransport() { closingTransport = true; try { transport.Close(); } finally { closingTransport = false; } }
        private void ClearRace(bool preserveRetiredInput = false)
        {
            if (!preserveRetiredInput) retiredInputRange = default;
            pending.Clear(); events.Clear(); remotes.Clear(); Array.Clear(probes, 0, probes.Length);
            Array.Clear(predictedHistory, 0, predictedHistory.Length);
            hasCheckpoint = false; predictor = null; authoritative = default; heldAnalog = default; lastAppliedInputTick = -1;
            sequence = processedSequence = 0; lastTargetTick = 0; RiderId = 0; raceEpoch = 0;
            LatestAuthoritativeWorld = null; latestPredictionSnapshot = null; LocalRider = default; LastCorrectionMeters = 0;
            MaximumCorrectionMeters = 0; PresentationCorrectionRevision = 0;
            ResultsPending = false; SteadyResidualSamples = ContactResidualSamples = 0; MaximumSteadyResidualMeters = MaximumContactResidualMeters = 0;
            PresentationFrozen = false; predictionNeighbors.RiderCount = predictionNeighbors.TrafficCount = predictionNeighbors.PedestrianCount = 0;
            Standings = Array.AsReadOnly(new MultiplayerStandingReadModel[0]);
            predictedRider = default; correctionS = correctionD = 0; cachedPresentation = null; snapshotRevision++; eventRevision++;
            NearCombatResidualSamples = 0; NearCombatResidualMeters = MaximumNearCombatResidualMeters = 0;
        }
        private int SendCommand(MpCommand command)
        {
            ThrowDisposed(); if (Status != SessionStatus.Connected) throw new InvalidOperationException("Chưa kết nối máy chủ.");
            command.sessionEpoch = sessionEpoch; command.requestId = ++requestId; transport.Send(codec.Encode(command)); return command.requestId;
        }
        private void NeedRoom() { if (Room == null) throw new InvalidOperationException("Chưa tham gia phòng."); }
        private void Fail(string message)
        { CloseTransport(); waitingWelcome = IsReconnecting = false; Status = SessionStatus.Failed; Error = message; pending.Clear(); Changed?.Invoke(); }
        public void Dispose()
        {
            if (disposed) return; Disconnect(false); disposed = true;
            transport.Opened -= OnOpened; transport.Message -= OnMessage; transport.Closed -= OnClosed; transport.Dispose();
        }
        private void ThrowDisposed() { if (disposed) throw new ObjectDisposedException(nameof(MultiplayerSession)); }
        private static bool ValidName(string name, int max)
        {
            if (string.IsNullOrWhiteSpace(name) || name.Trim().Length > max) return false;
            foreach (char c in name) if (char.IsControl(c) || c == '<' || c == '>') return false; return true;
        }
        private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static int Quantize(float value, float min, float max) => (int)Math.Round(Math.Max(min, Math.Min(max, value)) * 1000, MidpointRounding.AwayFromZero);
    }
}
