using RacingBois.Client.Application;

namespace RacingBois.Client.Presentation
{
    internal static class MultiplayerCopy
    {
        public static string Error(string message, string locale = DisplayLanguage.Default)
        {
            const string prefix="Máy chủ từ chối: ";
            if(string.IsNullOrEmpty(message)||!message.StartsWith(prefix,System.StringComparison.Ordinal))return UiText.ClientMessage(locale,message);
            switch(message.Substring(prefix.Length))
            {
                case "room_full":  return UiText.Get(locale, "multiplayer.error.room-full");
                case "room_not_found":  return UiText.Get(locale, "multiplayer.error.room-not-found");
                case "room_started": case "late_join_closed":  return UiText.Get(locale, "multiplayer.error.room-started");
                case "host_only":  return UiText.Get(locale, "multiplayer.error.host-only");
                case "not_ready":  return UiText.Get(locale, "multiplayer.error.not-ready");
                case "invalid_name":  return UiText.Get(locale, "multiplayer.error.invalid-name");
                case "room_settings":  return UiText.Get(locale, "multiplayer.error.room-settings");
                case "course_unavailable":  return UiText.Get(locale, "multiplayer.error.course-unavailable");
                case "campaign_locked":  return UiText.Get(locale, "multiplayer.error.campaign-locked");
                case "repair_required":  return UiText.Get(locale, "multiplayer.error.repair-required");
                case "profile_busy":  return UiText.Get(locale, "multiplayer.error.profile-busy");
                case "profile_revoked":  return UiText.Get(locale, "multiplayer.error.profile-revoked");
                case "already_in_room":  return UiText.Get(locale, "multiplayer.error.already-in-room");
                case "profile_in_room":  return UiText.Get(locale, "multiplayer.error.profile-in-room");
                case "profile_unavailable": case "profile_storage_unavailable":  return UiText.Get(locale, "multiplayer.error.profile-unavailable");
                case "resume_expired":  return UiText.Get(locale, "multiplayer.error.resume-expired");
                case "resume_owner": case "session_replaced":  return UiText.Get(locale, "multiplayer.error.resume-owner");
                case "version_mismatch":  return UiText.Get(locale, "multiplayer.error.version-mismatch");
                case "server_full": case "hello_capacity": case "profile_capacity":  return UiText.Get(locale, "multiplayer.error.server-full");
                case "room_capacity":  return UiText.Get(locale, "multiplayer.error.room-capacity");
                case "persistence_pending": case "start_pending":  return UiText.Get(locale, "multiplayer.error.persistence-pending");
                case "persistence_queue_full": case "persistence_unavailable":  return UiText.Get(locale, "multiplayer.error.persistence-queue-full");
                case "result_save_retry":  return UiText.Get(locale, "multiplayer.error.result-save-retry");
                case "start_cancelled":  return UiText.Get(locale, "multiplayer.error.start-cancelled");
                case "result_required":  return UiText.Get(locale, "multiplayer.error.result-required");
                case "command_rate":  return UiText.Get(locale, "multiplayer.error.command-rate");
                case "not_room_member":  return UiText.Get(locale, "multiplayer.error.not-room-member");
                default: return UiText.Get(locale, "multiplayer.error.unknown");
            }
        }
    }
}
