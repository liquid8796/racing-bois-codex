using System;
using System.IO;

namespace RacingBois.Client.Application
{
    /// <summary>Public installation settings. Credentials and player state never belong in this file.</summary>
    [Serializable]
    public sealed class DesktopRuntimeConfig
    {
        public int schema = 1;
        public string connectionMode = "lan";
        public string backendWebSocketUrl = "";
        public string contentBaseUrl = "";
    }

    public static class DesktopRuntimeConfigRules
    {
        public const string DefaultLanEndpoint = "ws://127.0.0.1:7777/multiplayer";
        public const int MaximumConfigBytes = 8192;

        public static string BackendEndpoint(DesktopRuntimeConfig config)
        {
            ValidateIdentity(config);
            string value = string.IsNullOrEmpty(config.backendWebSocketUrl) ? DefaultLanEndpoint : config.backendWebSocketUrl;
            if (!TryPublicUri(value, out var uri) || (uri.Scheme != "ws" && uri.Scheme != "wss") || uri.AbsolutePath != "/multiplayer")
                throw new ArgumentException("Địa chỉ máy chủ phải là WS/WSS và kết thúc bằng /multiplayer.");
            if (config.connectionMode == "online" && uri.Scheme != "wss")
                throw new ArgumentException("Máy chủ online cần kết nối WSS có chứng chỉ tin cậy.");
            if (config.connectionMode == "online" && string.IsNullOrEmpty(config.backendWebSocketUrl))
                throw new ArgumentException("Cấu hình online chưa có địa chỉ máy chủ.");
            return uri.AbsoluteUri;
        }

        public static Uri ContentBase(DesktopRuntimeConfig config, string streamingAssetsPath, bool editor, string editorBaseUrl = "")
        {
            ValidateIdentity(config);
            if (!string.IsNullOrEmpty(config.contentBaseUrl)) return RemoteContentBase(config.contentBaseUrl, false);
            if (editor && !string.IsNullOrEmpty(editorBaseUrl)) return RemoteContentBase(editorBaseUrl, true);
            string root = editor ? Path.GetFullPath("Build/Content-editor") : Path.GetFullPath(Path.Combine(streamingAssetsPath, "Content"));
            return new Uri(root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar);
        }

        public static Uri RemoteContentBase(string value, bool allowEditorLoopbackHttp)
        {
            if (!TryPublicUri(value, out var uri) || (uri.Scheme != "https" && !(allowEditorLoopbackHttp && uri.Scheme == "http" && uri.IsLoopback)) || value.Contains("%") || value.Contains("\\"))
                throw new ArgumentException("Nguồn nội dung từ xa cần URL HTTPS hợp lệ, không chứa thông tin đăng nhập.");
            return new Uri(uri.AbsoluteUri.TrimEnd('/') + "/");
        }

        private static void ValidateIdentity(DesktopRuntimeConfig config)
        {
            if (config == null || config.schema != 1 || (config.connectionMode != "lan" && config.connectionMode != "online"))
                throw new ArgumentException("Cấu hình desktop không phù hợp phiên bản trò chơi.");
        }

        private static bool TryPublicUri(string value, out Uri uri)
        {
            uri = null;
            return !string.IsNullOrEmpty(value) && value.Length <= 2048 && value == value.Trim() &&
                Uri.TryCreate(value, UriKind.Absolute, out uri) && uri.UserInfo.Length == 0 && uri.Query.Length == 0 && uri.Fragment.Length == 0;
        }
    }

    public static class DesktopMusicUrlRules
    {
        public static bool TryValidate(string value, Uri contentBase, out string normalized)
        {
            normalized = "";
            if (contentBase == null || string.IsNullOrEmpty(value) || value.Length > 4096 || !Uri.TryCreate(value, UriKind.Absolute, out var uri) ||
                uri.UserInfo.Length != 0 || uri.Query.Length != 0 || uri.Fragment.Length != 0 || uri.Scheme != contentBase.Scheme || uri.Authority != contentBase.Authority) return false;
            if (uri.IsFile)
            {
                foreach (char c in Uri.UnescapeDataString(uri.AbsolutePath)) if (char.IsControl(c)) return false;
                // AbsoluteUri may escape spaces in Program Files. Compare decoded, canonical paths with a separator boundary.
                try
                {
                    string root = Path.GetFullPath(contentBase.LocalPath).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
                    if (!Path.GetFullPath(uri.LocalPath).StartsWith(root, StringComparison.OrdinalIgnoreCase)) return false;
                }
                catch (ArgumentException) { return false; }
                catch (NotSupportedException) { return false; }
            }
            else if (uri.Scheme != "https" && !(uri.Scheme == "http" && uri.IsLoopback) || !uri.AbsolutePath.StartsWith(contentBase.AbsolutePath, StringComparison.Ordinal) || value.Contains("%")) return false;
            string file = Path.GetFileName(uri.LocalPath);
            if (!file.EndsWith(".ogg", StringComparison.OrdinalIgnoreCase) || file.Length < 68) return false;
            string hash = file.Substring(file.Length - 68, 64);
            foreach (char c in hash) if (!Uri.IsHexDigit(c)) return false;
            normalized = uri.AbsoluteUri;
            return true;
        }
    }
}
