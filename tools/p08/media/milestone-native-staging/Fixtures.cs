using System;
using System.Collections.Generic;
using System.Reflection;
using RacingBois.Client.Adapters;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;

namespace RacingBois.Tools.NativeMilestones
{
    // This adapter resolves only public methods on the actual loaded production Application assembly.
    // It allows preparing the helper before the reviewed milestone type is installed, without linking a duplicate.
    internal sealed class Tracker
    {
        private readonly object instance;
        private readonly Type type;
        public Tracker(CareerSession session)
        {
            type = typeof(CareerSession).Assembly.GetType("RacingBois.Client.Application.CareerMilestoneTracker", true);
            instance = Activator.CreateInstance(type, session);
        }
        private object Call(string name, params object[] args)
        {
            try { return type.GetMethod(name, BindingFlags.Instance | BindingFlags.Public).Invoke(instance, args); }
            catch (TargetInvocationException error) { throw error.InnerException ?? error; }
        }
        public void Reset() => Call("Reset");
        public void CancelCurrent() => Call("CancelCurrent");
        public void OutcomeCompleted(string resultId, bool skipped) => Call("OutcomeCompleted", resultId, skipped);
        public void Observe(string realm, string profile, string player, LobbyReadModel room, MultiplayerResultReadModel result)
            => Call("Observe", realm, profile, player, room, result);
        public bool TryTake(out string id)
        { var args = new object[] { "" }; bool result = (bool)Call("TryTake", args); id = (string)args[0]; return result; }
    }

    internal sealed class Fixture : IDisposable
    {
        public readonly Wire Wire = new Wire(); public readonly Store Store = new Store();
        public readonly CareerSession Session; public readonly Tracker Tracker;
        public readonly int Level, Mask; public string Match => "realm-a/7"; public MultiplayerResultReadModel Result;
        public int Reward => EconomyRules.RewardForRank(1, Level);
        private readonly WirePeer peer;
        public Fixture(int level = 0, int mask = 30)
        {
            NativeMilestoneContracts.OwnedFixtures.Add(this);
            Level = level; Mask = mask; const string endpoint = "wss://example.invalid/multiplayer";
            Store.Save(endpoint, new ProfileCredential("synthetic-capability", "profile-a", "Rider", "realm-a", 1000));
            Session = new CareerSession(Wire, Store, Store); Session.SetEndpoint(endpoint); Session.Refresh(); Wire.Complete(Before());
            peer = new WirePeer(this);
            Tracker = new Tracker(Session); Tracker.Observe("realm-a", "profile-a", "session-a", Room(LobbyPhase.Racing), null);
        }
        public MpLobby LobbyMessage(LobbyPhase phase) => new MpLobby { roomId = "room-a", code = "AAAAAA", name = "Synthetic room",
            hostSessionId = "session-a", matchId = Match, state = (int)phase, revision = 1, raceEpoch = 1, botCount = 0, maxPlayers = 8,
            startServiceTick = 0, serverServiceTick = 0, publicRoom = false, courseIndex = 0, levelIndex = Level,
            members = new[] { new MpMember { sessionId = "session-a", displayName = "Rider", riderId = 1, ready = true, connected = true, guest = false } } };
        public LobbyReadModel Room(LobbyPhase phase) => peer.Room(phase);
        public CareerResponse Before() => new CareerResponse { ok = true, profile = new CareerProfileData { realmId = "realm-a", realmKind = "offline", profileId = "profile-a", displayName = "Rider",
            selectedBikeId = BikeCatalog.StarterBikeId, selectedCharacterId = CharacterCatalog.GetAt(0).Id, credits = 1000, levelIndex = Level, qualificationMask = Mask, revision = 10,
            bikes = new[] { new CareerBikeData { bikeId = BikeCatalog.StarterBikeId, condition = 100 } } }, ledger = Array.Empty<CareerLedgerEntry>() };
        public CareerResponse After()
        {
            var response = Before(); var expected = CampaignRules.ApplyQualification(Level, Mask, false, 0, 1);
            response.profile.levelIndex = expected.LevelIndex; response.profile.qualificationMask = expected.QualificationMask; response.profile.campaignComplete = expected.Completed;
            response.profile.credits = 1000 + Reward; response.profile.revision = 11;
            response.ledger = new[] { new CareerLedgerEntry { transactionId = "match:7", reason = "race_result", bikeId = BikeCatalog.StarterBikeId, delta = Reward, balance = 1000 + Reward } };
            return response;
        }
        public MultiplayerResultReadModel CreateResult(bool persisted = true, RaceOutcome outcome = RaceOutcome.Finished, string resultId = null)
            => peer.Result(persisted, outcome, resultId ?? Match);
        public void Finish(CareerResponse after = null) { Result = CreateResult(); Session.Refresh(); Wire.Complete(after ?? After()); Observe(); }
        public void Observe() => Tracker.Observe("realm-a", "profile-a", "session-a", Room(Result == null ? LobbyPhase.Racing : LobbyPhase.Results), Result);
        public void Dispose() { peer?.Dispose(); Wire.Callback = null; }
    }

