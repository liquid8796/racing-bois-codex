using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

namespace RacingBois.Diagnostics.NativeProbe
{
    public sealed class NativeProbeConfiguration
    {
        public bool Enabled { get; private set; }
        public string Endpoint { get; private set; }
        public string ReportPath { get; private set; }
        public string ExpectedFingerprint { get; private set; }
        public int Seconds { get; private set; } = 90;
        public static NativeProbeConfiguration Parse(string[] args)
        {
            var result = new NativeProbeConfiguration(); var seen = new HashSet<string>(StringComparer.Ordinal);
            for (int i = 0; i < args.Length; i++)
            {
                string arg = args[i]; if (!arg.StartsWith("--rb-native-", StringComparison.Ordinal)) continue;
                if (!seen.Add(arg)) throw new ArgumentException("duplicate_probe_option");
                if (arg == "--rb-native-probe") { result.Enabled = true; continue; }
                if (i + 1 >= args.Length) throw new ArgumentException("missing_probe_value");
                string value = args[++i];
                switch (arg)
                {
                    case "--rb-native-endpoint": result.Endpoint = value; break;
                    case "--rb-native-report": result.ReportPath = value; break;
                    case "--rb-native-fingerprint": result.ExpectedFingerprint = value; break;
                    case "--rb-native-seconds":
                        if (!int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out int seconds) || seconds < 60 || seconds > 600) throw new ArgumentException("duration_out_of_bounds");
                        result.Seconds = seconds; break;
                    default: throw new ArgumentException("unknown_probe_option");
                }
            }
            if (!result.Enabled)
            {
                if (seen.Count != 0) throw new ArgumentException("probe_opt_in_required");
                return result;
            }
            if (!Uri.TryCreate(result.Endpoint, UriKind.Absolute, out var endpoint) || endpoint.Scheme != "wss" ||
                endpoint.UserInfo.Length != 0 || endpoint.Query.Length != 0 || endpoint.Fragment.Length != 0 || endpoint.AbsolutePath != "/multiplayer")
                throw new ArgumentException("ordinary_wss_endpoint_required");
            result.Endpoint = endpoint.AbsoluteUri;
            if (string.IsNullOrWhiteSpace(result.ReportPath) || !Path.IsPathRooted(result.ReportPath) || Path.GetExtension(result.ReportPath) != ".json")
                throw new ArgumentException("absolute_json_report_required");
            result.ReportPath = Path.GetFullPath(result.ReportPath);
            if (result.ExpectedFingerprint == null || result.ExpectedFingerprint.Length != 64) throw new ArgumentException("source_fingerprint_required");
            foreach (char c in result.ExpectedFingerprint) if (!Uri.IsHexDigit(c)) throw new ArgumentException("invalid_source_fingerprint");
            result.ExpectedFingerprint = result.ExpectedFingerprint.ToLowerInvariant();
            return result;
        }
    }
}
