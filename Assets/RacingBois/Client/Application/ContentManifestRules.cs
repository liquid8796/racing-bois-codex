using System;
using System.Collections.Generic;
using System.IO;
namespace RacingBois.Client.Application
{
    [Serializable] public sealed class P08BundleEntry
    { public string id, url, sha256, asset, kind; public uint crc; public long bytes; public int courseIndex; }
    [Serializable] public sealed class P08ContentManifest
    { public int schema; public string contentHash, actorsId, buildTarget; public P08BundleEntry[] bundles; }
    /// <summary>Pure validation shared by Unity streaming and native acceptance fixtures.</summary>
    public static class ContentManifestRules
    {
        public const long MaximumBundleBytes = 64L * 1024 * 1024;
        public static Dictionary<string,P08BundleEntry> Validate(P08ContentManifest manifest,string expectedHash,Uri contentBase,string expectedTarget = null)
        {
            if (manifest == null || manifest.schema != 1 || manifest.contentHash != expectedHash || manifest.actorsId != "actors" || manifest.bundles == null || manifest.bundles.Length < 11 || manifest.bundles.Length > 96)
                throw new InvalidDataException("Invalid content manifest identity.");
            if (!string.IsNullOrEmpty(expectedTarget) && manifest.buildTarget != expectedTarget)
                throw new InvalidDataException("Content manifest platform differs from the running player.");
            var entries = new Dictionary<string,P08BundleEntry>(StringComparer.Ordinal);
            foreach (var entry in manifest.bundles)
            {
                if (entry == null || !Identifier(entry.id) || entries.ContainsKey(entry.id) || entry.bytes <= 0 || entry.bytes > MaximumBundleBytes ||
                    !Hex(entry.sha256,64) || (entry.kind != "music" && (string.IsNullOrEmpty(entry.asset) || !entry.asset.StartsWith("assets/",StringComparison.Ordinal) || entry.asset.Length > 240 || entry.asset.Contains(".."))) ||
                    (entry.kind != "actors" && entry.kind != "route" && entry.kind != "music")) throw new InvalidDataException("Invalid bundle contract.");
                BundleUri(contentBase,entry.url);
                if (entry.kind == "music" && (!entry.url.EndsWith(".ogg",StringComparison.OrdinalIgnoreCase) || !entry.url.EndsWith(entry.sha256 + ".ogg",StringComparison.OrdinalIgnoreCase)))
                    throw new InvalidDataException("Streamed music URL must carry its content fingerprint.");
                entries.Add(entry.id,entry);
            }
            if (!entries.TryGetValue("actors",out var actors) || actors.kind != "actors") throw new InvalidDataException("Actor bundle missing.");
            for (int i = 0; i < 5; i++) if (!entries.TryGetValue("route-" + i,out var route) || route.kind != "route" || route.courseIndex != i) throw new InvalidDataException("Route bundle missing.");
            return entries;
        }
        public static Uri BundleUri(Uri contentBase,string relative)
        {
            if (contentBase == null || !contentBase.IsAbsoluteUri || contentBase.UserInfo.Length > 0 || contentBase.Query.Length > 0 || contentBase.Fragment.Length > 0 || !contentBase.AbsolutePath.EndsWith("/",StringComparison.Ordinal) || (contentBase.Scheme != "http" && contentBase.Scheme != "https" && !contentBase.IsFile) ||
                string.IsNullOrEmpty(relative) || relative.Length > 180 || relative.Contains("..") || relative.Contains("%") || relative.Contains("\\") || relative.Contains("?") || relative.Contains("#") || relative.StartsWith("/"))
                throw new InvalidDataException("Invalid content URL.");
            if (!Uri.TryCreate(relative,UriKind.Relative,out _)) throw new InvalidDataException("Absolute bundle URL rejected.");
            var result = new Uri(contentBase,relative);
            if (result.Scheme != contentBase.Scheme || result.Authority != contentBase.Authority || !result.AbsolutePath.StartsWith(contentBase.AbsolutePath,StringComparison.Ordinal))
                throw new InvalidDataException("Bundle escapes its same-origin content root.");
            return result;
        }
        private static bool Identifier(string value)
        { if (string.IsNullOrEmpty(value) || value.Length > 64) return false; foreach (char c in value) if (!(c >= 'a' && c <= 'z' || c >= '0' && c <= '9' || c == '-')) return false; return true; }
        private static bool Hex(string value,int count)
        { if (value == null || value.Length != count) return false; foreach (char c in value) if (!Uri.IsHexDigit(c)) return false; return true; }
    }
}
