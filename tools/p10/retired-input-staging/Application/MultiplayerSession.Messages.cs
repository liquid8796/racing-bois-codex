using System;
using System.Collections.Generic;
using System.Text;
using RacingBois.Gameplay.Definitions;
using RacingBois.NetworkMapping;
using RacingBois.Protocol;
using RacingBois.Simulation;

namespace RacingBois.Client.Application
{
    public sealed partial class MultiplayerSession
    {
        private void OnMessage(string text)
        {
            if (disposed || IsSuspended || Status == SessionStatus.Offline || Status == SessionStatus.Failed) return;
            if (text == null || text.Length > MultiplayerProtocol.MaxSnapshotBytes || Encoding.UTF8.GetByteCount(text) > MultiplayerProtocol.MaxSnapshotBytes)
            { Fail("Phản hồi máy chủ vượt giới hạn."); return; }
            try
            {
                var envelope = codec.Decode<MessageEnvelope>(text); if (envelope == null) return;
                if (envelope.kind == "mpWelcome") { Welcome(codec.Decode<MpWelcome>(text)); return; }
                if (envelope.kind == "mpError") { ServerError(codec.Decode<MpError>(text)); return; }
                if (Status != SessionStatus.Connected) return;
                lastReceiveAt = clock.NowSeconds;
                switch (envelope.kind)
                {
                    case "mpSnapshot": Snapshot(codec.Decode<MpSnapshot>(text)); break;
                    case "mpLobby": Lobby(codec.Decode<MpLobby>(text)); break;
                    case "mpRooms": Rooms(codec.Decode<MpRoomList>(text)); break;
                    case "mpEvents": Events(codec.Decode<MpEventBatch>(text)); break;
                    case "mpResult": Results(codec.Decode<MpResult>(text)); break;
                    case "mpPong": Pong(codec.Decode<MpPong>(text)); break;
                    case "mpAccepted": Accepted(codec.Decode<MpCommandAccepted>(text)); break;
                }
            }
            catch (Exception)
            {
                InvalidSnapshots++; Fail("Dữ liệu máy chủ không hợp lệ. Phiên đã dừng để đồng bộ an toàn.");
            }
        }
        private void Welcome(MpWelcome m)
        {
            if (!waitingWelcome || m == null || m.requestNonce != helloNonce || m.sessionEpoch <= sessionEpoch) return;
            Require(m.protocolVersion == MultiplayerProtocol.Version && m.simulationRulesVersion == MultiplayerProtocol.RulesVersion &&
                m.contentHash == MultiplayerProtocol.ContentHash && m.tickRate == 60 && m.snapshotRate == 20 && m.maxPlayers == 8 &&
                MultiplayerProjection.Text(m.sessionId, 128) && MultiplayerProjection.Text(m.resumeToken, 512) &&
                MultiplayerProjection.Text(m.profileId, 128) && MultiplayerProjection.Text(m.realmId, 128) && ValidName(m.displayName, 24) &&
                m.credits >= 0 && m.serverServiceTick >= 0 && m.reliableSequence >= 0, "Invalid welcome");
            if (receipt != null && m.resumed) Require(receipt.PlayerId == m.sessionId, "Resume identity changed");
            string acceptedProfileToken = m.profileToken ?? "";
            if (acceptedProfileToken.Length == 0 && credential != null && credential.ProfileId == m.profileId && credential.RealmId == m.realmId)
                acceptedProfileToken = credential.ProfileToken;
            if (!m.guest) Require(MultiplayerProjection.Text(acceptedProfileToken, 512), "Missing profile capability");
            // Nonces survive only pre-welcome retries; a later reconnect creates a new handshake capability.
            waitingWelcome = false; Status = SessionStatus.Connected; IsReconnecting = false; stableSince = clock.NowSeconds; Error = "";
            PlayerId = m.sessionId; sessionEpoch = m.sessionEpoch; IsGuest = m.guest; CurrentCredits = m.credits;
            realmId = m.realmId; serverProfileId = m.profileId; displayName = m.displayName; welcomeProfileToken = acceptedProfileToken;
            if (m.reliableReset) reliableSequence = m.reliableSequence;
            else Require(m.reliableSequence >= reliableSequence, "Reliable cursor went backwards");
            ClearRace(); requestId = leaveRequest = 0; Room = null; Result = null; nextPingAt = 0; lastReceiveAt = clock.NowSeconds;
            receipt = new ResumeReceipt("", "", PlayerId, m.resumeToken); resumeStore?.Save(endpoint, receipt);
            SaveCredential(); AnchorClock(m.serverServiceTick, true); helloNonce = Guid.NewGuid().ToString("N"); Changed?.Invoke(); RequestLobbyList();
        }
        private void SaveCredential()
        {
            if (freshGuest || IsGuest || string.IsNullOrEmpty(welcomeProfileToken)) return;
            credential = new ProfileCredential(welcomeProfileToken, serverProfileId, displayName, realmId, CurrentCredits);
            credentials?.Save(endpoint, credential);
        }
        private void Snapshot(MpSnapshot m)
        {
            if (m == null || m.sessionEpoch != sessionEpoch || Room == null || m.roomId != Room.RoomId || m.raceEpoch != Room.RaceEpoch) return;
            if (hasCheckpoint && m.tick < authoritative.Tick) return;
            Require(m.roomState >= 0 && m.roomState <= 4 && m.matchId == Room.MatchId && m.raceEpoch >= 1 && m.startServiceTick == Room.StartServiceTick && m.courseIndex == Room.CourseIndex && m.level == Room.LevelIndex, "Wrong race envelope");
            if (RiderId != 0) Require(m.riderId == RiderId, "Rider ownership changed");
            var projected = MultiplayerProjection.World(m, sequence, processedSequence, events.ToArray());
            var candidate = projected.World;
            var checkpoint = CheckpointMapper.ToCheckpoint(m.own); var analog = CheckpointMapper.ToInput(m.heldAnalog);
            var standingRows = new List<MultiplayerStandingReadModel>(m.standings.Length);
            foreach (var row in m.standings) if (row.values[0] < 2000)
                standingRows.Add(new MultiplayerStandingReadModel(row.values[0], row.values[1], (RaceOutcome)row.values[2], row.values[3] / 100f));
            if (m.resultsPending != ResultsPending)
            { ResultsPending = m.resultsPending; snapshotRevision++; cachedPresentation = null; }
            if (m.resultsPending || GameplayRules.IsTerminal(checkpoint.Data.Mode))
            { pending.Clear(); if (hasCheckpoint) predictor?.Restore(authoritative); correctionS = correctionD = 0; }
            if (hasCheckpoint && m.tick == authoritative.Tick)
            {
                // Countdown deliberately publishes tick0 for3seconds; its fresh snapshots must keep clock/freshness alive.
                if (Room.Phase == LobbyPhase.Countdown || Room.Phase == LobbyPhase.Results || ResultsPending || GameplayRules.IsTerminal(checkpoint.Data.Mode))
                { lastSnapshotAt = clock.NowSeconds; AnchorClock(m.serverServiceTick, false); }
                return;
            }
            // All validation and allocation completed before committing any authoritative session state.
            float oldS = predictedRider.LongitudinalMeters, oldD = predictedRider.LateralMeters;
            var oldMode = predictedRider.Mode; long predictedTick = predictor == null ? -1 : predictor.Checkpoint.Tick;
            PredictionNeighborBuilder.Fill(predictionNeighbors, projected, latestPredictionSnapshot, m.riderId);
            RiderId = m.riderId; MeasureRenderResidual(candidate); LatestAuthoritativeWorld = candidate; latestPredictionSnapshot = projected; Standings = standingRows.AsReadOnly();
            authoritative = checkpoint; snapshotRevision++; heldAnalog = new RaceInput(analog.ThrottlePermille, analog.BrakePermille, analog.SteerPermille);
            lastAppliedInputTick = m.lastAppliedInputTick; processedSequence = m.lastProcessedSequence; raceEpoch = m.raceEpoch;
            lastSnapshotAt = clock.NowSeconds; LateInputs = m.lateInputs; FutureInputs = m.futureInputs; MissingInputs = m.missingInputs;
            for (int i = pending.Count - 1; i >= 0; i--) if (pending[i].Tick <= m.resolvedThroughTick) pending.RemoveAt(i);
            if (predictor == null) predictor = new RiderPredictor(m.level, m.courseIndex);
            predictor.SetNeighbors(predictionNeighbors);
            bool wasReady = hasCheckpoint; hasCheckpoint = true; lastTargetTick = Math.Max(lastTargetTick, m.tick);
            remotes.Add(candidate); AnchorClock(m.serverServiceTick, false); ReplayPrediction();
            if (wasReady && predictedTick == predictor.Checkpoint.Tick)
            {
                float s = oldS - predictedRider.LongitudinalMeters, d = oldD - predictedRider.LateralMeters;
                LastCorrectionMeters = (float)Math.Sqrt(s * s + d * d);
                MaximumCorrectionMeters = Math.Max(MaximumCorrectionMeters, LastCorrectionMeters);
                if (oldMode == predictedRider.Mode && LastCorrectionMeters < 4)
                {
                    float remaining = Math.Max(0, 1 - (float)((clock.NowSeconds - correctionAt) / .12));
                    correctionS = s + correctionS * remaining; correctionD = d + correctionD * remaining; correctionAt = clock.NowSeconds;
                    if (correctionS * correctionS + correctionD * correctionD >= 16) correctionS = correctionD = 0;
                }
                else correctionS = correctionD = 0;
            }
            else correctionS = correctionD = 0;
            while (events.Count > 0 && events[0].Tick < m.tick - 120) { events.RemoveAt(0); eventRevision++; }
        }
        private void Lobby(MpLobby m)
        {
            if (m == null) throw new ArgumentException("Missing lobby");
            Reliable(m.reliableSequence, () =>
            {
                if (m.state == (int)MultiplayerRoomState.Closing && m.roomId == "" && m.members != null && m.members.Length == 0)
                { Room = null; Result = null; ClearRace(); SaveReceiptRoom(); Changed?.Invoke(); return; }
                var candidate = MultiplayerProjection.Lobby(m);
                bool belongs = false; foreach (var member in candidate.Members) if (member.PlayerId == PlayerId) belongs = true;
                Require(belongs, "Local participant missing");
                if (Room != null && Room.RoomId == candidate.RoomId && candidate.Revision < Room.Revision) return;
                if (Room != null && candidate.RoomId == Room.RoomId && candidate.RaceEpoch == Room.RaceEpoch && candidate.Phase == LobbyPhase.Results)
                    RetireRaceInputs();
                bool preserveRetired = Room != null && candidate.RoomId == Room.RoomId &&
                    ((Room.Phase == LobbyPhase.Results && candidate.Phase == LobbyPhase.Lobby && candidate.RaceEpoch == Room.RaceEpoch) ||
                     (Room.Phase == LobbyPhase.Lobby && candidate.Phase == LobbyPhase.Countdown && candidate.RaceEpoch == Room.RaceEpoch + 1));
                if (Room == null || candidate.RoomId != Room.RoomId || candidate.RaceEpoch != Room.RaceEpoch ||
                    (candidate.Phase == LobbyPhase.Lobby && Room.Phase != LobbyPhase.Lobby))
                { ClearRace(preserveRetired); Result = null; }
                if (candidate.Phase == LobbyPhase.Racing) retiredInputRange = default;
                Room = candidate; raceEpoch = candidate.RaceEpoch; AnchorClock(m.serverServiceTick, false);
                if (candidate.Phase == LobbyPhase.Results)
                { pending.Clear(); correctionS = correctionD = 0; if (hasCheckpoint) predictor?.Restore(authoritative); cachedPresentation = null; }
                foreach (var member in candidate.Members) if (member.PlayerId == PlayerId) RiderId = member.RiderId;
                SaveReceiptRoom(); Changed?.Invoke();
            });
        }
        private void SaveReceiptRoom()
        {
            if (receipt == null) return;
            receipt = new ResumeReceipt(Room?.RoomId ?? "", Room?.Code ?? "", PlayerId, receipt.ResumeToken); resumeStore?.Save(endpoint, receipt);
        }
        private void Rooms(MpRoomList m)
        {
            if (m == null) throw new ArgumentException("Missing room list");
            Reliable(m.reliableSequence, () =>
            {
                Require(m.rooms != null && m.rooms.Length <= MultiplayerProtocol.MaxRooms, "Room list capacity");
                var rows = new LobbySummaryReadModel[m.rooms.Length]; var codes = new HashSet<string>();
                for (int i = 0; i < rows.Length; i++)
                {
                    var r = m.rooms[i]; Require(r != null && MultiplayerProjection.Text(r.code, 16) && codes.Add(r.code) &&
                        ValidName(r.name, 40) && r.players >= 0 && r.players <= 8 && r.maxPlayers == 8 && r.state >= 0 && r.state <= 4, "Invalid room list entry");
                    rows[i] = new LobbySummaryReadModel(r.code, r.name, r.players, r.maxPlayers, (LobbyPhase)r.state, r.publicRoom, r.courseIndex, r.levelIndex);
                }
                Lobbies = Array.AsReadOnly(rows); Changed?.Invoke();
            });
        }
        private void Events(MpEventBatch m)
        {
            if (m == null) throw new ArgumentException("Missing event batch");
            Reliable(m.reliableSequence, () =>
            {
                Require(m.events != null && m.events.Length <= 128, "Event capacity");
                if (Room == null || m.roomId != Room.RoomId || m.raceEpoch != Room.RaceEpoch || m.matchId != Room.MatchId) return;
                var candidates = new List<RaceEventReadModel>(m.events.Length); long previous = 0;
                foreach (var e in m.events)
                {
                    Require(e != null && e.id > previous && e.tick >= 0 && e.kind >= 0 && e.kind <= (int)RaceEventKind.PedestrianRecovered &&
                        e.sourceId >= 0 && e.sourceId <= 4999 && e.targetId >= 0 && e.targetId <= 4999 && e.value >= -1000000 && e.value <= 1000000, "Invalid event");
                    previous = e.id; candidates.Add(new RaceEventReadModel(e.id, e.tick, (RaceEventKind)e.kind, e.sourceId, e.targetId, e.value));
                }
                foreach (var e in candidates)
                {
                    if (events.Count > 0 && e.Id <= events[events.Count - 1].Id) continue;
                    if (events.Count == 128) events.RemoveAt(0); events.Add(e); eventRevision++;
                }
            });
        }
        private void Results(MpResult m)
        {
            if (m == null) throw new ArgumentException("Missing result");
            Reliable(m.reliableSequence, () =>
            {
                Require(m.entries != null && m.entries.Length <= 16 && MultiplayerProjection.Text(m.resultId, 128), "Invalid result");
                if (Room == null || m.roomId != Room.RoomId || m.raceEpoch != Room.RaceEpoch || m.matchId != Room.MatchId) return;
                var entries = new MultiplayerResultEntry[m.entries.Length]; var ids = new HashSet<int>(); int credits = CurrentCredits;
                for (int i = 0; i < entries.Length; i++)
                {
                    var e = m.entries[i]; Require(e != null && e.riderId > 0 && e.riderId <= 1999 && ids.Add(e.riderId) &&
                        ValidName(e.displayName, 32) && e.outcome >= 0 && e.outcome <= 4 && e.rank >= 0 && e.rank <= 16 && e.reward >= -2000 && e.reward <= 100000 && e.credits >= 0 && e.finishTick >= -1, "Invalid result row");
                    entries[i] = new MultiplayerResultEntry(e.sessionId ?? "", e.displayName, e.riderId, (RaceOutcome)e.outcome, e.rank, e.reward, e.credits, e.finishTick);
                    if (e.sessionId == PlayerId) credits = e.credits;
                }
                Result = new MultiplayerResultReadModel(m.resultId, m.matchId, m.persisted, entries); CurrentCredits = credits;
                SaveCredential(); Changed?.Invoke();
            });
        }
        private void Accepted(MpCommandAccepted m)
        {
            if (m == null) return;
            Reliable(m.reliableSequence, () =>
            {
                if (m.sessionEpoch != sessionEpoch) return;
                if (logoutRequest != 0 && m.requestId == logoutRequest) { FinishDisconnect(true); return; }
                if (leaveRequest != 0 && m.requestId == leaveRequest)
                { leaveRequest = 0; Room = null; Result = null; ClearRace(); SaveReceiptRoom(); RequestLobbyList(); Changed?.Invoke(); }
            });
        }
        private void ServerError(MpError m)
        {
            if (m == null) return;
            Action apply = () =>
            {
                if (m.sessionEpoch != 0 && m.sessionEpoch != sessionEpoch) return;
                // A confirmed completed race may still have input frames in
                // flight. Consume/ack their reliable rejection without turning
                // expected turnover into a persistent user-facing error.
                if (IsRetiredInputError(m)) return;
                string code = m.code ?? "unknown";
                if (code.Length > 64) code = "unknown";
                foreach (char c in code) if (!(char.IsLetterOrDigit(c) || c == '_')) { code = "unknown"; break; }
                if (!m.terminal && (code == "input_late" || code == "input_future"))
                { if (code == "input_future" && m.serverServiceTick >= lastServiceStamp) AnchorClock(m.serverServiceTick, true); return; }
                Error = "Máy chủ từ chối: " + code;
                if (m.terminal)
                {
                    if (code.Contains("resume")) { resumeStore?.Clear(endpoint); receipt = null; }
                    Fail(Error);
                }
                else Changed?.Invoke();
            };
            if (waitingWelcome || m.reliableSequence == 0) apply(); else Reliable(m.reliableSequence, apply);
        }
        private void Pong(MpPong m)
        {
            if (m == null || m.sessionEpoch != sessionEpoch || m.nonce != pingNonce || m.clientMicroseconds != pingMicros) return;
            double sample = clock.NowSeconds - pingMicros / 1000000.0;
            Require(sample >= 0 && sample < 10 && m.serverServiceTick >= 0, "Invalid ping timing");
            if (rtt == 0) rtt = sample; else { jitter = jitter * .8 + Math.Abs(sample - rtt) * .2; rtt = rtt * .8 + sample * .2; }
            pingNonce = ""; AnchorClock(m.serverServiceTick, false);
        }
        private void AnchorClock(long serviceTick, bool reset)
        {
            if (!reset && serviceTick < lastServiceStamp) return;
            double now = clock.NowSeconds, candidate = serviceTick + rtt * 30;
            if (!reset && lastServiceStamp >= 0) candidate = Math.Max(EstimatedServiceTick - 2, candidate);
            clockAnchorTick = candidate; clockAnchorAt = now; lastServiceStamp = serviceTick;
        }
        private void Reliable(long seq, Action apply)
        {
            Require(seq > 0, "Invalid reliable sequence");
            if (seq <= reliableSequence) { AckReliable(); return; }
            if (seq != reliableSequence + 1) { ScheduleReconnect("Thiếu thông điệp trạng thái. Đang khôi phục…"); return; }
            apply(); reliableSequence = seq; AckReliable();
        }
        private void AckReliable()
        { if (Status == SessionStatus.Connected) transport.Send(codec.Encode(new MpAck { sessionEpoch = sessionEpoch, reliableSequence = reliableSequence })); }
        private static void Require(bool valid, string message) => MultiplayerProjection.Require(valid, message);
    }
}
