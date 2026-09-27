using System;
using System.IO;
using RacingBois.Client.Application;
using UnityEngine;

namespace RacingBois.Client.Adapters
{
    /// <summary>Reads only the public, installation-owned config. Save data remains in the existing storage adapter.</summary>
    public static class DesktopConfiguration
    {
        public const string FileName = "RacingBois.runtime.json";
        public static DesktopRuntimeConfig Read()
        {
            string path = Path.Combine(UnityEngine.Application.streamingAssetsPath, FileName);
            if (!File.Exists(path)) return new DesktopRuntimeConfig();
            if (new FileInfo(path).Length > DesktopRuntimeConfigRules.MaximumConfigBytes)
                throw new ArgumentException("Tệp cấu hình desktop vượt giới hạn kích thước.");
            DesktopRuntimeConfig config;
            try { config = JsonUtility.FromJson<DesktopRuntimeConfig>(File.ReadAllText(path)); }
            catch (ArgumentException) { throw new ArgumentException("Không đọc được cấu hình desktop."); }
            DesktopRuntimeConfigRules.BackendEndpoint(config);
            DesktopRuntimeConfigRules.ContentBase(config, UnityEngine.Application.streamingAssetsPath, UnityEngine.Application.isEditor);
            return config;
        }

        public static Uri ContentBase(DesktopRuntimeConfig config = null, string editorBaseUrl = "")
            => DesktopRuntimeConfigRules.ContentBase(config ?? Read(), UnityEngine.Application.streamingAssetsPath, UnityEngine.Application.isEditor, editorBaseUrl);
    }
}
