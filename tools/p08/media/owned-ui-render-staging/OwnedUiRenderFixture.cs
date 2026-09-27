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

namespace RacingBois.Tools.OwnedUi
{
    /// <summary>Root-invoked diagnostic fixture. Persistent copies are retained; Dispose never deletes font assets.</summary>
    public sealed class OwnedUiRenderFixture : IDisposable
    {
        public const string SourceTree = "Assets/RacingBois/UI/Race.uxml";
        public const string SourcePanel = "Assets/RacingBois/Settings/MainPanel.asset";
        private const string OwnedPrefix = "Assets/RacingBois/Diagnostics/OwnedUiReview/";
        private const string CorpusPath = "docs/p08/media/global-copy-character-corpus-20260928.json";
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
            public object protectedFontSnapshot;
            public string[] consumedDependencies;
        }
        public sealed class TextLayout
        {
            public string name, text, fontPath, visibility;
            public float x, y, width, height, opacity;
            public bool elided;
        }
        public UIDocument Document { get; private set; }
        public RenderTexture Target { get; private set; }
        public string AssetRoot { get; private set; }
        private readonly Report report = new Report();
        private readonly Dictionary<string, string> copies = new Dictionary<string, string>(StringComparer.Ordinal);
        private ProtectedUiFonts protectedFonts;
        private string evidenceRoot;
        private PanelSettings panel;
        private PanelTextSettings textSettings;
        private FontAsset defaultFont;
        private VisualTreeAsset tree;
        private GameObject owner;
        private Scene preview;
        private bool disposed, detached;
        private int ticks, lastMutationTick;

        public static OwnedUiRenderFixture Prepare(string runId, int width, int height)
        {
            ProtectedUiFonts.Need(Regex.IsMatch(runId ?? "", "^[a-z0-9][a-z0-9-]{0,47}$"), "invalid_owned_ui_run_id");
            ProtectedUiFonts.Need(!EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling && !EditorApplication.isUpdating, "idle_editor_required");
            ProtectedUiFonts.Need(width >= 640 && width <= 3840 && height >= 360 && height <= 2160, "bounded_ui_render_size_required");
            foreach (var document in Resources.FindObjectsOfTypeAll<UIDocument>())
                ProtectedUiFonts.Need(!document.gameObject.scene.IsValid() || !document.isActiveAndEnabled, "quiet_scene_without_enabled_uidocument_required");
            var result = new OwnedUiRenderFixture();
            try { result.PrepareCore(runId, width, height); return result; }
            catch (Exception error)
            {
                result.report.failure = error.ToString(); result.report.state = "preparation-failed";
                // Asset copies may be incomplete/unvalidated. Never destroy a FontAsset on this failure path.
                result.ReleaseTransient(); result.WritePhase("preparation-failed"); throw;
            }
        }

