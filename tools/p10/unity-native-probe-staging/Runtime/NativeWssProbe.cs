using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using RacingBois.Client.Application;
using RacingBois.Client.Adapters;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;
using UnityEngine;
using App = UnityEngine.Application;

namespace RacingBois.Diagnostics.NativeProbe
{
    /// <summary>Opt-in native transport acceptance specimen. No renderer/content/gameplay substitution.</summary>
    public sealed class NativeWssProbe : MonoBehaviour
    {
        private enum Stage { Disabled, Connecting, Creating, Starting, Driving, Suspended, Resuming, Leaving, Disconnecting, Done }
        [Serializable] private sealed class Binding { public string sourceFingerprint = "", backend = "", unityVersion = ""; public int protocolVersion = 0; }
        [Serializable] private sealed class Sample
        { public double elapsed, rttMs; public string stage, session, phase, mode; public long authorityTick; public int pending; public float distance, correction; }
        [Serializable] private sealed class Report
        {
            public int schema = 1, protocolVersion, openedConnections, acceptedWelcomes, authoritativeSamples, postResumeSamples, maximumPending, invalidSnapshots, completedRaces;
            public string runId, status = "RUNNING", errorCode = "", startedUtc, finishedUtc, endpoint, unityVersion, platform, backend, sourceFingerprint, bindingSha256, lastTransportCode;
            public bool guestOnly, privateRoom, resumedWelcome, resumeIdentityPreserved, resumeSlotPreserved, resumeRoomPreserved, ownedRoomLeaveAcknowledged, logoutAcknowledged, monoDetected;
            public double elapsedSeconds, maximumRttMs; public float maximumDistanceMeters, maximumCorrectionMeters;
            public Sample[] samples;
            public string scope = "Actual Unity Windows Mono player with production native BrowserSocketTransport, MultiplayerSession, UnityWireCodec and UnityMonotonicClock. Private guest room, real authoritative progress and planned suspend/resume. No game rendering, assets, full multiplayer quality, performance or release acceptance.";
        }
        private NativeProbeConfiguration configuration; private Report report; private Stage stage;
        private BrowserSocketTransport transport; private MultiplayerSession session; private UnityWireCodec codec; private UnityMonotonicClock clock;
        private NativeProbeMemoryStore store; private readonly Queue<Sample> samples = new Queue<Sample>();
        private double began, deadline, raceBegan = -1, nextInput, nextReport, suspendUntil; private long observedTick = -1;
        private bool readySent, startSent, resumeAttempted, finished, active, requestedSuccess;
        private string identity, roomIdentity; private int riderIdentity, resumeRaceEpoch;

