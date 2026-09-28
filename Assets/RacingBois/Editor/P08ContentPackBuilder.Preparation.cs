using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using UnityEditor;
using UnityEngine;

namespace RacingBois.Authoring.Editor
{
    public static partial class P08ContentPackBuilder
    {
        [Serializable] private sealed class PreparationCheck
        { public string input; public bool passed; public string error; }
        [Serializable] private sealed class PreparationReport
        {
            public int schema = 1;
            public bool passed;
            public string scope = "Read-only preparation prerequisites; no art acceptance, composition, bundle or player build inferred.";
            public PreparationCheck[] checks;
        }

        /// <summary>Checks the entire shared pack before any preparation entry point creates assets or changes importers.</summary>
        public static string InspectPreparation() => JsonUtility.ToJson(CheckPreparation(), true);

        private static void RunPreparation(Action compose)
        {
            var drafts = new NativeBuildDirtyAssetGuard();
            try
            {
                var report = CheckPreparation();
                if (!report.passed)
                    throw new InvalidOperationException("content_preparation_prerequisites:" + string.Join("; ", report.checks.Where(x => !x.passed).Select(x => x.input + ": " + x.error)));
                compose();
            }
            finally { drafts.VerifyUnchanged(); }
        }

        private static PreparationReport CheckPreparation()
        {
            var checks = new List<PreparationCheck>();
            var inputPaths = new HashSet<string>(StringComparer.Ordinal);
            Action<string, Action> check = (name, inspect) =>
            {
                var row = new PreparationCheck { input = name };
                try { inspect(); row.passed = true; }
                catch (Exception error) { row.error = error.Message; }
                checks.Add(row);
            };
            GoldenProductionBindings bindings = null;
            string[] names = null;
            check("production-bindings", () =>
            {
                names = PackPrefabNames().Distinct(StringComparer.Ordinal).ToArray();
                bindings = GoldenProductionBindings.Load();
                bindings.ValidateConsumed(names);
            });
            if (bindings != null && names != null)
                foreach (string name in names)
                    check(name, () =>
                    {
                        var prefab = bindings.Resolve(name, Prefab);
                        if (!PrefabUtility.IsPartOfPrefabAsset(prefab)) throw new InvalidOperationException("Persistent prefab required.");
                        bindings.ValidateBound(name, prefab);
                        inputPaths.Add(AssetDatabase.GetAssetPath(prefab));
                    });

            string[] surfaces = { "Assets/RacingBois/Materials/P06/RB_P06_Asphalt.mat", "Assets/RacingBois/Materials/P06/RB_P06_Gravel.mat",
                "Assets/RacingBois/Materials/RacePaint.mat", "Assets/RacingBois/Materials/RaceYellow.mat", "Assets/RacingBois/Materials/P06/RB_P06_Roadside.mat" };
            foreach (string path in surfaces)
                check(path, () => { Require<Material>(path); inputPaths.Add(path); });
            foreach (string shader in new[] { "Universal Render Pipeline/Lit", "Skybox/Procedural" })
                check(shader, () => { if (Shader.Find(shader) == null) throw new InvalidOperationException("Required shader missing."); });

            const string rider = "Assets/RacingBois/Art/P06/Hero/RB_P06_Rider.fbx";
            check(rider, () =>
            {
                var clips = AssetDatabase.LoadAllAssetsAtPath(rider).OfType<AnimationClip>().Where(c => P06HeroAssetBuilder.ClipNames.Contains(c.name)).ToArray();
                if (clips.Length != 12 || clips.Select(x => x.name).Distinct().Count() != 12 || P06HeroAssetBuilder.ClipNames.Any(name => !clips.Any(x => x.name == name)))
                    throw new InvalidOperationException("All 12 unique rider clips are required.");
                inputPaths.Add(rider);
            });
            const string bank = "Assets/RacingBois/Audio/P06/RB_P06_AudioBank.asset";
            check(bank, () => { if (!Require<RaceAudioBank>(bank).HasGameplayEffects) throw new InvalidOperationException("Utility audio bank incomplete."); inputPaths.Add(bank); });
            for (int character = 0; character < CharacterCatalog.Count; character++)
                for (int state = 0; state < 3; state++)
                {
                    string path = "Assets/RacingBois/Art/P08/Portraits/RB_P08_Portrait_" + character.ToString("D2") + "_" + state.ToString("D2") + ".png";
                    check(path, () =>
                    {
                        if (!File.Exists(path) || !(AssetImporter.GetAtPath(path) is TextureImporter)) throw new InvalidOperationException("Portrait texture/importer missing.");
                        inputPaths.Add(path);
                    });
                }
            AudioEntry[] audio = null;
            check("audio-delivery", () => { audio = ReadAudio(); ValidateAudioInventory(audio); });
            if (audio != null)
                foreach (var entry in audio)
                    check(entry.oggPath, () =>
                    {
                        P08DesktopCompiledSources.Inside(entry.oggPath);
                        if (Digest(entry.oggPath) != entry.oggSha256) throw new InvalidOperationException("Audio delivery SHA256 differs.");
                        if (entry.category == "sfx")
                        {
                            if (!(AssetImporter.GetAtPath(entry.oggPath) is AudioImporter)) throw new InvalidOperationException("Sound importer missing.");
                            Require<AudioClip>(entry.oggPath);
                            inputPaths.Add(entry.oggPath);
                        }
                    });
            foreach (string path in RouteOutputs().Concat(ActorOutputs()))
                check(path, () => CheckPreparedOutput(path));
            check("clean-input-dependencies", () =>
            {
                var dependencies = AssetDatabase.GetDependencies(inputPaths.ToArray(), true);
                new NativeBuildDirtyAssetGuard().RejectDirtyDependencies(dependencies);
                foreach (string path in dependencies)
                {
                    var importer = AssetImporter.GetAtPath(path);
                    if (importer != null && EditorUtility.IsDirty(importer)) throw new InvalidOperationException("Unsaved importer: " + path);
                }
            });
            return new PreparationReport { passed = checks.All(x => x.passed), checks = checks.ToArray() };
        }

