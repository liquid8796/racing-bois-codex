using System;
using System.Collections.Generic;
using System.Linq;

namespace RacingBois.Diagnostics.NativeProbe
{
    /// <summary>Bounded, value-only diagnostics. Never stores raw errors, frames, tokens or identity fields.</summary>
    [Serializable]
    public sealed class NativeProbeObservations
    {
        [Serializable] public sealed class Count { public string code; public int count; }
        [Serializable] public sealed class Entry
        {
            public double elapsed; public string kind, code, stage, session;
            public bool reconnecting; public int pending, previousPending, late, future, missing;
        }
        public int connectionOpens, plannedReconnectTransitions, unexpectedReconnectTransitions, plannedResumeOpens, unexpectedConnectionOpens;
        public int latestPending, maximumPending, latestLate, latestFuture, latestMissing, maximumLate, maximumFuture;
        public string latestSessionCode = "none";
        public Count[] transportCodes = Array.Empty<Count>(), serverCodes = Array.Empty<Count>(), sessionCodes = Array.Empty<Count>();
        public Entry[] lifecycle = Array.Empty<Entry>();
        private readonly Dictionary<string, int> transport = new Dictionary<string, int>(), server = new Dictionary<string, int>(), sessions = new Dictionary<string, int>();
        private readonly Queue<Entry> entries = new Queue<Entry>();
        private bool reconnecting, resumePlanned;
        private string lastSession = "", lastCause = "none";
        public bool OnlyPlannedReconnect => connectionOpens == 2 && plannedReconnectTransitions == 1 && unexpectedReconnectTransitions == 0 &&
            plannedResumeOpens == 1 && unexpectedConnectionOpens == 0;