        private void PrepareCore(string runId, int width, int height)
        {
            AssetRoot = OwnedPrefix + runId; evidenceRoot = FreshProjectDirectory("docs/p08/ui-owned-render/" + runId);
            string backup = FreshProjectDirectory("_local/ui-owned-render-font-backups/" + runId);
            FreshAssetDirectory(AssetRoot);
            ProtectedUiFonts.Need(ProtectedUiFonts.FileHash(CorpusPath) == CorpusHash, "authored_character_corpus_changed");
            var corpus = JsonConvert.DeserializeObject<Corpus>(File.ReadAllText(CorpusPath));
            ProtectedUiFonts.Need(corpus != null && corpus.keys == 925 && corpus.cells == 5550 && corpus.codepoints != null && corpus.codepoints.Length == 248 && corpus.codepoints.Distinct().Count() == 248, "authored_corpus_shape_changed");
            protectedFonts = new ProtectedUiFonts(backup);
            report.protectedFontSnapshot = protectedFonts.Before;
            report.ownedRoot = AssetRoot; report.corpusSha256 = CorpusHash;
            string[] dependencies = AssetDatabase.GetDependencies(new[] { SourceTree, SourcePanel }, true);
            var copyPaths = dependencies.Where(path => path.StartsWith("Assets/", StringComparison.Ordinal)).Distinct().OrderBy(CopyOrder).ThenBy(path => path, StringComparer.Ordinal).ToArray();
            ProtectedUiFonts.Need(ProtectedUiFonts.Paths.All(copyPaths.Contains), "ui_dependency_tree_does_not_bind_both_expected_fonts");
            foreach (string source in copyPaths)
            {
                CanonicalAssetFile(source); CanonicalAssetFile(source + ".meta");
                ProtectedUiFonts.Need(new[] { ".uxml", ".uss", ".tss", ".asset", ".ttf", ".otf" }.Contains(Path.GetExtension(source)), "unsupported_ui_dependency:" + source);
                report.originalInputs[source] = ProtectedUiFonts.FileHash(source); report.originalInputs[source + ".meta"] = ProtectedUiFonts.FileHash(source + ".meta");
                copies.Add(source, AssetRoot + "/Mirror/" + source);
            }
            foreach (var pair in copies)
            {
                EnsureAssetFolders(Path.GetDirectoryName(pair.Value).Replace('\\', '/'));
                ProtectedUiFonts.Need(AssetDatabase.CopyAsset(pair.Key, pair.Value), "owned_asset_copy_failed:" + pair.Key);
                report.copiedPaths.Add(pair.Key, pair.Value);
                protectedFonts.Verify();
            }
            RemapCopiedReferences();
            foreach (string original in ProtectedUiFonts.Paths)
            {
                string path = copies[original]; var font = AssetDatabase.LoadAssetAtPath<FontAsset>(path);
                ValidateFont(font, path, true);
                VerifyOwnedFontDependencies(path); // No original source/fallback may be used by the following native font operations.
                font.name += " OwnedUi " + runId;
                var serialized = new SerializedObject(font); var clear = serialized.FindProperty("m_ClearDynamicDataOnBuild");
                ProtectedUiFonts.Need(clear != null && clear.propertyType == SerializedPropertyType.Boolean, "copied_font_clear_field_missing");
                clear.boolValue = false; serialized.ApplyModifiedPropertiesWithoutUndo();
                font.isMultiAtlasTexturesEnabled = true; font.ReadFontAssetDefinition();
                bool added = font.TryAddCharacters(corpus.codepoints, out uint[] missing, true);
                foreach (var texture in font.atlasTextures)
                    if (texture != null && !EditorUtility.IsPersistent(texture))
                    { ProtectedUiFonts.Need(!protectedFonts.Contains(texture), "original_atlas_must_never_be_reparented"); AssetDatabase.AddObjectToAsset(texture, font); }
                EditorUtility.SetDirty(font); AssetDatabase.SaveAssetIfDirty(font);
                var proof = ValidateFont(font, path, true); proof.corpusAdded = added; proof.missing = missing ?? Array.Empty<uint>(); report.fonts.Add(proof);
                ProtectedUiFonts.Need(added && proof.missing.Length == 0, "owned_font_could_not_add_complete_authored_corpus:" + path);
                protectedFonts.Verify();
            }
            panel = AssetDatabase.LoadAssetAtPath<PanelSettings>(copies[SourcePanel]);
            ProtectedUiFonts.Need(panel != null, "owned_panel_missing");
            textSettings = ScriptableObject.CreateInstance<PanelTextSettings>(); textSettings.name = "OwnedUi TextSettings " + runId;
            defaultFont = AssetDatabase.LoadAssetAtPath<FontAsset>(copies[ProtectedUiFonts.Paths[0]]);
            var textSerialized = new SerializedObject(textSettings); var defaultFontProperty = textSerialized.FindProperty("m_DefaultFontAsset");
            ProtectedUiFonts.Need(defaultFontProperty != null && defaultFontProperty.propertyType == SerializedPropertyType.ObjectReference, "owned_text_settings_default_font_schema_changed");
            defaultFontProperty.objectReferenceValue = defaultFont; textSerialized.ApplyModifiedPropertiesWithoutUndo();
            textSettings.fallbackFontAssets = new List<FontAsset> { defaultFont, AssetDatabase.LoadAssetAtPath<FontAsset>(copies[ProtectedUiFonts.Paths[1]]) };
            textSettings.defaultFontAssetPath = AssetRoot + "/Mirror/Assets/RacingBois/UI/Fonts/";
            AssetDatabase.CreateAsset(textSettings, AssetRoot + "/OwnedPanelTextSettings.asset");
            panel.textSettings = textSettings; EditorUtility.SetDirty(panel); AssetDatabase.SaveAssetIfDirty(panel);
            foreach (string path in copies.Values.Where(path => new[] { ".uss", ".tss", ".uxml" }.Contains(Path.GetExtension(path))))
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
            tree = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(copies[SourceTree]);
            ProtectedUiFonts.Need(tree != null, "owned_uxml_missing");
            VerifyClosure(); VerifyOriginals();
            Target = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { name = "OwnedUi " + runId, hideFlags = HideFlags.HideAndDontSave };
            Target.Create(); var previousTarget = RenderTexture.active;
            try { RenderTexture.active = Target; GL.Clear(true, true, Color.clear); }
            finally { RenderTexture.active = previousTarget; }
            panel.targetTexture = Target;
            preview = EditorSceneManager.NewPreviewScene();
            owner = new GameObject("Owned UI render " + runId); owner.hideFlags = HideFlags.HideAndDontSave; owner.SetActive(false);
            SceneManager.MoveGameObjectToScene(owner, preview);
            Document = owner.AddComponent<UIDocument>(); Document.enabled = false; Document.panelSettings = panel; Document.visualTreeAsset = tree;
            if (Document.rootVisualElement != null) Document.rootVisualElement.style.unityFontDefinition = new StyleFontDefinition(FontDefinition.FromSDFFont(defaultFont));
            report.state = "prepared"; EditorApplication.update += CountTick; WritePhase("prepared");
        }

