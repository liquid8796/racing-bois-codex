using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Protocol;
using RacingBois.Server.Application.Multiplayer;

internal sealed class TestClock : IMonotonicClock { public double NowSeconds { get; set; } }
internal sealed class TestCodec : IWireCodec
{
    internal static readonly JsonSerializerOptions Options = new() { IncludeFields = true };
    public string Encode(object message) => JsonSerializer.Serialize(message, message.GetType(), Options);
    public T Decode<T>(string text) where T : class => JsonSerializer.Deserialize<T>(text, Options);
    public object DecodeClient(string text)
    {
        string kind = Decode<MessageEnvelope>(text).kind;
        return kind switch {
            "mpHello" => Decode<MpHello>(text), "mpCreate" => Decode<MpCreateRoom>(text), "mpJoin" => Decode<MpJoinRoom>(text),
            "mpReady" => Decode<MpSetReady>(text), "mpStart" => Decode<MpStartRace>(text), "mpLeave" => Decode<MpLeaveRoom>(text),
            "mpBack" => Decode<MpReturnToLobby>(text), "mpList" => Decode<MpListRooms>(text), "mpGoodbye" => Decode<MpGoodbye>(text),
            "mpInput" => Decode<MpInput>(text), "mpPing" => Decode<MpPing>(text), "mpAck" => Decode<MpAck>(text),
            _ => throw new InvalidOperationException(kind) };
    }
}
internal sealed class MemoryStore : IResumeReceiptStore, IProfileCredentialStore
{
    public readonly Dictionary<string, ResumeReceipt> Resumes = new();
    public readonly Dictionary<string, ProfileCredential> Profiles = new();
    private static string Key(string key) { if (!Uri.TryCreate(key, UriKind.Absolute, out var uri) || (uri.Scheme != "ws" && uri.Scheme != "wss")) throw new ArgumentException("Endpoint required"); return key; }
    ResumeReceipt IResumeReceiptStore.Load(string key) => Resumes.GetValueOrDefault(Key(key));
    void IResumeReceiptStore.Save(string key, ResumeReceipt value) => Resumes[Key(key)] = value;
    void IResumeReceiptStore.Clear(string key) => Resumes.Remove(Key(key));
    ProfileCredential IProfileCredentialStore.Load(string key) => Profiles.GetValueOrDefault(Key(key));
    void IProfileCredentialStore.Save(string key, ProfileCredential value) => Profiles[Key(key)] = value;
    void IProfileCredentialStore.Clear(string key) => Profiles.Remove(Key(key));
}
internal sealed class TestPeer : IRealtimeTransport
{
    public event Action Opened; public event Action<string> Message; public event Action<string> Closed;
    public readonly TestNetwork Network;
    public readonly MemoryStore Store;
    public MultiplayerSession Session;
    public string Connection = "", LastSnapshot = "";
    public int Connections, InputsSent, InputsReceivedByServer;
    public float Throttle, Steer; public float Brake = 0; public int Attack; public bool Kick = false;
    public readonly List<string> Trace = new();
    private readonly Queue<Action> incoming = new();
    public double BlockUplinkUntil;
    internal TestPeer(TestNetwork network, MemoryStore store)
    { Network = network; Store = store; Session = new MultiplayerSession(this, network.Codec, network.Clock, store, store); }
    public void Connect(string endpoint)
    { Connection = Guid.NewGuid().ToString("N"); Connections++; Network.PeersByConnection[Connection] = this; Opened?.Invoke(); }
    public void Send(string text)
    {
        string connection = Connection; if (connection == "") return;
        bool input = Network.Codec.Decode<MessageEnvelope>(text).kind == "mpInput"; if (input) InputsSent++;
        Network.Schedule(connection + "up", Math.Max(Network.Clock.NowSeconds + Network.TransitDelay(), BlockUplinkUntil), () =>
        { if (Connection != connection) return; Network.Server.Handle(connection, Network.Codec.DecodeClient(text)); Network.PumpStorage(); if (input) InputsReceivedByServer++; });
    }
    public void Close()
    { if (Connection == "") return; string old = Connection; Connection = ""; Network.Server.Disconnect(old); }
    public void Drop() { Close(); Closed?.Invoke("synthetic_drop"); }
    public void Poll() { while (incoming.Count > 0) incoming.Dequeue()(); }
    public void Dispose() { Close(); }
    public void Deliver(string connection, string text)
    {
        if (Connection != connection) return;
        incoming.Enqueue(() => DeliverOnPoll(connection, text));
    }
    private void DeliverOnPoll(string connection, string text)
    {
        if (Connection != connection) return;
        if (Network.Codec.Decode<MessageEnvelope>(text).kind == "mpSnapshot") LastSnapshot = text;
        using var document = JsonDocument.Parse(text);
        string kind = Network.Codec.Decode<MessageEnvelope>(text).kind;
        if (kind != "mpSnapshot" && kind != "mpPong") Trace.Add("recv:" + kind + ":" + (document.RootElement.TryGetProperty("reliableSequence", out var seq) ? seq.ToString() : "-") + " at" + Network.Server.ServiceTick);
        Message?.Invoke(text);
        if (Session.IsReconnecting || Session.Status == SessionStatus.Failed) Trace.Add("state:" + Session.Status + ":" + Session.Error);
    }
    public void Inject(object message) => Message?.Invoke(Network.Codec.Encode(message));
    public void ServerClose(string connection, string reason) { incoming.Enqueue(() => { if (Connection == connection) { Close(); Closed?.Invoke(reason); } }); }
}
internal sealed class TestNetwork : IMultiplayerSink
{
    private sealed class Delivery { internal double At; internal long Order; internal Action Apply; }
    private readonly List<Delivery> deliveries = new();
    private readonly Dictionary<string, double> fifo = new();
    private long order; private int half;
    public readonly TestClock Clock = new(); public readonly TestCodec Codec = new();
    public readonly RealmStore Realm; public readonly MultiplayerService Server;
    public readonly List<TestPeer> Peers = new(); public readonly Dictionary<string, TestPeer> PeersByConnection = new();
    public double OneWayDelay, JitterSeconds; public int DropWelcomes;
    private readonly Random delayRandom = new Random(1996);
    public double ClientFrameSeconds = 1.0 / 120, BlockClientUntil;
    private double nextClientFrame, lastClientFrame, accumulated;
    public Action<TestPeer> InputController;
    public TestNetwork(double rttMilliseconds = 0)
    {
        OneWayDelay = rttMilliseconds / 2000;
        Realm = new RealmStore(Path.Combine("_local", "p05-client-tests", Guid.NewGuid().ToString("N")));
        Server = new MultiplayerService(Realm, this, message => Encoding.UTF8.GetBytes(Codec.Encode(message)));
    }
    public TestPeer Add(string name, bool guest = true, MemoryStore store = null)
    {
        var peer = new TestPeer(this, store ?? new MemoryStore()); Peers.Add(peer);
        peer.Session.Connect("ws://127.0.0.1:7777/multiplayer", new LocalPlayerProfile(Guid.NewGuid().ToString("N"), name, 0), guest);
        return peer;
    }
    public void Schedule(string stream, double at, Action action)
    {
        at = Math.Max(at, fifo.GetValueOrDefault(stream)); fifo[stream] = at;
        deliveries.Add(new Delivery { At = at, Order = order++, Apply = action });
    }
    public double TransitDelay() => Math.Max(0, OneWayDelay + (delayRandom.NextDouble() * 2 - 1) * JitterSeconds);
    private void Drain()
    {
        while (true)
        {
            Delivery item = deliveries.Where(d => d.At <= Clock.NowSeconds + 1e-9).OrderBy(d => d.At).ThenBy(d => d.Order).FirstOrDefault();
            if (item == null) return; deliveries.Remove(item); item.Apply();
        }
    }
    public void Run(int ticks, bool inputs = true)
    {
        for (int i = 0; i < ticks * 2; i++)
        {
            Clock.NowSeconds += 1.0 / 120; Drain();
            if (++half % 2 == 0) { Server.Step(); PumpStorage(); }
            if (Clock.NowSeconds + 1e-9 >= nextClientFrame && Clock.NowSeconds >= BlockClientUntil)
            {
                accumulated += Math.Min(.1, Clock.NowSeconds - lastClientFrame); lastClientFrame = Clock.NowSeconds;
                nextClientFrame = Clock.NowSeconds + ClientFrameSeconds;
                foreach (var peer in Peers.ToArray()) peer.Session.Poll();
                int steps = 0;
                while (accumulated + 1e-9 >= 1.0 / 60 && steps++ < 6)
                {
                    accumulated -= 1.0 / 60;
                    if (inputs) foreach (var peer in Peers.ToArray()) { InputController?.Invoke(peer); peer.Session.Step(peer.Throttle, peer.Brake, peer.Steer, peer.Attack, peer.Kick); }
                }
                foreach (var peer in Peers.ToArray()) peer.Session.SamplePresentation();
            }
            Drain();
        }
    }
    public bool Send(string connectionId, byte[] bytes, bool reliable)
    {
        if (!PeersByConnection.TryGetValue(connectionId, out var peer)) return false;
        string text = Encoding.UTF8.GetString(bytes);
        if (DropWelcomes > 0 && Codec.Decode<MessageEnvelope>(text).kind == "mpWelcome") { DropWelcomes--; return true; }
        Schedule(connectionId + "down", Clock.NowSeconds + TransitDelay(), () => peer.Deliver(connectionId, text)); return true;
    }
    public void PumpStorage()
    {
        int attempts = 0;
        while (Server.PendingStorageCount > 0)
        {
            Server.PollPersistence();
            if (++attempts > 3000) throw new InvalidOperationException("Synthetic test persistence did not drain");
            if (Server.PendingStorageCount > 0) System.Threading.Thread.Sleep(1);
        }
    }
    public void Close(string connectionId, string reason)
    {
        if (!PeersByConnection.TryGetValue(connectionId, out var peer)) return;
        Schedule(connectionId + "down", Clock.NowSeconds + OneWayDelay, () => peer.ServerClose(connectionId, reason));
    }
    public void PrepareRace(params TestPeer[] peers)
    {
        Run(45); peers[0].Session.CreateLobby("Client test", 0); Run(45);
        for (int i = 1; i < peers.Length; i++) { peers[i].Session.JoinLobby(peers[0].Session.Room.Code); Run(30); }
        foreach (var peer in peers) peer.Session.SetReady(true); Run(45);
        peers[0].Session.StartRace(); Run(240);
        if (peers[0].Session.Room?.Phase != LobbyPhase.Racing) throw new InvalidOperationException("Prepare failed phase=" + peers[0].Session.Room?.Phase + " status=" + peers[0].Session.Status + " error=" + peers[0].Session.Error + " tick=" + ServiceTickText() + " trace=" + string.Join("|",peers[0].Trace.TakeLast(24)));
    }
    private string ServiceTickText() => Server.ServiceTick + "/" + string.Join(",", Peers.Select(p => p.Session.Room == null ? "none" : string.Join(";", p.Session.Room.Members.Select(m => m.Ready + "/" + m.Connected))));
}