        private void Awake()
        {
            try
            {
                configuration = NativeProbeConfiguration.Parse(Environment.GetCommandLineArgs());
                if (!configuration.Enabled) { stage = Stage.Disabled; enabled = false; return; }
                if (File.Exists(configuration.ReportPath)) throw new IOException("report_already_exists");
                string bindingPath = Path.GetFullPath(Path.Combine(App.dataPath, "..", "NativeProbe.binding.json"));
                var binding = JsonUtility.FromJson<Binding>(File.ReadAllText(bindingPath));
                if (binding == null || binding.sourceFingerprint != configuration.ExpectedFingerprint || binding.backend != "Mono2x" || binding.protocolVersion != MultiplayerProtocol.Version)
                    throw new InvalidOperationException("build_binding_mismatch");
                clock = new UnityMonotonicClock(); codec = new UnityWireCodec(); store = new NativeProbeMemoryStore(); began = clock.NowSeconds;
                report = new Report { runId = Guid.NewGuid().ToString("N"), startedUtc = DateTime.UtcNow.ToString("O"), endpoint = configuration.Endpoint,
                    unityVersion = App.unityVersion, platform = App.platform.ToString(), backend = binding.backend, sourceFingerprint = binding.sourceFingerprint,
                    bindingSha256 = Digest(bindingPath), protocolVersion = MultiplayerProtocol.Version, monoDetected = Type.GetType("Mono.Runtime") != null };
                Directory.CreateDirectory(Path.GetDirectoryName(configuration.ReportPath));
                using (var reservation = new FileStream(configuration.ReportPath, FileMode.CreateNew, FileAccess.Write, FileShare.Read)) { }
                active = true; App.runInBackground = true; App.targetFrameRate = 60;
                if (App.isEditor || App.platform != RuntimePlatform.WindowsPlayer || !report.monoDetected) { Finish(false, "native_windows_mono_required"); return; }
                transport = gameObject.AddComponent<BrowserSocketTransport>();
                session = new MultiplayerSession(transport, codec, clock, store, store);
                // Subscribe after the production session, so the observer sees committed state.
                transport.Opened += () => report.openedConnections++;
                transport.Message += ObserveMessage;
                transport.Closed += reason => report.lastTransportCode = KnownTransportCode(reason);
                SetStage(Stage.Connecting, 20);
                session.Connect(configuration.Endpoint, new LocalPlayerProfile(Guid.NewGuid().ToString("N"), "Mono probe " + report.runId.Substring(0, 6), 0), true);
                WriteReport();
            }
            catch (Exception error)
            {
                if (active && report != null) Finish(false, error.GetType().Name);
                else { Debug.LogError("RB_NATIVE_PROBE_SETUP_FAILED " + error.GetType().Name); App.Quit(2); }
            }
        }
        private void Update()
        {
            if (!active || finished) return;
            try
            {
                session.Poll(); double now = clock.NowSeconds;
                if (session.InvalidSnapshots != 0) { BeginCleanup(false, "invalid_snapshot"); return; }
                if (session.Status == SessionStatus.Failed) { BeginCleanup(false, "session_failed"); return; }
                ObserveProgress();
                if (now >= nextReport) { nextReport = now + 1; AddSample(); WriteReport(); }
                if (now > deadline && stage != Stage.Driving) { BeginCleanup(false, "timeout_" + stage); return; }
                switch (stage)
                {
                    case Stage.Connecting:
                        if (session.Status != SessionStatus.Connected) break;
                        report.guestOnly = session.IsGuest;
                        if (!report.guestOnly) { BeginCleanup(false, "unexpected_non_guest"); break; }
                        session.CreateLobby(new LobbyOptions("Native WSS probe " + report.runId.Substring(0, 6), 0, publicRoom: false)); SetStage(Stage.Creating, 15); break;
                    case Stage.Creating:
                        if (session.Room == null) break;
                        roomIdentity = session.Room.RoomId;
                        report.privateRoom = !session.Room.PublicRoom && session.IsHost && session.Room.Members.Count == 1;
                        if (!report.privateRoom) { BeginCleanup(false, "private_room_contract"); break; }
                        readySent = startSent = false; SetStage(Stage.Starting, 15); break;
                    case Stage.Starting:
                        if (session.Room == null) { BeginCleanup(false, "owned_room_missing"); break; }
                        if (!readySent && session.Room.Phase == LobbyPhase.Lobby) { session.SetReady(true); readySent = true; }
                        if (!startSent && session.Room.Phase == LobbyPhase.Lobby && session.Room.Members.All(member => member.Ready)) { session.StartRace(); startSent = true; }
                        if (session.Room.Phase == LobbyPhase.Racing) { if (raceBegan < 0) raceBegan = now; nextInput = now; SetStage(Stage.Driving, configuration.Seconds + 30); }
                        break;
                    case Stage.Driving:
                        Drive(now);
                        if (!resumeAttempted && now - raceBegan >= 15 && session.Room != null && session.Room.Phase == LobbyPhase.Racing)
                        {
                            resumeAttempted = true; identity = session.PlayerId; riderIdentity = session.RiderId; resumeRaceEpoch = session.Room.RaceEpoch;
                            session.NotifyVisibility(false); suspendUntil = now + 1; SetStage(Stage.Suspended, 3); break;
                        }
                        if (now - raceBegan >= configuration.Seconds)
                        {
                            bool passed = report.guestOnly && report.privateRoom && report.resumedWelcome && report.resumeIdentityPreserved && report.resumeSlotPreserved && report.resumeRoomPreserved &&
                                report.openedConnections >= 2 && report.authoritativeSamples >= 30 && report.postResumeSamples >= 20 && report.maximumDistanceMeters >= 20 && report.invalidSnapshots == 0;
                            BeginCleanup(passed, passed ? "" : "missing_runtime_evidence"); break;
                        }
                        if (session.Room != null && session.Room.Phase == LobbyPhase.Results && session.Result != null)
                        { report.completedRaces++; session.ReturnToLobby(); readySent = startSent = false; SetStage(Stage.Starting, 15); }
                        break;
                    case Stage.Suspended:
                        if (now >= suspendUntil) { session.NotifyVisibility(true); SetStage(Stage.Resuming, 20); } break;
                    case Stage.Resuming:
                        if (session.Status != SessionStatus.Connected || session.IsReconnecting || session.Room == null || session.RiderId == 0) break;
                        report.resumeIdentityPreserved = session.PlayerId == identity; report.resumeSlotPreserved = session.RiderId == riderIdentity;
                        report.resumeRoomPreserved = session.Room.RoomId == roomIdentity && session.Room.RaceEpoch == resumeRaceEpoch;
                        if (!(report.resumeIdentityPreserved && report.resumeSlotPreserved && report.resumeRoomPreserved && report.resumedWelcome)) { BeginCleanup(false, "resume_identity_or_room_changed"); break; }
                        observedTick = -1; nextInput = now; SetStage(Stage.Driving, configuration.Seconds + 30); break;
                    case Stage.Leaving:
                        if (session.Room == null) { session.Disconnect(); SetStage(Stage.Disconnecting, 5); } break;
                    case Stage.Disconnecting:
                        if (session.Status == SessionStatus.Offline) Finish(requestedSuccess && report.ownedRoomLeaveAcknowledged && report.logoutAcknowledged,
                            report.errorCode.Length != 0 ? report.errorCode : report.ownedRoomLeaveAcknowledged && report.logoutAcknowledged ? "" : "cleanup_not_acknowledged");
                        break;
                }
            }
            catch (Exception error) { BeginCleanup(false, error.GetType().Name); }
        }
        private void Drive(double now)
        {
            int catchup = 0;
            while (now >= nextInput && catchup++ < 4)
            {
                nextInput += 1d / 60; var rider = session.LocalRider;
                var track = TrackDefinition.ForCourse(session.Room == null ? 0 : session.Room.CourseIndex, session.Room == null ? 0 : session.Room.LevelIndex);
                float lane = session.RiderId % 2 == 0 ? 1.8f : -1.8f, speed = rider.SpeedMetersPerSecond * 1000;
                float lateral = Mathf.Clamp((lane-rider.LateralMeters)*2000, -6500, 6500);
                float steer = Mathf.Clamp((lateral+speed*track.CurvatureAt((long)(rider.LongitudinalMeters*1000))/100000)/(1200+speed/6), -1, 1);
                session.Step(1, 0, steer); session.SamplePresentation();
            }
            if (now-nextInput > .15) nextInput = now;
        }
        private void ObserveProgress()
        {
            report.maximumRttMs = Math.Max(report.maximumRttMs, session.RttMs); report.maximumPending = Math.Max(report.maximumPending, session.PendingInputCount);
            report.maximumCorrectionMeters = Math.Max(report.maximumCorrectionMeters, session.MaximumCorrectionMeters); report.invalidSnapshots = session.InvalidSnapshots;
            if (session.Room == null || session.Room.Phase != LobbyPhase.Racing || session.LastResolvedTick == observedTick) return;
            observedTick = session.LastResolvedTick; report.authoritativeSamples++;
            if (resumeAttempted && report.resumeRoomPreserved) report.postResumeSamples++;
            if (session.LatestAuthoritativeWorld != null)
                foreach (var rider in session.LatestAuthoritativeWorld.Riders) if (rider.Id == session.RiderId) report.maximumDistanceMeters = Math.Max(report.maximumDistanceMeters, rider.LongitudinalMeters);
        }
        private void ObserveMessage(string text)
        {
            try
            {
                var envelope = codec.Decode<MessageEnvelope>(text);
                if (envelope.kind == "mpWelcome")
                {
                    var welcome = codec.Decode<MpWelcome>(text);
                    if (session.Status == SessionStatus.Connected && welcome.sessionId == session.PlayerId)
                    { report.acceptedWelcomes++; if (resumeAttempted && welcome.resumed) report.resumedWelcome = true; }
                }
                if (stage == Stage.Leaving && session.Status == SessionStatus.Connected && session.Room == null && (envelope.kind == "mpAccepted" || envelope.kind == "mpLobby")) report.ownedRoomLeaveAcknowledged = true;
                if (stage == Stage.Disconnecting && envelope.kind == "mpAccepted" && session.Status == SessionStatus.Offline && string.IsNullOrEmpty(session.Error)) report.logoutAcknowledged = true;
            }
            catch (Exception) { report.errorCode = "observer_decode_failed"; }
        }
        private void BeginCleanup(bool success, string code)
        {
            if (finished) return;
            if (code.Length != 0 && report.errorCode.Length == 0) report.errorCode = code;
            if (stage == Stage.Leaving || stage == Stage.Disconnecting) { Finish(false, report.errorCode.Length == 0 ? "cleanup_timeout" : report.errorCode); return; }
            requestedSuccess = success;
            if (session != null && session.Status == SessionStatus.Connected && session.Room != null && session.Room.RoomId == roomIdentity)
            { session.LeaveLobby(); SetStage(Stage.Leaving, 10); return; }
            if (session != null && session.Status == SessionStatus.Connected && session.Room == null)
            { session.Disconnect(); SetStage(Stage.Disconnecting, 10); return; }
            Finish(false, report.errorCode.Length == 0 ? "cleanup_unavailable" : report.errorCode);
        }
        private void Finish(bool success, string code)
        {
            if (finished) return; finished = true; stage = Stage.Done;
            report.status = success && report.errorCode.Length == 0 ? "PASS" : "FAIL"; if (code.Length != 0) report.errorCode = code;
            report.finishedUtc = DateTime.UtcNow.ToString("O");
            session?.Dispose(); transport?.Dispose(); store?.Clear();
            WriteReport(); Debug.Log("RB_NATIVE_WSS_PROBE_" + report.status + " " + report.errorCode); App.Quit(report.status == "PASS" ? 0 : 1);
        }
        private void SetStage(Stage value, double seconds) { stage = value; deadline = clock.NowSeconds + seconds; }
        private void AddSample()
        {
            while (samples.Count >= 256) samples.Dequeue(); samples.Enqueue(new Sample { elapsed = clock.NowSeconds-began, stage = stage.ToString(), session = session.Status.ToString(),
                phase = session.Room == null ? "none" : session.Room.Phase.ToString(), mode = session.LocalRider.Mode.ToString(), authorityTick = session.LastResolvedTick,
                pending = session.PendingInputCount, rttMs = session.RttMs, distance = session.LocalRider.LongitudinalMeters, correction = session.LastCorrectionMeters });
        }
        private void WriteReport()
        {
            if (report == null || configuration == null) return; report.elapsedSeconds = clock.NowSeconds-began; report.samples = samples.ToArray();
            string temp = configuration.ReportPath + ".tmp"; File.WriteAllText(temp, JsonUtility.ToJson(report, true));
            if (File.Exists(configuration.ReportPath)) File.Replace(temp, configuration.ReportPath, null); else File.Move(temp, configuration.ReportPath);
        }
        private static string Digest(string path) { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(); }
        private static string KnownTransportCode(string reason)
        {
            switch (reason) { case "WebSocketException": case "AuthenticationException": case "OperationCanceledException": case "ObjectDisposedException": case "InvalidOperationException": case "closed": case "send failed": case "session_replaced": return reason; default: return "other"; }
        }
        private void OnApplicationQuit() { if (active && !finished) { report.status = "FAIL"; report.errorCode = "interrupted"; report.finishedUtc = DateTime.UtcNow.ToString("O"); session?.Dispose(); store?.Clear(); WriteReport(); } }
        private void OnDestroy() { session?.Dispose(); transport?.Dispose(); store?.Clear(); }
    }
}