        public void Attach()
        {
            ProtectedUiFonts.Need(!disposed && !detached && Document != null && !report.attached, "prepared_fixture_required");
            VerifyClosure(); VerifyOriginals();
            owner.SetActive(true); Document.enabled = true;
            ProtectedUiFonts.Need(Document.rootVisualElement != null, "owned_document_root_missing_after_enable");
            Document.rootVisualElement.style.unityFontDefinition = new StyleFontDefinition(FontDefinition.FromSDFFont(defaultFont));
            report.attached = true; MarkChanged();
            VerifyOriginals(); report.state = "attached"; WritePhase("attached");
        }
        public void MarkChanged()
        { ProtectedUiFonts.Need(!disposed, "fixture_disposed"); lastMutationTick = ticks; Document?.rootVisualElement.MarkDirtyRepaint(); EditorApplication.QueuePlayerLoopUpdate(); }
        private void CountTick() { ticks++; if (report.attached) EditorApplication.QueuePlayerLoopUpdate(); }
        public string Snapshot() => JsonConvert.SerializeObject(report, Formatting.Indented);

        public void FocusControl(string name)
        {
            ProtectedUiFonts.Need(report.attached && !disposed && Document.rootVisualElement.panel != null, "attached_panel_required_for_focus");
            var element = Document.rootVisualElement.Q<VisualElement>(name);
            ProtectedUiFonts.Need(element != null && element.focusable && element.enabledInHierarchy && element.worldBound.width > 0 && element.worldBound.height > 0, "focus_target_unavailable");
            element.Focus(); MarkChanged();
        }
        public void SubmitFocused()
        {
            ProtectedUiFonts.Need(report.attached && !disposed, "attached_panel_required_for_submit");
            var focused = Document.rootVisualElement.panel?.focusController.focusedElement as VisualElement;
            ProtectedUiFonts.Need(focused != null && focused.enabledInHierarchy, "focused_target_unavailable");
            using (var input = NavigationSubmitEvent.GetPooled()) focused.SendEvent(input);
            MarkChanged();
        }
        public string CapturePng(string leafName)
        {
            ProtectedUiFonts.Need(report.attached && !disposed && ticks - lastMutationTick >= 2 && Regex.IsMatch(leafName ?? "", "^[a-z0-9][a-z0-9-]{0,80}\\.png$"), "render_frame_barrier_or_name_invalid");
            ProtectedUiFonts.Need(Document.rootVisualElement.panel != null && Document.rootVisualElement.layout.width > 0 && Document.rootVisualElement.layout.height > 0, "owned_panel_not_laid_out");
            VerifyClosure(); VerifyOriginals(); ValidateRenderedFonts();
            string output = Path.Combine(evidenceRoot, leafName); ProtectedUiFonts.Need(!File.Exists(output) && !File.Exists(Path.ChangeExtension(output, ".json")), "fresh_capture_required");
            var previous = RenderTexture.active; Texture2D image = null;
            try
            {
                image = new Texture2D(Target.width, Target.height, TextureFormat.RGBA32, false, true);
                RenderTexture.active = Target; image.ReadPixels(new Rect(0, 0, Target.width, Target.height), 0, 0); image.Apply(false, false);
                ProtectedUiFonts.Need(image.GetRawTextureData<byte>().ToArray().Any(value => value != 0), "owned_render_texture_is_clear");
                ProtectedUiFonts.WriteNew(output, image.EncodeToPNG());
            }
            finally { RenderTexture.active = previous; if (image != null) Object.DestroyImmediate(image); }
            VerifyOriginals();
            var focused = Document.rootVisualElement.panel.focusController.focusedElement as VisualElement;
            var focusedField = focused as TextField ?? focused?.GetFirstAncestorOfType<TextField>();
            var layouts = new List<TextLayout>();
            Document.rootVisualElement.Query<UnityEngine.UIElements.TextElement>().ForEach(element =>
            {
                var bounds = element.worldBound;
                if (element.resolvedStyle.display == DisplayStyle.None || bounds.width <= 0 || bounds.height <= 0 || string.IsNullOrEmpty(element.text)) return;
                var field = element.GetFirstAncestorOfType<TextField>();
                layouts.Add(new TextLayout { name = element.name, text = field != null && field.isPasswordField ? "[masked field]" : element.text,
                    fontPath = AssetDatabase.GetAssetPath(element.resolvedStyle.unityFontDefinition.fontAsset ?? defaultFont),
                    x = bounds.x, y = bounds.y, width = bounds.width, height = bounds.height, elided = element.isElided,
                    visibility = element.resolvedStyle.visibility.ToString(), opacity = element.resolvedStyle.opacity });
            });
            string json = JsonConvert.SerializeObject(new { schema = 1, image = output, sha256 = ProtectedUiFonts.FileHash(output), width = Target.width, height = Target.height,
                editorTicks = ticks, focusedElement = focused?.name ?? "", focusedTextField = focusedField?.name ?? "", textLayout = layouts,
                scope = "Actual owned-panel render and native focus/layout observation; no full-game, input-device, visual-concept or release acceptance.", fixture = report }, Formatting.Indented);
            ProtectedUiFonts.WriteNew(Path.ChangeExtension(output, ".json"), Encoding.UTF8.GetBytes(json)); return json;
        }

