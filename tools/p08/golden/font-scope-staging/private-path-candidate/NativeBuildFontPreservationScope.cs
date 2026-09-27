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
    /// <summary>Temporarily protects clean, unreferenced dynamic TextCore font assets from the global build hook.</summary>
    public sealed class NativeBuildFontPreservationScope : IDisposable
    {
        private const string FontType = "UnityEngine.TextCore.Text.FontAsset";
        private const string ClearField = "m_ClearDynamicDataOnBuild";
        private const string ProbeRoot = "Assets/RacingBois/Golden/Generated/FontPreservationProbe/";
        private sealed class MemberState
        {
            internal UnityEngine.Object Value;
            internal MemberRecord Before;
        }
        private sealed class State
        {
            internal UnityEngine.Object Owner;
            internal string OwnerJson, TransientJson;
            internal FontRecord Record;
            internal MemberState[] Members;
            internal bool Applied, TransientDirtyCleared, Restored;
        }
        [Serializable] public sealed class MemberRecord
        {
            public string type, name, memorySha256, pixelsSha256;
            public long localId;
            public bool dirty, readable;
            public int width, height, format, mipmaps, hideFlags;
        }
        [Serializable] public sealed class FontRecord
        {
            public string path, guid, sourceSha256, metaSha256, ownerMemorySha256, transientOwnerMemorySha256;
            public string sourceBackup, metaBackup, ownerMemoryBackup;
            public int populationMode;
            public bool clearOnBuild, ownerDirty;
            public long[] atlasLocalIds;
            public MemberRecord[] members;
        }
        [Serializable] public sealed class Report
        {
            public int schema = 1;
            public string scope, state, utc;
            public bool globalSelection, applied, restored, sourceBytesPreserved, memoryAndAtlasPreserved;
            public string[] failures;
            public FontRecord[] fonts;
        }
        private readonly List<State> states = new List<State>();
        private readonly string evidenceDirectory;
        private readonly bool globalSelection;
        private bool applied, restored;

        /// <summary>Captures and backs up first. Journal Restore before calling Apply.</summary>
        public NativeBuildFontPreservationScope(IEnumerable<string> actualBuildDependencies, string newEvidenceDirectory)
            : this(actualBuildDependencies, newEvidenceDirectory, null) { }

        /// <summary>Only an owned copied font may exercise the scope without touching real project fonts.</summary>
        public static NativeBuildFontPreservationScope ForOwnedCopyProbe(string fontPath, string newEvidenceDirectory)
        {
            Need(fontPath != null && fontPath.StartsWith(ProbeRoot, StringComparison.Ordinal), "owned_font_probe_copy_required");
            return new NativeBuildFontPreservationScope(Array.Empty<string>(), newEvidenceDirectory, new[] { fontPath });
        }

        private NativeBuildFontPreservationScope(IEnumerable<string> dependencies, string newEvidenceDirectory, string[] probePaths)
        {
            evidenceDirectory = FreshEvidencePath(newEvidenceDirectory);
            globalSelection = probePaths == null;
            var referenced = new HashSet<string>(dependencies ?? Array.Empty<string>(), StringComparer.Ordinal);
            var paths = probePaths ?? AssetDatabase.FindAssets("t:FontAsset", new[] { "Assets" })
                .Select(AssetDatabase.GUIDToAssetPath).Distinct().OrderBy(path => path, StringComparer.Ordinal).ToArray();
            foreach (string path in paths)
            {
                AssetFile(path); AssetFile(path + ".meta");
                var owner = AssetDatabase.LoadMainAssetAtPath(path);
                if (owner == null || owner.GetType().FullName != FontType)
                { Need(globalSelection, "probe_must_be_textcore_font"); continue; }
                var serialized = new SerializedObject(owner);
                var clear = serialized.FindProperty(ClearField);
                var population = serialized.FindProperty("m_AtlasPopulationMode");
                Need(clear != null && clear.propertyType == SerializedPropertyType.Boolean && population != null &&
                    (population.propertyType == SerializedPropertyType.Integer || population.propertyType == SerializedPropertyType.Enum), "textcore_font_schema_changed");
                if (!clear.boolValue || (population.intValue != 1 && population.intValue != 2)) continue;
                Need(!referenced.Contains(path), "referenced_dynamic_font_requires_isolated_build:" + path);
                Need(!EditorUtility.IsDirty(owner), "dirty_font_owner_not_owned:" + path);
                var atlasProperty = serialized.FindProperty("m_AtlasTextures");
                var materialProperty = serialized.FindProperty("m_Material");
                Need(atlasProperty != null && atlasProperty.isArray && atlasProperty.arraySize > 0 && materialProperty != null, "font_membership_schema_changed");
                var atlas = Enumerable.Range(0, atlasProperty.arraySize).Select(i => atlasProperty.GetArrayElementAtIndex(i).objectReferenceValue as Texture2D).ToArray();
                Need(atlas.All(texture => texture != null && EditorUtility.IsPersistent(texture) && AssetDatabase.GetAssetPath(texture) == path && texture.isReadable), "font_atlas_must_be_owned_readable_subassets");
                // The observed native hook does not act on an empty-width atlas. Preserve it without intervention.
                if (atlas[0].width == 0) continue;
                var material = materialProperty.objectReferenceValue as Material;
                Need(material != null && EditorUtility.IsPersistent(material) && AssetDatabase.GetAssetPath(material) == path && material.HasProperty("_MainTex") && material.GetTexture("_MainTex") == atlas[0], "font_material_atlas_membership_changed");
                var members = AssetDatabase.LoadAllAssetsAtPath(path);
                Need(members.Length > 0 && members.All(value => value != null && !EditorUtility.IsDirty(value)), "dirty_font_subasset_not_owned:" + path);
                Need(members.All(value => value == owner || value is Material || value is Texture2D) && members.Contains(material) && atlas.All(members.Contains), "unsupported_font_subasset");
                Need(members.OfType<Texture2D>().Count() == atlas.Length, "font_has_unbound_texture_subasset");
                string ownerJson = EditorJsonUtility.ToJson(owner);
                string transient = ToggleJsonFlag(ownerJson, false);
                string guid = AssetDatabase.AssetPathToGUID(path);
                Need(guid != null && guid.Length == 32 && guid.All(Uri.IsHexDigit), "font_guid_missing");
                var memberStates = members.Select(value => new MemberState { Value = value, Before = CaptureMember(value) }).ToArray();
                var record = new FontRecord
                {
                    path = path, guid = guid, sourceSha256 = FileHash(path), metaSha256 = FileHash(path + ".meta"),
                    populationMode = population.intValue, clearOnBuild = true, ownerDirty = false,
                    ownerMemorySha256 = TextHash(ownerJson), transientOwnerMemorySha256 = TextHash(transient),
                    atlasLocalIds = atlas.Select(LocalId).ToArray(), members = memberStates.Select(member => member.Before).ToArray(),
                    sourceBackup = guid + ".asset", metaBackup = guid + ".asset.meta", ownerMemoryBackup = guid + ".owner-before.json"
                };
                states.Add(new State { Owner = owner, OwnerJson = ownerJson, TransientJson = transient, Record = record, Members = memberStates });
            }
            Need(globalSelection || states.Count == 1, "owned_probe_requires_one_eligible_font");
            // Capture all candidate states before writing evidence or changing any object.
            Directory.CreateDirectory(evidenceDirectory);
            foreach (var state in states)
            {
                WriteNew(Path.Combine(evidenceDirectory, state.Record.sourceBackup), File.ReadAllBytes(AssetFile(state.Record.path)));
                WriteNew(Path.Combine(evidenceDirectory, state.Record.metaBackup), File.ReadAllBytes(AssetFile(state.Record.path + ".meta")));
                WriteNew(Path.Combine(evidenceDirectory, state.Record.ownerMemoryBackup), Encoding.UTF8.GetBytes(state.OwnerJson));
                Need(FileHash(Path.Combine(evidenceDirectory, state.Record.sourceBackup)) == state.Record.sourceSha256 &&
                    FileHash(Path.Combine(evidenceDirectory, state.Record.metaBackup)) == state.Record.metaSha256, "font_changed_during_backup");
                CheckState(state, false, false);
            }
            WriteReport("prepared", Array.Empty<string>(), false);
        }

        public FontRecord[] Before => states.Select(state => state.Record).ToArray();
        public bool IsGlobalSelection => globalSelection;

        public void Apply()
        {
            Need(!applied && !restored, "font_scope_already_used");
            foreach (var state in states) CheckState(state, false, false);
            foreach (var state in states)
            {
                // Mark ownership before invoking a native setter so partial failures are restorable.
                state.Applied = true;
                SetClearFlag(state.Owner, false);
                CheckState(state, true, true);
                // The owner was proved clean and only our single field differs. Suppress only
                // this owned transient dirty flag; never clear pre-existing authoring changes.
                EditorUtility.ClearDirty(state.Owner);
                state.TransientDirtyCleared = true;
                CheckState(state, true, false);
            }
            applied = true; WriteReport("applied", Array.Empty<string>(), false);
        }

        public void VerifyProtected()
        {
            Need(applied && !restored, "font_scope_not_active");
            foreach (var state in states) CheckState(state, true, false);
        }

        public void Restore()
        {
            if (restored) return;
            var failures = new List<string>();
            foreach (var state in states.AsEnumerable().Reverse())
            {
                if (!state.Applied || state.Restored) continue;
                try
                {
                    // Do not restore whole JSON, pixels, source files or metadata. If anything
                    // outside our flag changed, preserve it and fail for root to inspect/recover.
                    CheckState(state, true, !state.TransientDirtyCleared);
                    SetClearFlag(state.Owner, true);
                    CheckState(state, false, true);
                    EditorUtility.ClearDirty(state.Owner);
                    CheckState(state, false, false);
                    state.Restored = true;
                }
                catch (Exception error)
                {
                    failures.Add(state.Record.path + ":" + error.GetType().Name + ":" + error.Message);
                    // Even on a mismatch, return only our reserved flag when the exact owner
                    // still exists. Preserve all other values and the resulting dirty state.
                    try
                    {
                        if (state.Owner != null && AssetDatabase.GetAssetPath(state.Owner) == state.Record.path && AssetDatabase.AssetPathToGUID(state.Record.path) == state.Record.guid)
                        {
                            var flag = new SerializedObject(state.Owner).FindProperty(ClearField);
                            if (flag != null && !flag.boolValue) SetClearFlag(state.Owner, true);
                        }
                    }
                    catch (Exception restoreError) { failures.Add(state.Record.path + ":flag-restore:" + restoreError.GetType().Name); }
                }
            }
            // Constructor-only scopes never mutated fonts and still verify their original state.
            foreach (var state in states.Where(state => !state.Applied))
                try { CheckState(state, false, false); } catch (Exception error) { failures.Add(state.Record.path + ":" + error.Message); }
            restored = failures.Count == 0;
            WriteReport(restored ? "restored" : "restore-failed", failures.ToArray(), restored);
            Need(restored, "font_preservation_restore_failed:" + string.Join(",", failures));
        }
        public void Dispose() => Restore();

        private static void CheckState(State state, bool transient, bool allowOwnedDirty)
        {
            var record = state.Record;
            Need(state.Owner != null && AssetDatabase.GetAssetPath(state.Owner) == record.path && AssetDatabase.AssetPathToGUID(record.path) == record.guid, "font_owner_identity_changed");
            Need(FileHash(AssetFile(record.path)) == record.sourceSha256 && FileHash(AssetFile(record.path + ".meta")) == record.metaSha256, "font_source_or_meta_changed");
            Need(EditorJsonUtility.ToJson(state.Owner) == (transient ? state.TransientJson : state.OwnerJson), "font_owner_data_changed_beyond_owned_flag");
            var currentMembers = AssetDatabase.LoadAllAssetsAtPath(record.path);
            Need(currentMembers.Length == state.Members.Length && state.Members.All(member => currentMembers.Contains(member.Value)), "font_subasset_identity_changed");
            foreach (var member in state.Members)
            {
                var current = CaptureMember(member.Value); var before = member.Before;
                if (member.Value == state.Owner)
                {
                    current.memorySha256 = before.memorySha256; // Full expected owner JSON already checked above.
                    if (allowOwnedDirty) current.dirty = before.dirty;
                }
                Need(JsonUtility.ToJson(current) == JsonUtility.ToJson(before), "font_material_or_atlas_changed:" + before.localId);
            }
        }
        private static void SetClearFlag(UnityEngine.Object owner, bool value)
        {
            var serialized = new SerializedObject(owner); var field = serialized.FindProperty(ClearField);
            Need(field != null && field.propertyType == SerializedPropertyType.Boolean, "textcore_clear_field_missing");
            field.boolValue = value; serialized.ApplyModifiedPropertiesWithoutUndo();
            var check = new SerializedObject(owner).FindProperty(ClearField);
            Need(check != null && check.boolValue == value, "font_clear_flag_did_not_apply");
        }
        private static string ToggleJsonFlag(string json, bool value)
        {
            var pattern = new Regex("(\\\"" + ClearField + "\\\"\\s*:\\s*)(true|false|0|1)(?=\\s*[,}])");
            var matches = pattern.Matches(json);
            Need(matches.Count == 1 && (matches[0].Groups[2].Value == "true" || matches[0].Groups[2].Value == "1"), "font_clear_json_schema_changed");
            return pattern.Replace(json, match => match.Groups[1].Value + ((match.Groups[2].Value == "true" || match.Groups[2].Value == "false") ? (value ? "true" : "false") : (value ? "1" : "0")));
        }
        private static MemberRecord CaptureMember(UnityEngine.Object value)
        {
            Need(value != null, "font_member_missing");
            var record = new MemberRecord { type = value.GetType().FullName, name = value.name, localId = LocalId(value),
                dirty = EditorUtility.IsDirty(value), hideFlags = (int)value.hideFlags, memorySha256 = TextHash(EditorJsonUtility.ToJson(value)) };
            if (value is Texture2D texture)
            {
                Need(texture.isReadable, "font_atlas_cpu_pixels_unavailable");
                record.readable = true; record.width = texture.width; record.height = texture.height;
                record.format = (int)texture.format; record.mipmaps = texture.mipmapCount;
                record.pixelsSha256 = BytesHash(texture.GetRawTextureData<byte>().ToArray());
            }
            return record;
        }
        private static long LocalId(UnityEngine.Object value)
        {
            Need(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(value, out string _, out long id), "font_member_local_id_missing");
            return id;
        }
        private void WriteReport(string phase, string[] failures, bool preserved)
        {
            var report = new Report { scope = "Unreferenced clean dynamic TextCore font preservation only; no source asset save/reimport or atlas rewrite.",
                state = phase, utc = DateTime.UtcNow.ToString("O"), globalSelection = globalSelection, applied = applied, restored = restored,
                sourceBytesPreserved = preserved, memoryAndAtlasPreserved = preserved, failures = failures, fonts = Before };
            string path = Path.Combine(evidenceDirectory, phase + ".json");
            if (!File.Exists(path)) WriteNew(path, Encoding.UTF8.GetBytes(JsonUtility.ToJson(report, true)));
        }
        private static string FreshEvidencePath(string path)
        {
            Need(!string.IsNullOrWhiteSpace(path), "font_evidence_path_missing");
            string root = Path.GetFullPath(".").TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string full = Path.GetFullPath(path);
            Need(full.StartsWith(root, StringComparison.OrdinalIgnoreCase) && !Directory.Exists(full) && !File.Exists(full), "fresh_project_font_evidence_required");
            string relative = Path.GetRelativePath(root, full).Replace('\\', '/');
            Need(relative.StartsWith("_local/", StringComparison.Ordinal) || relative.StartsWith("Build/", StringComparison.Ordinal), "font_backups_must_stay_in_private_build_or_local_storage");
            NoLinks(full, root); return full;
        }
        private static string AssetFile(string path)
        {
            Need(path != null && path.StartsWith("Assets/", StringComparison.Ordinal) && !path.Contains("\\") && !path.Contains(":") && !path.Split('/').Any(part => part == ".." || part == "." || part.Length == 0), "canonical_font_asset_path_required");
            string root = Path.GetFullPath(".").TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string full = Path.GetFullPath(path);
            Need(full.StartsWith(root, StringComparison.OrdinalIgnoreCase) && File.Exists(full), "font_asset_missing"); NoLinks(full, root); return full;
        }
        private static void NoLinks(string path, string root)
        {
            for (string current = path; current != null && current.Length >= root.Length - 1; current = Path.GetDirectoryName(current))
                Need(!(File.Exists(current) || Directory.Exists(current)) || (File.GetAttributes(current) & FileAttributes.ReparsePoint) == 0, "linked_font_path_rejected");
        }
        private static string TextHash(string text) => BytesHash(Encoding.UTF8.GetBytes(text));
        private static string FileHash(string path) { using (var stream = File.OpenRead(path)) using (var hash = SHA256.Create()) return Hex(hash.ComputeHash(stream)); }
        private static string BytesHash(byte[] bytes) { using (var hash = SHA256.Create()) return Hex(hash.ComputeHash(bytes)); }
        private static string Hex(byte[] bytes) => BitConverter.ToString(bytes).Replace("-", "").ToLowerInvariant();
        private static void WriteNew(string path, byte[] bytes) { using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write)) stream.Write(bytes, 0, bytes.Length); }
        private static void Need(bool value, string message) { if (!value) throw new InvalidOperationException(message); }
    }
}