        public void PlanResume() { resumePlanned = true; }
        public void Opened(double elapsed, string stage, string session)
        {
            Increment(ref connectionOpens);
            if (connectionOpens > 1)
            {
                if (resumePlanned && plannedResumeOpens == 0 && stage == "Resuming") Increment(ref plannedResumeOpens);
                else Increment(ref unexpectedConnectionOpens);
            }
            Add(elapsed, "opened", "opened", stage, session, latestPending);
        }
        public void Closed(string reason, double elapsed, string stage, string session)
        { string code = TransportCode(reason); CountCode(transport, code); transportCodes = Export(transport); Add(elapsed, "closed", code, stage, session, latestPending); }
        public void ServerError(string reason, double elapsed, string stage, string session)
        { string code = ServerCode(reason); CountCode(server, code); serverCodes = Export(server); Add(elapsed, "mpError", code, stage, session, latestPending); }
        public void State(double elapsed, string stage, string session, string error, bool isReconnecting, int pending, int late, int future, int missing)
        {
            int previous = latestPending;
            latestPending = pending; maximumPending = Math.Max(maximumPending, pending);
            latestLate = late; latestFuture = future; latestMissing = missing;
            maximumLate = Math.Max(maximumLate, late); maximumFuture = Math.Max(maximumFuture, future);
            string cause = SessionCode(error); latestSessionCode = cause;
            if (isReconnecting && !reconnecting)
            {
                if (resumePlanned && plannedReconnectTransitions == 0 && cause == "planned_resume") Increment(ref plannedReconnectTransitions);
                else Increment(ref unexpectedReconnectTransitions);
            }
            if (session != lastSession || cause != lastCause || isReconnecting != reconnecting)
            {
                if (cause != "none" && cause != lastCause) { CountCode(sessions, cause); sessionCodes = Export(sessions); }
                reconnecting = isReconnecting; Add(elapsed, "session", cause, stage, session, previous);
            }
            reconnecting = isReconnecting; lastSession = session; lastCause = cause;
        }
        private void Add(double elapsed, string kind, string code, string stage, string session, int previous)
        {
            while (entries.Count >= 64) entries.Dequeue();
            entries.Enqueue(new Entry { elapsed = elapsed, kind = kind, code = code, stage = stage, session = session, reconnecting = reconnecting,
                pending = latestPending, previousPending = previous, late = latestLate, future = latestFuture, missing = latestMissing });
            lifecycle = entries.ToArray();
        }
        private static void Increment(ref int value) { if (value < int.MaxValue) value++; }
        private static void CountCode(Dictionary<string, int> values, string code) { values.TryGetValue(code, out int count); if (count < int.MaxValue) count++; values[code] = count; }
        private static Count[] Export(Dictionary<string, int> values) => values.OrderBy(pair => pair.Key, StringComparer.Ordinal).Select(pair => new Count { code = pair.Key, count = pair.Value }).ToArray();
        public static string TransportCode(string value)
        {
            switch (value)
            {
                case "WebSocketException": case "AuthenticationException": case "OperationCanceledException": case "ObjectDisposedException":
                case "InvalidOperationException": case "closed": case "send failed": return value;
                case "Địa chỉ máy chủ không hợp lệ.": return "invalid_endpoint";
                default: return ServerCode(value);
            }
        }
        public static string ServerCode(string value)
        {
            switch (value)
            {
                case "input_late": case "input_future": case "input_sequence": case "input_range": case "input_queue_full":
                case "already_attached": case "already_in_room": case "campaign_locked": case "command_rate": case "course_unavailable":
                case "future_ack": case "guest_profile_conflict": case "handshake_pending_conflict": case "handshake_replaced": case "heartbeat_timeout":
                case "hello_capacity": case "hello_nonce_conflict": case "hello_nonce_revoked": case "host_only": case "invalid_ack": case "invalid_hello":
                case "invalid_name": case "late_join_closed": case "logout": case "not_ready": case "not_room_member": case "persistence_pending":
                case "persistence_queue_full": case "persistence_unavailable": case "profile_busy": case "profile_capacity": case "profile_in_room":
                case "profile_revoked": case "profile_storage_unavailable": case "profile_unavailable": case "race_epoch": case "reliable_overflow":
                case "repair_required": case "request_sequence": case "request_stale": case "result_required": case "result_save_retry":
                case "resume_expired": case "resume_owner": case "room_capacity": case "room_full": case "room_not_found": case "room_settings":
                case "room_started": case "server_full": case "session_epoch": case "session_replaced": case "session_required": case "slow_reader":
                case "start_cancelled": case "start_pending": case "unknown_command": case "unknown_message": case "version_mismatch": return value;
                default: return "other";
            }
        }
        public static string SessionCode(string value)
        {
            switch (value)
            {
                case null: case "": return "none";
                case "Mất xác nhận từ máy chủ.": return "ack_or_snapshot_stalled";
                case "Dòng thời gian cần đồng bộ lại.": return "timeline_ahead";
                case "Kết nối quá thời gian chờ.": return "welcome_timeout";
                case "Máy chủ không phản hồi.": return "receive_timeout";
                case "Đang khôi phục phiên…": return "planned_resume";
                case "Kết nối bị gián đoạn.": return "transport_interrupted";
                case "Thiếu thông điệp trạng thái. Đang khôi phục…": return "reliable_gap";
                case "Không khôi phục được phiên. Hãy kết nối lại.": return "reconnect_exhausted";
                case "Đã đóng kết nối; máy chủ chưa xác nhận thoát phiên.": return "logout_ack_timeout";
                case "Máy chủ chưa xác nhận thoát phiên.": return "logout_closed_before_ack";
                case "Phiên đã tạm dừng trước khi nhận thông tin kết nối.": return "suspend_without_receipt";
                case "Phiên đã được mở ở thẻ khác. Chọn Khách mới để chơi thêm một người.": return "session_replaced";
                case "Phản hồi máy chủ vượt giới hạn.": return "response_budget";
                case "Dữ liệu máy chủ không hợp lệ. Phiên đã dừng để đồng bộ an toàn.": return "invalid_server_data";
            }
            const string prefix = "Máy chủ từ chối: ";
            return value.StartsWith(prefix, StringComparison.Ordinal) ? "server_" + ServerCode(value.Substring(prefix.Length)) : "other";
        }
    }
}
