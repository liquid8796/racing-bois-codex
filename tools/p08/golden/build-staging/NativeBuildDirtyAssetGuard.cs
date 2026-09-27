using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Observes pre-existing dirty persistent assets; never saves, clears, reimports or restores user assets.</summary>
    public sealed class NativeBuildDirtyAssetGuard
    {
        [Serializable] public sealed class Evidence
        {
            public string path, type, savedSha256, metaSha256, memorySha256;
            public long localId;
            public bool wasDirty;
        }
        private sealed class State { internal UnityEngine.Object Value; internal Evidence Before; }
        private readonly State[] states;

        public NativeBuildDirtyAssetGuard()
        {
            states = Resources.FindObjectsOfTypeAll<UnityEngine.Object>()
                .Where(value => value != null && EditorUtility.IsPersistent(value) && EditorUtility.IsDirty(value))
                .Where(value => AssetPath(AssetDatabase.GetAssetPath(value)))
                .Select(value => new State { Value = value, Before = Capture(value) }).ToArray();
        }
        public Evidence[] Before => states.Select(state => state.Before).ToArray();
        public void RejectDirtyDependencies(IEnumerable<string> logicalPaths)
        {
            var paths = new HashSet<string>(logicalPaths ?? Array.Empty<string>(), StringComparer.Ordinal);
            var dirty = Resources.FindObjectsOfTypeAll<UnityEngine.Object>().Where(value => value != null && EditorUtility.IsPersistent(value) &&
                paths.Contains(AssetDatabase.GetAssetPath(value)) && EditorUtility.IsDirty(value)).Select(value => AssetDatabase.GetAssetPath(value)).Distinct().ToArray();
            if (dirty.Length != 0) throw new InvalidOperationException("dirty_build_dependencies:" + string.Join(",", dirty));
        }
        public void VerifyUnchanged()
        {
            var changed = new List<string>();
            foreach (var state in states)
            {
                try
                {
                    var current = Capture(state.Value);
                    if (JsonUtility.ToJson(current) != JsonUtility.ToJson(state.Before)) changed.Add(state.Before.path);
                }
                catch { changed.Add(state.Before.path); }
            }
            if (changed.Count != 0) throw new InvalidOperationException("unrelated_dirty_assets_changed:" + string.Join(",", changed.Distinct()));
        }
        private static Evidence Capture(UnityEngine.Object value)
        {
            if (value == null) throw new InvalidOperationException("dirty_asset_removed");
            string path = AssetDatabase.GetAssetPath(value);
            if (!AssetPath(path) || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out string _, out long localId))
                throw new InvalidOperationException("dirty_asset_identity_unavailable");
            string physical = Physical(path);
            return new Evidence { path = path, type = value.GetType().FullName, localId = localId,
                savedSha256 = FileHash(physical), metaSha256 = FileHash(physical + ".meta"),
                memorySha256 = BytesHash(Encoding.UTF8.GetBytes(EditorJsonUtility.ToJson(value))), wasDirty = EditorUtility.IsDirty(value) };
        }
        private static bool AssetPath(string path) => !string.IsNullOrEmpty(path) && (path.StartsWith("Assets/", StringComparison.Ordinal) || path.StartsWith("Packages/", StringComparison.Ordinal));
        private static string Physical(string path)
        {
            if (!path.StartsWith("Packages/", StringComparison.Ordinal)) return path;
            var package = UnityEditor.PackageManager.PackageInfo.FindForAssetPath(path);
            if (package == null) throw new InvalidOperationException("dirty_package_asset_unresolved");
            string prefix = "Packages/" + package.name + "/";
            if (!path.StartsWith(prefix, StringComparison.Ordinal)) throw new InvalidOperationException("dirty_package_asset_alias");
            return Path.Combine(package.resolvedPath, path.Substring(prefix.Length));
        }
        private static string FileHash(string path) => File.Exists(path) ? BytesHash(File.ReadAllBytes(path)) : "missing";
        private static string BytesHash(byte[] bytes) { using (var hash = SHA256.Create()) return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
    }
}