        public void Detach()
        {
            if (disposed || detached) return;
            if (Document != null) { Document.enabled = false; Document.visualTreeAsset = null; Document.panelSettings = null; }
            if (owner != null) owner.SetActive(false);
            report.attached = false; detached = true; lastMutationTick = ticks; EditorApplication.QueuePlayerLoopUpdate();
            VerifyOriginals(); report.state = "detached"; WritePhase("detached");
        }
        public void Dispose()
        {
            if (disposed) return;
            ProtectedUiFonts.Need(detached && ticks - lastMutationTick >= 2, "detach_and_wait_before_releasing_uidocument");
            ProtectedUiFonts.Need(Document == null || Document.rootVisualElement == null || Document.rootVisualElement.panel == null, "uidocument_is_still_attached");
            ReleaseTransient(); VerifyOriginals(); report.state = "released-render-objects-copies-retained"; WritePhase("released"); disposed = true;
        }

        private void ReleaseTransient()
        {
            EditorApplication.update -= CountTick;
            if (Document != null) { Document.enabled = false; Document.visualTreeAsset = null; Document.panelSettings = null; }
            if (owner != null) Object.DestroyImmediate(owner);
            if (preview.IsValid()) EditorSceneManager.ClosePreviewScene(preview);
            if (panel != null) panel.targetTexture = null;
            if (Target != null) { Target.Release(); Object.DestroyImmediate(Target); }
            Document = null; Target = null;
        }
        private void VerifyOriginals()
        {
            report.protectedOriginalsPreserved = false;
            try
            {
                protectedFonts.Verify();
                foreach (var input in report.originalInputs) ProtectedUiFonts.Need(ProtectedUiFonts.FileHash(input.Key) == input.Value, "original_ui_dependency_bytes_changed:" + input.Key);
                report.protectedOriginalsPreserved = true;
            }
            catch (Exception error) { report.state = "preservation-failed"; report.failure = error.ToString(); throw; }
        }
        private void VerifyClosure()
        {
            report.dependencyClosurePassed = false;
            string[] dependencies = AssetDatabase.GetDependencies(new[] { copies[SourceTree], copies[SourcePanel], AssetRoot + "/OwnedPanelTextSettings.asset" }, true);
            ProtectedUiFonts.Need(!dependencies.Any(path => ProtectedUiFonts.Paths.Contains(path) || copies.ContainsKey(path)), "owned_ui_closure_references_original_asset");
            ProtectedUiFonts.Need(ProtectedUiFonts.Paths.All(path => dependencies.Contains(copies[path])), "owned_ui_closure_missing_expected_copied_font");
            foreach (string original in ProtectedUiFonts.Paths) ValidateFont(AssetDatabase.LoadAssetAtPath<FontAsset>(copies[original]), copies[original], true);
            report.consumedDependencies = dependencies.OrderBy(value => value, StringComparer.Ordinal).ToArray(); report.dependencyClosurePassed = true;
        }
        private void ValidateRenderedFonts()
        {
            Document.rootVisualElement.Query<UnityEngine.UIElements.TextElement>().ForEach(element =>
            {
                if (element.resolvedStyle.display == DisplayStyle.None || string.IsNullOrEmpty(element.text)) return;
                var definition = element.resolvedStyle.unityFontDefinition;
                if (definition.font != null)
                    ProtectedUiFonts.Need(AssetDatabase.GetAssetPath(definition.font).StartsWith(AssetRoot + "/", StringComparison.Ordinal), "resolved_text_uses_unowned_legacy_font:" + element.name);
                var font = definition.fontAsset ?? defaultFont;
                ProtectedUiFonts.Need(font != null && AssetDatabase.GetAssetPath(font).StartsWith(AssetRoot + "/", StringComparison.Ordinal), "resolved_text_uses_unowned_font:" + element.name);
            });
        }
        private void VerifyOwnedFontDependencies(string path)
        {
            string[] dependencies = AssetDatabase.GetDependencies(path, true);
            ProtectedUiFonts.Need(!dependencies.Any(value => ProtectedUiFonts.Paths.Contains(value) || copies.ContainsKey(value)), "copied_font_dependency_still_references_original_before_prewarm");
            foreach (string dependency in dependencies)
            {
                var main = AssetDatabase.LoadMainAssetAtPath(dependency);
                if (main is FontAsset || main is Font)
                    ProtectedUiFonts.Need(dependency.StartsWith(AssetRoot + "/", StringComparison.Ordinal), "copied_font_has_unowned_font_dependency_before_prewarm");
            }
        }
        private FontEvidence ValidateFont(FontAsset font, string path, bool requireCopiedSource)
        {
            ProtectedUiFonts.Need(font != null && AssetDatabase.GetAssetPath(font) == path && !protectedFonts.Contains(font), "copied_font_identity_invalid");
            var atlas = font.atlasTextures;
            ProtectedUiFonts.Need(atlas != null && atlas.Length > 0 && atlas.All(texture => texture != null && AssetDatabase.IsSubAsset(texture) && AssetDatabase.GetAssetPath(texture) == path && !protectedFonts.Contains(texture)), "copied_atlas_ownership_invalid");
            var material = font.material;
            ProtectedUiFonts.Need(material != null && AssetDatabase.IsSubAsset(material) && AssetDatabase.GetAssetPath(material) == path && material.mainTexture == atlas[0] && !protectedFonts.Contains(material), "copied_material_ownership_invalid");
            var members = AssetDatabase.LoadAllAssetsAtPath(path);
            ProtectedUiFonts.Need(members.Contains(font) && members.Contains(material) && atlas.All(members.Contains) && atlas.Distinct().Count() == atlas.Length &&
                members.OfType<Texture2D>().Count() == atlas.Length && members.All(value => value == font || value is Material || value is Texture2D), "copied_font_subasset_membership_invalid");
            string sourcePath = AssetDatabase.GetAssetPath(font.sourceFontFile);
            if (requireCopiedSource) ProtectedUiFonts.Need(sourcePath.StartsWith(AssetRoot + "/", StringComparison.Ordinal), "copied_font_still_reads_original_ttf");
            return new FontEvidence { path = path, guid = AssetDatabase.AssetPathToGUID(path), fontLocalId = ProtectedUiFonts.LocalId(font), materialLocalId = ProtectedUiFonts.LocalId(material),
                atlasLocalIds = atlas.Select(ProtectedUiFonts.LocalId).ToArray(), sourceFontPath = sourcePath, ownershipPassed = true };
        }
        private void RemapCopiedReferences()
        {
            var objects = new Dictionary<string, Object>(StringComparer.Ordinal); var strings = new Dictionary<string, string>(copies, StringComparer.Ordinal);
            foreach (var pair in copies)
            {
                string oldGuid = AssetDatabase.AssetPathToGUID(pair.Key), newGuid = AssetDatabase.AssetPathToGUID(pair.Value); strings[oldGuid] = newGuid;
                foreach (var value in AssetDatabase.LoadAllAssetsAtPath(pair.Value)) objects[oldGuid + ":" + ProtectedUiFonts.LocalId(value)] = value;
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
        private void WritePhase(string name)
        {
            if (string.IsNullOrEmpty(evidenceRoot)) return;
            Directory.CreateDirectory(evidenceRoot);
            ProtectedUiFonts.WriteNew(Path.Combine(evidenceRoot, name + ".json"), Encoding.UTF8.GetBytes(Snapshot()));
        }
        private static int CopyOrder(string path)
        { string extension = Path.GetExtension(path); return extension == ".ttf" || extension == ".otf" ? 0 : path.EndsWith("SDF.asset", StringComparison.Ordinal) ? 1 : extension == ".uss" ? 2 : extension == ".tss" ? 3 : extension == ".uxml" ? 4 : 5; }
        private static void EnsureAssetFolders(string path)
        {
            string parent = "Assets";
            foreach (string part in path.Split('/').Skip(1))
            { string next = parent + "/" + part; if (!AssetDatabase.IsValidFolder(next)) ProtectedUiFonts.Need(!string.IsNullOrEmpty(AssetDatabase.CreateFolder(parent, part)), "owned_ui_folder_creation_failed"); parent = next; }
        }
        private static string FreshProjectDirectory(string path)
        { string full = ProjectPath(path); ProtectedUiFonts.Need(!Directory.Exists(full) && !File.Exists(full), "fresh_owned_directory_required"); return full; }
        private static void FreshAssetDirectory(string path)
        { ProtectedUiFonts.Need(path.StartsWith(OwnedPrefix, StringComparison.Ordinal), "owned_ui_root_required"); FreshProjectDirectory(path); ProtectedUiFonts.Need(!File.Exists(path + ".meta"), "owned_root_meta_already_exists"); }
        private static void CanonicalAssetFile(string path)
        { ProtectedUiFonts.Need(path.StartsWith("Assets/", StringComparison.Ordinal) && File.Exists(ProjectPath(path)), "canonical_existing_asset_required:" + path); }
        private static string ProjectPath(string path)
        {
            ProtectedUiFonts.Need(!string.IsNullOrEmpty(path) && !Path.IsPathRooted(path) && !path.Contains("\\") && !path.Split('/').Any(part => part == "." || part == ".." || part.Length == 0), "canonical_project_path_required");
            string root = Path.GetFullPath(".").TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar; string full = Path.GetFullPath(path);
            ProtectedUiFonts.Need(full.StartsWith(root, StringComparison.OrdinalIgnoreCase), "path_outside_project");
            for (string current = full; current != null && current.Length >= root.Length - 1; current = Path.GetDirectoryName(current))
                ProtectedUiFonts.Need(!(File.Exists(current) || Directory.Exists(current)) || (File.GetAttributes(current) & FileAttributes.ReparsePoint) == 0, "linked_project_path_rejected");
            return full;
        }
    }
}
