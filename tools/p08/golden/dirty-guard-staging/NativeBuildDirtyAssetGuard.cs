using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Preserves dirty authoring data. Imported Shader artifacts use explicit source/importer/property identity.</summary>
    public sealed class NativeBuildDirtyAssetGuard
    {
        [Serializable] public sealed class Evidence
        {
            public string path, type, savedSha256, metaSha256, memorySha256;
            public long localId;
            public bool wasDirty, importedShaderArtifact, importerWasDirty;
            public string importerType, importerMemorySha256, dependencyHash, shaderName;
            public int shaderMaximumLod, globalMaximumLod, shaderHideFlags;
        }
        private sealed class State { internal UnityEngine.Object Value; internal Evidence Before; }
        private readonly State[] states;
        private readonly List<string> restoredDirtyFlags = new List<string>();

        public NativeBuildDirtyAssetGuard()
        {
            states = Resources.FindObjectsOfTypeAll<UnityEngine.Object>()
                .Where(value => value != null && EditorUtility.IsPersistent(value) && EditorUtility.IsDirty(value))
                .Where(value => AssetPath(AssetDatabase.GetAssetPath(value)))
                .Select(value => new State { Value = value, Before = Capture(value) }).ToArray();
        }
        public Evidence[] Before => states.Select(state => state.Before).ToArray();
        public string[] RestoredDirtyFlags => restoredDirtyFlags.ToArray();

        public void RejectDirtyDependencies(IEnumerable<string> logicalPaths)
        {
            var paths = new HashSet<string>(logicalPaths ?? Array.Empty<string>(), StringComparer.Ordinal);
            var rejected = new List<string>();
            foreach (var value in Resources.FindObjectsOfTypeAll<UnityEngine.Object>().Where(value => value != null && EditorUtility.IsPersistent(value) &&
                paths.Contains(AssetDatabase.GetAssetPath(value)) && EditorUtility.IsDirty(value)))
            {
                var current = Capture(value);
                var original = states.SingleOrDefault(state => state.Value == value)?.Before;
                // A .shader is imported compiler output, not an editable serialized Shader asset.
                // Only the observed read-only/default state with an unchanged clean ShaderImporter
                // is allowed. Materials, fonts, .asset data and dirty importers still reject.
                bool importedArtifact = original != null && current.importedShaderArtifact &&
                    !current.importerWasDirty && !original.importerWasDirty &&
                    current.shaderMaximumLod == -1 && current.globalMaximumLod == int.MaxValue &&
                    current.shaderHideFlags == (int)HideFlags.NotEditable &&
                    SameAuthoringIdentity(original, current) && DeclaredShaderNameMatches(current);
                if (!importedArtifact) rejected.Add(current.path);
            }
            if (rejected.Count != 0) throw new InvalidOperationException("dirty_build_dependencies:" + string.Join(",", rejected.Distinct()));
        }

        public void VerifyUnchanged()
        {
            var changed = new List<string>();
            foreach (var state in states)
            {
                try
                {
                    var current = Capture(state.Value);
                    if (!SameAuthoringIdentity(state.Before, current)) { changed.Add(state.Before.path + ":authoring-data"); continue; }
                    if (current.wasDirty != state.Before.wasDirty)
                    {
                        // Baseline01 proved URP can save an identical pipeline and clear its flag.
                        // Restore only that flag after exact data identity; never overwrite values.
                        if (!state.Before.wasDirty || current.wasDirty || current.memorySha256 != state.Before.memorySha256) { changed.Add(state.Before.path + ":dirty-state-or-memory"); continue; }
                        EditorUtility.SetDirty(state.Value);
                        var restored = Capture(state.Value);
                        if (!restored.wasDirty || !SameAuthoringIdentity(state.Before, restored)) changed.Add(state.Before.path + ":dirty-restore");
                        else restoredDirtyFlags.Add(state.Before.path);
                    }
                }
                catch (Exception error) { changed.Add(state.Before.path + ":" + error.GetType().Name); }
            }
            if (changed.Count != 0) throw new InvalidOperationException("unrelated_dirty_assets_changed:" + string.Join(",", changed.Distinct()));
        }

        private static bool SameAuthoringIdentity(Evidence before, Evidence after)
        {
            if (before.path != after.path || before.type != after.type || before.localId != after.localId ||
                before.savedSha256 != after.savedSha256 || before.metaSha256 != after.metaSha256 ||
                before.importedShaderArtifact != after.importedShaderArtifact) return false;
            if (!before.importedShaderArtifact) return before.memorySha256 == after.memorySha256;
            // Keep full compiler JSON hashes in Evidence for diagnosis, but do not mistake cache
            // bytes for authored source. All writable Shader properties and importer data bind.
            return before.importerType == after.importerType && before.importerMemorySha256 == after.importerMemorySha256 &&
                before.importerWasDirty == after.importerWasDirty && before.dependencyHash == after.dependencyHash &&
                before.shaderName == after.shaderName && before.shaderMaximumLod == after.shaderMaximumLod &&
                before.globalMaximumLod == after.globalMaximumLod && before.shaderHideFlags == after.shaderHideFlags;
        }
        private static bool DeclaredShaderNameMatches(Evidence evidence)
        {
            var matches = Regex.Matches(File.ReadAllText(Physical(evidence.path)), @"(?m)^\s*Shader\s+""([^""]+)""\s*\{");
            return matches.Count == 1 && matches[0].Groups[1].Value == evidence.shaderName;
        }
        private static Evidence Capture(UnityEngine.Object value)
        {
            if (value == null) throw new InvalidOperationException("dirty_asset_removed");
            string path = AssetDatabase.GetAssetPath(value);
            if (!AssetPath(path) || !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out string _, out long localId))
                throw new InvalidOperationException("dirty_asset_identity_unavailable");
            string physical = Physical(path);
            var result = new Evidence { path = path, type = value.GetType().FullName, localId = localId,
                savedSha256 = FileHash(physical), metaSha256 = FileHash(physical + ".meta"),
                memorySha256 = BytesHash(Encoding.UTF8.GetBytes(EditorJsonUtility.ToJson(value))), wasDirty = EditorUtility.IsDirty(value) };
            if (value is Shader shader && path.EndsWith(".shader", StringComparison.OrdinalIgnoreCase) && AssetImporter.GetAtPath(path) is ShaderImporter importer)
            {
                result.importedShaderArtifact = true; result.importerType = importer.GetType().FullName;
                result.importerMemorySha256 = BytesHash(Encoding.UTF8.GetBytes(EditorJsonUtility.ToJson(importer)));
                result.importerWasDirty = EditorUtility.IsDirty(importer); result.dependencyHash = AssetDatabase.GetAssetDependencyHash(path).ToString();
                result.shaderName = shader.name; result.shaderMaximumLod = shader.maximumLOD;
                result.globalMaximumLod = Shader.globalMaximumLOD; result.shaderHideFlags = (int)shader.hideFlags;
            }
            return result;
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
