using System;
using System.IO;

namespace RacingBois.Client.Bootstrap
{
    /// <summary>Explicit local QA configuration. No remote control or gameplay authority.</summary>
    [Serializable]
    public sealed class DesktopAcceptanceConfiguration
    {
        public int schema = 1;
        public string runId = "", outputDirectory = "", buildReceiptPath = "";
        public string buildReceiptSha256 = "", sourceFingerprint = "", executableSha256 = "", bootstrapSha256 = "", manifestSha256 = "";
        public int durationSeconds = 600, warmupSeconds = 10, raceWaitTimeoutSeconds = 300;
        public bool captureScreenshots;

        public void Validate(string installationRoot)
        {
            if (schema != 1 || !Guid.TryParseExact(runId, "N", out _)) throw new ArgumentException("Invalid QA schema or run ID.");
            if (durationSeconds != 600 || warmupSeconds < 5 || warmupSeconds > 60 || raceWaitTimeoutSeconds < 30 || raceWaitTimeoutSeconds > 1800)
                throw new ArgumentException("QA requires a complete 600-second sample and bounded warmup/wait.");
            foreach (string hash in new[] { buildReceiptSha256, sourceFingerprint, executableSha256, bootstrapSha256, manifestSha256 })
                if (!IsHash(hash)) throw new ArgumentException("QA identities must be full SHA-256 values.");
            if (!Path.IsPathFullyQualified(outputDirectory) || !Path.IsPathFullyQualified(buildReceiptPath))
                throw new ArgumentException("QA output and build receipt require absolute paths.");
            string output = Path.GetFullPath(outputDirectory), install = Path.GetFullPath(installationRoot);
            if (IsWithin(output, install) || IsWithin(install, output)) throw new ArgumentException("QA output must be outside the immutable installation.");
            if (Directory.Exists(output) || File.Exists(output)) throw new IOException("QA output already exists; use a fresh run.");
            if (!File.Exists(buildReceiptPath) || new FileInfo(buildReceiptPath).Length > 8 * 1024 * 1024)
                throw new ArgumentException("A bounded actual build receipt is required.");
            for (var parent = new DirectoryInfo(output).Parent; parent != null; parent = parent.Parent)
                if (parent.Exists && (parent.Attributes & FileAttributes.ReparsePoint) != 0)
                    throw new ArgumentException("QA output must not pass through a symlink or junction.");
        }

        public static bool IsHash(string text)
        {
            if (text == null || text.Length != 64) return false;
            foreach (char value in text) if (!(value >= '0' && value <= '9') && !(value >= 'a' && value <= 'f')) return false;
            return true;
        }

        private static bool IsWithin(string path, string root) => string.Equals(path.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar),
            root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar), StringComparison.OrdinalIgnoreCase) ||
            path.StartsWith(root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
    }
}