        private static void ValidateAudioInventory(AudioEntry[] audio)
        {
            if (audio.Any(x => string.IsNullOrWhiteSpace(x.id) || x.id.Length > 64 || (x.category != "sfx" && x.category != "music")) ||
                audio.Select(x => x.id).Distinct(StringComparer.Ordinal).Count() != 97 || audio.Select(x => x.oggPath).Distinct(StringComparer.OrdinalIgnoreCase).Count() != 97)
                throw new InvalidOperationException("Audio IDs, categories or distinct paths are invalid.");
            var sfx = audio.Where(x => x.category == "sfx").ToArray();
            if (sfx.Length != 72 || audio.Count(x => x.category == "music") != 25 ||
                P08AudioRoles.All.Any(role => !sfx.Any(x => x.id == role.Id)) ||
                RouteMusic.Any(id => !audio.Any(x => x.category == "music" && x.id == id)))
                throw new InvalidOperationException("Functional audio or route music inventory incomplete.");
        }

        private static IEnumerable<string> ActorOutputs() => new[] { Root + "Actors.asset", Root + "Library.asset", Root + "AudioBank.asset" };
        private static IEnumerable<string> RouteOutputs()
        {
            for (int course = 0; course < 5; course++)
            {
                yield return Root + "Route-" + course + ".asset";
                foreach (string surface in new[] { "Asphalt", "Gravel", "Landscape" }) yield return Materials + "Route-" + course + "-" + surface + ".mat";
                yield return Materials + "Water-" + course + ".mat";
                yield return Materials + "Sky-" + course + ".mat";
            }
        }
        private static void CheckPreparedOutput(string path)
        {
            P08DesktopCompiledSources.Inside(path);
            if (!File.Exists(path)) return;
            Type expected = path.EndsWith(".mat", StringComparison.Ordinal) ? typeof(Material) :
                path == Root + "Actors.asset" ? typeof(P08ActorContent) : path == Root + "Library.asset" ? typeof(P08ContentLibrary) :
                path == Root + "AudioBank.asset" ? typeof(RaceAudioBank) : typeof(P08RouteContent);
            if (AssetDatabase.LoadMainAssetAtPath(path)?.GetType() != expected) throw new InvalidOperationException("Existing output type differs.");
            var importer = AssetImporter.GetAtPath(path);
            if (AssetDatabase.LoadAllAssetsAtPath(path).Any(EditorUtility.IsDirty) || (importer != null && EditorUtility.IsDirty(importer)))
                throw new InvalidOperationException("Existing output contains unsaved authoring data.");
        }
        private static void SavePrepared(IEnumerable<string> paths)
        {
            foreach (string path in paths) AssetDatabase.SaveAssetIfDirty(Require<UnityEngine.Object>(path));
        }
    }
}