    // Immutable result models come from the actual production message handler, never internal constructors/reflection.
    internal sealed class WirePeer : IDisposable
    {
        private readonly Fixture owner;
        private readonly PacketWire wire = new PacketWire();
        private readonly MultiplayerSession session;
        private long sequence;
        private int revision = 1;
        public WirePeer(Fixture fixture)
        {
            owner = fixture;
            session = new MultiplayerSession(wire, wire.Codec, new Clock(), new Store(), new Store());
            session.Connect("wss://fixture.invalid/multiplayer", new LocalPlayerProfile("local-fixture", "Rider", 0));
            if (wire.Hello == null) throw new InvalidOperationException("Production hello not sent");
            wire.Enqueue(new MpWelcome { requestNonce = wire.Hello.requestNonce, sessionId = "session-a", resumeToken = "synthetic-lease",
                profileToken = "synthetic-capability", profileId = "profile-a", displayName = "Rider", realmId = "realm-a", sessionEpoch = 1,
                credits = 1000, reliableSequence = 0, reliableReset = true });
            session.Poll(); Check();
            Room(LobbyPhase.Racing);
        }
        private void Check()
        { if (session.Status != SessionStatus.Connected || session.InvalidSnapshots != 0) throw new InvalidOperationException("Production wire projection failed: " + session.Error); }
        public LobbyReadModel Room(LobbyPhase phase)
        {
            var message = owner.LobbyMessage(phase); message.revision = revision++; message.reliableSequence = ++sequence;
            wire.Enqueue(message); session.Poll(); Check();
            if (session.Room == null) throw new InvalidOperationException("Production lobby projection absent");
            return session.Room;
        }
        public MultiplayerResultReadModel Result(bool persisted, RaceOutcome outcome, string resultId)
        {
            Room(LobbyPhase.Results);
            wire.Enqueue(new MpResult { roomId = "room-a", matchId = owner.Match, resultId = resultId, raceEpoch = 1,
                reliableSequence = ++sequence, persisted = persisted,
                entries = new[] { new MpResultEntry { sessionId = "session-a", displayName = "Rider", riderId = 1, outcome = (int)outcome, rank = 1, reward = owner.Reward, credits = 1000 + owner.Reward, finishTick = 100 } } });
            session.Poll(); Check();
            if (session.Result == null || session.Result.ResultId != resultId) throw new InvalidOperationException("Production result projection absent");
            return session.Result;
        }
        public void Dispose() => session.Dispose();
    }
    internal sealed class Clock : IMonotonicClock { public double NowSeconds => 1; }
    internal sealed class PacketWire : IRealtimeTransport
    {
        public event Action Opened; public event Action<string> Message; public event Action<string> Closed;
        public readonly UnityWireCodec Codec = new UnityWireCodec(); public MpHello Hello;
        private readonly Queue<string> pending = new Queue<string>();
        public void Connect(string endpoint) => Opened?.Invoke();
        public void Send(string text)
        { if (Codec.Decode<MessageEnvelope>(text).kind == "mpHello") Hello = Codec.Decode<MpHello>(text); }
        public void Enqueue(object message) => pending.Enqueue(Codec.Encode(message));
        public void Poll() { while (pending.Count > 0) Message?.Invoke(pending.Dequeue()); }
        public void Close() => Closed?.Invoke("fixture-closed");
        public void Dispose() { pending.Clear(); Opened = null; Message = null; Closed = null; }
    }
    internal sealed class Wire : ICareerTransport
    {
        public CareerRequest Last; public Action<CareerResponse, bool> Callback;
        public void Send(string endpoint, string bearer, CareerRequest request, Action<CareerResponse, bool> completed) { Last = request; Callback = completed; }
        public void Complete(CareerResponse response, bool transient = false) => Callback(response, transient);
    }
    internal sealed class Store : IProfileCredentialStore, IResumeReceiptStore
    {
        private readonly Dictionary<string, ProfileCredential> credentials = new Dictionary<string, ProfileCredential>();
        public ProfileCredential Load(string endpoint) => credentials.TryGetValue(endpoint, out var value) ? value : null;
        public void Save(string endpoint, ProfileCredential value) => credentials[endpoint] = value;
        public void Clear(string endpoint) => credentials.Remove(endpoint);
        ResumeReceipt IResumeReceiptStore.Load(string endpoint) => null;
        void IResumeReceiptStore.Save(string endpoint, ResumeReceipt value) { }
        void IResumeReceiptStore.Clear(string endpoint) { }
    }
}
