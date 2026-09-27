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
            public FontTextureEvidence emptyImportedFontTexture;
        }
        [Serializable] public sealed class FontTextureEvidence
        {
            public string guid, ownerName, ownerMemorySha256, materialMemorySha256;
            public long ownerLocalId, materialLocalId, textureLocalId;
            public int ownerHideFlags, textureHideFlags, width, height, format, mipmapCount, filter, wrapU, wrapV, wrapW, anisoLevel;
            public float mipMapBias;
            public bool dynamicFont, ownerWasDirty, materialWasDirty, readable;
            public string textureName;
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

        /// <summary>BuildPlayer can autosave unrelated authoring objects; refuse drafts before invoking it.</summary>
        public void RejectUnsavedAuthoringAssets()
        {
            var rejected = Resources.FindObjectsOfTypeAll<UnityEngine.Object>()
                .Where(value => value != null && EditorUtility.IsPersistent(value) && EditorUtility.IsDirty(value))
                .Where(value => AssetPath(AssetDatabase.GetAssetPath(value)))
                // An observed empty imported TTF texture is the sole texture exception.
                // Authored textures, SDF atlases, materials, ScriptableObjects and fonts still reject.
                .Where(value => !(value is Shader) && !(value is AssetImporter) && !UnchangedEmptyFontTexture(value))
                .Select(value => AssetDatabase.GetAssetPath(value) + ":" + value.GetType().FullName)
                .Distinct().OrderBy(path => path, StringComparer.Ordinal).ToArray();
            if (rejected.Length != 0) throw new InvalidOperationException("unsaved_authoring_assets_before_build:" + string.Join(",", rejected));
        }

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
                // is allowed. The independently identified empty TTF texture has its own strict contract.
                bool importedArtifact = original != null && current.importedShaderArtifact &&
                    !current.importerWasDirty && !original.importerWasDirty &&
                    current.shaderMaximumLod == -1 && current.globalMaximumLod == int.MaxValue &&
                    current.shaderHideFlags == (int)HideFlags.NotEditable &&
                    SameAuthoringIdentity(original, current) && DeclaredShaderNameMatches(current);
                importedArtifact |= original != null && original.emptyImportedFontTexture != null &&
                    current.emptyImportedFontTexture != null && SameAuthoringIdentity(original, current);
                if (!importedArtifact) rejected.Add(current.path);
            }
            if (rejected.Count != 0) throw new InvalidOperationException("dirty_build_dependencies:" + string.Join(",", rejected.Distinct()));
        }

        private bool UnchangedEmptyFontTexture(UnityEngine.Object value)
        {
            var original = states.SingleOrDefault(state => state.Value == value)?.Before;
            if (original == null || original.emptyImportedFontTexture == null) return false;
            var current = Capture(value);
            return current.emptyImportedFontTexture != null && SameAuthoringIdentity(original, current);
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
                before.importedShaderArtifact != after.importedShaderArtifact ||
                (before.emptyImportedFontTexture == null) != (after.emptyImportedFontTexture == null)) return false;
            if (before.emptyImportedFontTexture != null)
                return before.memorySha256 == after.memorySha256 &&
                    before.importerType == after.importerType && before.importerMemorySha256 == after.importerMemorySha256 &&
                    before.importerWasDirty == after.importerWasDirty && before.dependencyHash == after.dependencyHash &&
                    JsonUtility.ToJson(before.emptyImportedFontTexture) == JsonUtility.ToJson(after.emptyImportedFontTexture);
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
            else if (value is Texture2D texture) CaptureEmptyImportedFontTexture(texture, path, result);
            return result;
        }

        private static void CaptureEmptyImportedFontTexture(Texture2D texture, string path, Evidence result)
        {
            // The native proof covers only empty, unreadable, read-only TTF importer caches.
            // A populated texture or a TextCore/SDF .asset never enters this exception.
            if (!path.StartsWith("Assets/", StringComparison.Ordinal) || !path.EndsWith(".ttf", StringComparison.OrdinalIgnoreCase) ||
                !AssetDatabase.IsSubAsset(texture) || texture.name != "Font Texture" || texture.hideFlags != HideFlags.NotEditable ||
                texture.width != 0 || texture.height != 0 || texture.format != TextureFormat.Alpha8 || texture.mipmapCount != 1 ||
                texture.isReadable || texture.filterMode != FilterMode.Bilinear || texture.wrapModeU != TextureWrapMode.Repeat ||
                texture.wrapModeV != TextureWrapMode.Repeat || texture.wrapModeW != TextureWrapMode.Repeat || texture.anisoLevel != 1 || texture.mipMapBias != 0)
                return;
            if (!(AssetImporter.GetAtPath(path) is TrueTypeFontImporter importer) || EditorUtility.IsDirty(importer) ||
                !(AssetDatabase.LoadMainAssetAtPath(path) is Font owner) || !owner.dynamic || owner.hideFlags != HideFlags.NotEditable || EditorUtility.IsDirty(owner))
                return;
            var material = owner.material;
            if (material == null || EditorUtility.IsDirty(material) || material.mainTexture != texture || !AssetDatabase.IsSubAsset(material) ||
                AssetDatabase.GetAssetPath(owner) != path || AssetDatabase.GetAssetPath(material) != path ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(owner, out string ownerGuid, out long ownerId) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string materialGuid, out long materialId) ||
                !AssetDatabase.TryGetGUIDAndLocalFileIdentifier(texture, out string textureGuid, out long textureId) ||
                ownerGuid != materialGuid || ownerGuid != textureGuid || ownerGuid != AssetDatabase.AssetPathToGUID(path) ||
                ownerId != 12800000 || materialId != 2100000 || textureId != 2800000 || textureId != result.localId)
                return;
            result.emptyImportedFontTexture = new FontTextureEvidence
            {
                guid = ownerGuid, ownerName = owner.name, ownerLocalId = ownerId, materialLocalId = materialId, textureLocalId = textureId,
                ownerMemorySha256 = BytesHash(Encoding.UTF8.GetBytes(EditorJsonUtility.ToJson(owner))),
                materialMemorySha256 = BytesHash(Encoding.UTF8.GetBytes(EditorJsonUtility.ToJson(material))),
                ownerHideFlags = (int)owner.hideFlags, textureHideFlags = (int)texture.hideFlags,
                dynamicFont = owner.dynamic, ownerWasDirty = EditorUtility.IsDirty(owner), materialWasDirty = EditorUtility.IsDirty(material),
                textureName = texture.name, width = texture.width, height = texture.height, format = (int)texture.format,
                mipmapCount = texture.mipmapCount, filter = (int)texture.filterMode, wrapU = (int)texture.wrapModeU,
                wrapV = (int)texture.wrapModeV, wrapW = (int)texture.wrapModeW, anisoLevel = texture.anisoLevel,
                mipMapBias = texture.mipMapBias, readable = texture.isReadable
            };
            result.importerType = importer.GetType().FullName;
            result.importerMemorySha256 = BytesHash(Encoding.UTF8.GetBytes(EditorJsonUtility.ToJson(importer)));
            result.importerWasDirty = EditorUtility.IsDirty(importer);
            result.dependencyHash = AssetDatabase.GetAssetDependencyHash(path).ToString();
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
