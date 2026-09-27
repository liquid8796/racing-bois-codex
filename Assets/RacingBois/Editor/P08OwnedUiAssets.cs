using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TextCore.Text;
using UnityEngine.UIElements;
using Object = UnityEngine.Object;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Owned UI/font asset preparation extracted from the native-proven R2 fixture; no scene, panel attachment or font destruction.</summary>
    public sealed class P08OwnedUiAssets
    {
        public const string SourceTree = "Assets/RacingBois/UI/Race.uxml";
        public const string SourcePanel = "Assets/RacingBois/Settings/MainPanel.asset";
        private const string OwnedPrefix = "Assets/RacingBois/Diagnostics/P08DesktopBuild/";
        internal const string CorpusPath = "docs/p08/media/global-copy-character-corpus-20260928.json";
        private const string CorpusHash = "2dfb91d19cddd3cbc04de3abc32e8d8c400198851b8c6e44314ebb89d031bacc";
        private sealed class Corpus { public int keys = 0, cells = 0; public uint[] codepoints = Array.Empty<uint>(); }
        public sealed class FontEvidence
        {
            public string path, guid, sourceFontPath;
            public long fontLocalId, materialLocalId;
            public long[] atlasLocalIds;
            public uint[] missing;
            public bool ownershipPassed, corpusAdded;
        }
        public sealed class Report
        {
            public int schema = 1;
            public string state, ownedRoot, corpusSha256, failure = "";
            public bool protectedOriginalsPreserved, dependencyClosurePassed, attached, originalFontsAccepted = false, releaseAccepted = false;
            public Dictionary<string, string> originalInputs = new Dictionary<string, string>();
            public Dictionary<string, string> copiedPaths = new Dictionary<string, string>();
            public List<FontEvidence> fonts = new List<FontEvidence>();
            public object protectedFontSnapshot, ownedFontSnapshot;
            public string[] consumedDependencies;
        }
        public string AssetRoot { get; private set; }
        public string TreePath => copies[SourceTree];
        public string PanelPath => copies[SourcePanel];
        public IReadOnlyDictionary<string, string> OriginalFiles => report.originalInputs;
        private readonly Report report = new Report();
        private readonly Dictionary<string, string> copies = new Dictionary<string, string>(StringComparer.Ordinal);
        private P08ProtectedUiFonts protectedFonts;
        private P08ProtectedUiFonts ownedFonts;
        private string privateEvidenceDirectory;
        private PanelSettings panel;
        private PanelTextSettings textSettings;
        private FontAsset defaultFont;
        private VisualTreeAsset tree;

        public static P08OwnedUiAssets Prepare(string assetRoot, string privateBackupDirectory)
        {
            P08ProtectedUiFonts.Need(Regex.IsMatch(assetRoot ?? "", "^Assets/RacingBois/Diagnostics/P08DesktopBuild/[a-f0-9]{32}/Ui$"), "owned_desktop_ui_root_required");
            string attempt = assetRoot.Split('/')[4];
            P08ProtectedUiFonts.Need(privateBackupDirectory == "_local/p08-desktop/" + attempt + "/original-ui-fonts", "owned_private_font_backup_required");
            P08ProtectedUiFonts.Need(!EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling && !EditorApplication.isUpdating, "idle_editor_required");
            foreach (var document in Resources.FindObjectsOfTypeAll<UIDocument>())
                P08ProtectedUiFonts.Need(!document.gameObject.scene.IsValid() || !document.isActiveAndEnabled, "quiet_scene_without_enabled_uidocument_required");
            var result = new P08OwnedUiAssets();
            try { result.PrepareCore(assetRoot, privateBackupDirectory, attempt); return result; }
            catch (Exception error)
            {
                result.report.state = "preparation-failed"; result.report.failure = error.ToString();
                // Copy/prewarm may already have happened even though the caller has not
                // received this object. Verify its captured originals on this path too.
                try { if (result.protectedFonts != null) result.VerifyOriginals(); }
                catch (Exception preservation) { result.report.failure += "\nOriginal preservation: " + preservation; }
                if (result.privateEvidenceDirectory != null)
                    P08ProtectedUiFonts.WriteNew(Path.Combine(result.privateEvidenceDirectory, "preparation-failed-" + Guid.NewGuid().ToString("N") + ".json"), Encoding.UTF8.GetBytes(result.Snapshot()));
                throw;
            }
        }
        public string Snapshot() => JsonConvert.SerializeObject(report, Formatting.Indented);

        private void PrepareCore(string assetRoot, string privateBackupDirectory, string runId)
        {
            AssetRoot = assetRoot;
            string backup = FreshProjectDirectory(privateBackupDirectory);
            FreshAssetDirectory(AssetRoot);
            P08ProtectedUiFonts.Need(P08ProtectedUiFonts.FileHash(CorpusPath) == CorpusHash, "authored_character_corpus_changed");
            var corpus = JsonConvert.DeserializeObject<Corpus>(File.ReadAllText(CorpusPath));
            P08ProtectedUiFonts.Need(corpus != null && corpus.keys == 925 && corpus.cells == 5550 && corpus.codepoints != null && corpus.codepoints.Length == 248 && corpus.codepoints.Distinct().Count() == 248, "authored_corpus_shape_changed");
            protectedFonts = new P08ProtectedUiFonts(backup);
            privateEvidenceDirectory = backup;
            report.protectedFontSnapshot = protectedFonts.Before;
            report.ownedRoot = AssetRoot; report.corpusSha256 = CorpusHash;
            string[] dependencies = AssetDatabase.GetDependencies(new[] { SourceTree, SourcePanel }, true);
            var copyPaths = dependencies.Where(path => path.StartsWith("Assets/", StringComparison.Ordinal)).Distinct().OrderBy(CopyOrder).ThenBy(path => path, StringComparer.Ordinal).ToArray();
            P08ProtectedUiFonts.Need(P08ProtectedUiFonts.Paths.All(copyPaths.Contains), "ui_dependency_tree_does_not_bind_both_expected_fonts");
            foreach (string source in copyPaths)
            {
                CanonicalAssetFile(source); CanonicalAssetFile(source + ".meta");
                P08ProtectedUiFonts.Need(new[] { ".uxml", ".uss", ".tss", ".asset", ".ttf", ".otf" }.Contains(Path.GetExtension(source)), "unsupported_ui_dependency:" + source);
                report.originalInputs[source] = P08ProtectedUiFonts.FileHash(source); report.originalInputs[source + ".meta"] = P08ProtectedUiFonts.FileHash(source + ".meta");
                copies.Add(source, AssetRoot + "/Mirror/" + source);
            }
            foreach (var pair in copies)
            {
                EnsureAssetFolders(Path.GetDirectoryName(pair.Value).Replace('\\', '/'));
                P08ProtectedUiFonts.Need(AssetDatabase.CopyAsset(pair.Key, pair.Value), "owned_asset_copy_failed:" + pair.Key);
                report.copiedPaths.Add(pair.Key, pair.Value);
                protectedFonts.Verify();
            }
            RemapCopiedReferences();
            foreach (string original in P08ProtectedUiFonts.Paths)
            {
                string path = copies[original]; var font = AssetDatabase.LoadAssetAtPath<FontAsset>(path);
                ValidateFont(font, path, true);
                VerifyOwnedFontDependencies(path); // No original source/fallback may be used by the following native font operations.
                var serialized = new SerializedObject(font); var clear = serialized.FindProperty("m_ClearDynamicDataOnBuild");
                P08ProtectedUiFonts.Need(clear != null && clear.propertyType == SerializedPropertyType.Boolean, "copied_font_clear_field_missing");
                clear.boolValue = false; serialized.ApplyModifiedPropertiesWithoutUndo();
                font.isMultiAtlasTexturesEnabled = true; font.ReadFontAssetDefinition();
                bool added = font.TryAddCharacters(corpus.codepoints, out uint[] missing, true);
                foreach (var texture in font.atlasTextures)
                    if (texture != null && !EditorUtility.IsPersistent(texture))
                    { P08ProtectedUiFonts.Need(!protectedFonts.Contains(texture), "original_atlas_must_never_be_reparented"); AssetDatabase.AddObjectToAsset(texture, font); }
                EditorUtility.SetDirty(font); AssetDatabase.SaveAssetIfDirty(font);
                var proof = ValidateFont(font, path, true); proof.corpusAdded = added; proof.missing = missing ?? Array.Empty<uint>(); report.fonts.Add(proof);
                P08ProtectedUiFonts.Need(added && proof.missing.Length == 0, "owned_font_could_not_add_complete_authored_corpus:" + path);
                protectedFonts.Verify();
            }
            panel = AssetDatabase.LoadAssetAtPath<PanelSettings>(copies[SourcePanel]);
            P08ProtectedUiFonts.Need(panel != null, "owned_panel_missing");
            textSettings = ScriptableObject.CreateInstance<PanelTextSettings>(); textSettings.name = "OwnedUi TextSettings " + runId;
            defaultFont = AssetDatabase.LoadAssetAtPath<FontAsset>(copies[P08ProtectedUiFonts.Paths[0]]);
            var textSerialized = new SerializedObject(textSettings); var defaultFontProperty = textSerialized.FindProperty("m_DefaultFontAsset");
            P08ProtectedUiFonts.Need(defaultFontProperty != null && defaultFontProperty.propertyType == SerializedPropertyType.ObjectReference, "owned_text_settings_default_font_schema_changed");
            defaultFontProperty.objectReferenceValue = defaultFont; textSerialized.ApplyModifiedPropertiesWithoutUndo();
            textSettings.fallbackFontAssets = new List<FontAsset> { defaultFont, AssetDatabase.LoadAssetAtPath<FontAsset>(copies[P08ProtectedUiFonts.Paths[1]]) };
            textSettings.defaultFontAssetPath = AssetRoot + "/Mirror/Assets/RacingBois/UI/Fonts/";
            AssetDatabase.CreateAsset(textSettings, AssetRoot + "/OwnedPanelTextSettings.asset");
            panel.textSettings = textSettings; EditorUtility.SetDirty(panel); AssetDatabase.SaveAssetIfDirty(panel);
            foreach (string path in copies.Values.Where(path => new[] { ".uss", ".tss", ".uxml" }.Contains(Path.GetExtension(path))))
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
            tree = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(copies[SourceTree]);
            P08ProtectedUiFonts.Need(tree != null, "owned_uxml_missing");
            VerifyClosure(); VerifyOriginals();
            ownedFonts = new P08ProtectedUiFonts(null, P08ProtectedUiFonts.Paths.Select(path => copies[path]));
            report.ownedFontSnapshot = ownedFonts.Before;
            report.state = "prepared-assets-only";
        }

        public void VerifyOriginals()
        {
            report.protectedOriginalsPreserved = false;
            try
            {
                protectedFonts.Verify();
                VerifySourceFiles();
                report.protectedOriginalsPreserved = true;
            }
            catch (Exception error) { report.state = "preservation-failed"; report.failure = error.ToString(); throw; }
        }
        public void VerifySourceFiles()
        {
            foreach (var input in report.originalInputs)
                P08ProtectedUiFonts.Need(P08ProtectedUiFonts.FileHash(input.Key) == input.Value, "original_ui_dependency_bytes_changed:" + input.Key);
        }
        public void VerifyOwnedFonts()
        {
            P08ProtectedUiFonts.Need(ownedFonts != null, "owned_font_snapshot_missing");
            ownedFonts.Verify();
        }
        public void VerifyClosure()
        {
            report.dependencyClosurePassed = false;
            string[] dependencies = AssetDatabase.GetDependencies(new[] { copies[SourceTree], copies[SourcePanel], AssetRoot + "/OwnedPanelTextSettings.asset" }, true);
            P08ProtectedUiFonts.Need(!dependencies.Any(path => P08ProtectedUiFonts.Paths.Contains(path) || copies.ContainsKey(path)), "owned_ui_closure_references_original_asset");
            P08ProtectedUiFonts.Need(P08ProtectedUiFonts.Paths.All(path => dependencies.Contains(copies[path])), "owned_ui_closure_missing_expected_copied_font");
            foreach (string original in P08ProtectedUiFonts.Paths) ValidateFont(AssetDatabase.LoadAssetAtPath<FontAsset>(copies[original]), copies[original], true);
            report.consumedDependencies = dependencies.OrderBy(value => value, StringComparer.Ordinal).ToArray(); report.dependencyClosurePassed = true;
        }
        private void VerifyOwnedFontDependencies(string path)
        {
            string[] dependencies = AssetDatabase.GetDependencies(path, true);
            P08ProtectedUiFonts.Need(!dependencies.Any(value => P08ProtectedUiFonts.Paths.Contains(value) || copies.ContainsKey(value)), "copied_font_dependency_still_references_original_before_prewarm");
            foreach (string dependency in dependencies)
            {
                var main = AssetDatabase.LoadMainAssetAtPath(dependency);
                if (main is FontAsset || main is Font)
                    P08ProtectedUiFonts.Need(dependency.StartsWith(AssetRoot + "/", StringComparison.Ordinal), "copied_font_has_unowned_font_dependency_before_prewarm");
            }
        }
        private FontEvidence ValidateFont(FontAsset font, string path, bool requireCopiedSource)
        {
            P08ProtectedUiFonts.Need(font != null && AssetDatabase.GetAssetPath(font) == path && !protectedFonts.Contains(font), "copied_font_identity_invalid");
            var atlas = font.atlasTextures;
            P08ProtectedUiFonts.Need(atlas != null && atlas.Length > 0 && atlas.All(texture => texture != null && AssetDatabase.IsSubAsset(texture) && AssetDatabase.GetAssetPath(texture) == path && !protectedFonts.Contains(texture)), "copied_atlas_ownership_invalid");
            var material = font.material;
            P08ProtectedUiFonts.Need(material != null && AssetDatabase.IsSubAsset(material) && AssetDatabase.GetAssetPath(material) == path && material.mainTexture == atlas[0] && !protectedFonts.Contains(material), "copied_material_ownership_invalid");
            var members = AssetDatabase.LoadAllAssetsAtPath(path);
            P08ProtectedUiFonts.Need(members.Contains(font) && members.Contains(material) && atlas.All(members.Contains) && atlas.Distinct().Count() == atlas.Length &&
                members.OfType<Texture2D>().Count() == atlas.Length && members.All(value => value == font || value is Material || value is Texture2D), "copied_font_subasset_membership_invalid");
            string sourcePath = AssetDatabase.GetAssetPath(font.sourceFontFile);
            if (requireCopiedSource)
            {
                string originalPath = copies.Single(pair => pair.Value == path).Key;
                var original = AssetDatabase.LoadAssetAtPath<FontAsset>(originalPath);
                string originalSource = original == null ? "" : AssetDatabase.GetAssetPath(original.sourceFontFile);
                P08ProtectedUiFonts.Need(copies.TryGetValue(originalSource, out string expectedSource) && sourcePath == expectedSource &&
                    sourcePath.StartsWith(AssetRoot + "/", StringComparison.Ordinal), "copied_font_source_does_not_match_original_ttf_mapping");
            }
            return new FontEvidence { path = path, guid = AssetDatabase.AssetPathToGUID(path), fontLocalId = P08ProtectedUiFonts.LocalId(font), materialLocalId = P08ProtectedUiFonts.LocalId(material),
                atlasLocalIds = atlas.Select(P08ProtectedUiFonts.LocalId).ToArray(), sourceFontPath = sourcePath, ownershipPassed = true };
        }
        private void RemapCopiedReferences()
        {
            var objects = new Dictionary<string, Object>(StringComparer.Ordinal); var strings = new Dictionary<string, string>(copies, StringComparer.Ordinal);
            foreach (var pair in copies)
            {
                string oldGuid = AssetDatabase.AssetPathToGUID(pair.Key), newGuid = AssetDatabase.AssetPathToGUID(pair.Value); strings[oldGuid] = newGuid;
                foreach (var value in AssetDatabase.LoadAllAssetsAtPath(pair.Value)) objects[oldGuid + ":" + P08ProtectedUiFonts.LocalId(value)] = value;
            }
            foreach (string path in copies.Values)
                foreach (var value in AssetDatabase.LoadAllAssetsAtPath(path))
                {
                    // Relative stylesheet URLs are reimported after the mirrored tree is complete.
                    // Skip native TTF buffers, texture pixels and imported UI arrays; they contain no
                    // authored font references that this scoped remapper needs to rewrite.
                    if (!(value is FontAsset) && !(value is PanelSettings) && !(value is Material)) continue;
                    var serialized = new SerializedObject(value); var property = serialized.GetIterator(); bool changed = false, enterChildren = true;
                    while (property.Next(enterChildren))
                    {
                        enterChildren = property.propertyPath != "m_GlyphTable" && property.propertyPath != "m_CharacterTable" && property.propertyPath != "m_FontFeatureTable";
                        if (property.propertyType == SerializedPropertyType.ObjectReference && property.objectReferenceValue != null &&
                            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(property.objectReferenceValue, out string guid, out long id) && objects.TryGetValue(guid + ":" + id, out var replacement))
                        { property.objectReferenceValue = replacement; changed = true; }
                        else if (property.propertyType == SerializedPropertyType.String && strings.TryGetValue(property.stringValue, out string replacementText))
                        { property.stringValue = replacementText; changed = true; }
                    }
                    if (changed) { serialized.ApplyModifiedPropertiesWithoutUndo(); EditorUtility.SetDirty(value); AssetDatabase.SaveAssetIfDirty(value); }
                }
        }
        private static int CopyOrder(string path)
        { string extension = Path.GetExtension(path); return extension == ".ttf" || extension == ".otf" ? 0 : path.EndsWith("SDF.asset", StringComparison.Ordinal) ? 1 : extension == ".uss" ? 2 : extension == ".tss" ? 3 : extension == ".uxml" ? 4 : 5; }
        private static void EnsureAssetFolders(string path)
        {
            string parent = "Assets";
            foreach (string part in path.Split('/').Skip(1))
            { string next = parent + "/" + part; if (!AssetDatabase.IsValidFolder(next)) P08ProtectedUiFonts.Need(!string.IsNullOrEmpty(AssetDatabase.CreateFolder(parent, part)), "owned_ui_folder_creation_failed"); parent = next; }
        }
        private static string FreshProjectDirectory(string path)
        { string full = ProjectPath(path); P08ProtectedUiFonts.Need(!Directory.Exists(full) && !File.Exists(full), "fresh_owned_directory_required"); return full; }
        private static void FreshAssetDirectory(string path)
        { P08ProtectedUiFonts.Need(path.StartsWith(OwnedPrefix, StringComparison.Ordinal), "owned_ui_root_required"); FreshProjectDirectory(path); P08ProtectedUiFonts.Need(!File.Exists(path + ".meta"), "owned_root_meta_already_exists"); }
        private static void CanonicalAssetFile(string path)
        { P08ProtectedUiFonts.Need(path.StartsWith("Assets/", StringComparison.Ordinal) && File.Exists(ProjectPath(path)), "canonical_existing_asset_required:" + path); }
        private static string ProjectPath(string path)
        {
            P08ProtectedUiFonts.Need(!string.IsNullOrEmpty(path) && !Path.IsPathRooted(path) && !path.Contains("\\") && !path.Split('/').Any(part => part == "." || part == ".." || part.Length == 0), "canonical_project_path_required");
            string root = Path.GetFullPath(".").TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar; string full = Path.GetFullPath(path);
            P08ProtectedUiFonts.Need(full.StartsWith(root, StringComparison.OrdinalIgnoreCase), "path_outside_project");
            for (string current = full; current != null && current.Length >= root.Length - 1; current = Path.GetDirectoryName(current))
                P08ProtectedUiFonts.Need(!(File.Exists(current) || Directory.Exists(current)) || (File.GetAttributes(current) & FileAttributes.ReparsePoint) == 0, "linked_project_path_rejected");
            return full;
        }
    }
}
