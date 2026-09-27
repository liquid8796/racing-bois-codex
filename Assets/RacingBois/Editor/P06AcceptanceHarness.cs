using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using RacingBois.Client.Application;
using RacingBois.Client.Bootstrap;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace RacingBois.Authoring.Editor
{
    /// <summary>Explicit authoring checks. Merely importing this helper does not execute tests or write receipts.</summary>
    public static class P06AcceptanceHarness
    {
        public const string RaceScene = "Assets/RacingBois/Scenes/Race.unity";
        public const string ArtScene = "Assets/RacingBois/Scenes/ArtBenchmark.unity";
        public const string StressScene = "Assets/RacingBois/Scenes/StressBenchmark.unity";
        private const string Marker = "P06_ACCEPTANCE_GENERATED_BENCHMARK_V1";
        private static readonly string[] ClipNames = { "RB_Ride", "RB_LeanLeft", "RB_LeanRight", "RB_AttackLeft", "RB_AttackRight", "RB_KickLeft", "RB_KickRight", "RB_Hit", "RB_Fall", "RB_Run", "RB_Remount", "RB_Idle" };
        private static readonly FieldInfo WeaponHand = typeof(WeaponGripView).GetField("lastHand", BindingFlags.Instance | BindingFlags.NonPublic);

        [MenuItem("Racing Bois/P06/Create Benchmark Scenes")]
        public static void CreateBenchmarkScenes() { CreateBenchmarkScenes("unbound"); }

        public static string CreateBenchmarkScenes(string runtimeSourceRevision)
        {
            Require(!EditorApplication.isPlayingOrWillChangePlaymode, "Stop Play Mode before creating benchmark scenes.");
            Require(!string.IsNullOrWhiteSpace(runtimeSourceRevision), "Supply a source revision or explicitly use unbound.");
            for (int i = 0; i < SceneManager.sceneCount; i++)
                Require(!SceneManager.GetSceneAt(i).isDirty, "Save all dirty scenes explicitly before copying the Race scene.");
            Require(AssetDatabase.LoadAssetAtPath<SceneAsset>(RaceScene) != null, "Race scene is missing.");
            VerifyOwnedDestination(ArtScene);
            VerifyOwnedDestination(StressScene);
            string before = Hash(RaceScene);
            try
            {
                CreateBenchmark(ArtScene, false, runtimeSourceRevision);
                CreateBenchmark(StressScene, true, runtimeSourceRevision);
            }
            finally { EditorSceneManager.OpenScene(RaceScene, OpenSceneMode.Single); }
            Require(Hash(RaceScene) == before, "Race scene changed while creating benchmark copies.");
            return "Created ArtBenchmark and StressBenchmark; Race remains active and its saved bytes are unchanged. No benchmark was run.";
        }

        private static void VerifyOwnedDestination(string path)
        {
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(path) == null)
            {
                Require(!File.Exists(path), "Destination exists on disk but is not an imported scene; refresh and inspect it before copying: " + path);
                return;
            }
            var existing = SceneManager.GetSceneByPath(path);
            bool opened = !existing.IsValid() || !existing.isLoaded;
            if (opened) existing = EditorSceneManager.OpenScene(path, OpenSceneMode.Additive);
            try { Require(HasMarker(existing), "Refusing to overwrite an unrelated existing scene: " + path); }
            finally { if (opened) EditorSceneManager.CloseScene(existing, true); }
        }

        private static void CreateBenchmark(string destination, bool stress, string revision)
        {
            var source = EditorSceneManager.OpenScene(RaceScene, OpenSceneMode.Single);
            Require(EditorSceneManager.SaveScene(source, destination, true), "Could not save scene copy: " + destination);
            var copy = EditorSceneManager.OpenScene(destination, OpenSceneMode.Single);
            var apps = Components<RaceBootstrap>(copy);
            Require(apps.Length == 1, "Expected exactly one RaceBootstrap in copied scene.");
            var app = apps[0];
            Require(app.Stage != null && app.Stage.Road != null && app.Stage.ViewCamera != null, "Copied scene has missing Stage references.");
            Require(app.AudioBank != null && app.AudioBank.IsComplete, "Copied scene requires a complete audio bank.");
            Require(app.VisualQuality != null && app.VisualQuality.ViewCamera == app.Stage.ViewCamera, "Copied scene requires the existing camera quality controller.");
            Require(app.DustMaterial != null && app.SparkMaterial != null && app.SkidMaterial != null, "Copied scene requires all production effects materials.");
            app.enabled = false;
            foreach (var document in Components<UIDocument>(copy)) document.enabled = false;
            app.Stage.UseExternalEffects = true;
            foreach (var particle in app.Stage.GetComponentsInChildren<ParticleSystem>(true))
                particle.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var runner = app.GetComponent<P06BenchmarkRunner>();
            if (runner == null) runner = app.gameObject.AddComponent<P06BenchmarkRunner>();
            runner.Stage = app.Stage; runner.AudioBank = app.AudioBank;
            runner.VisualQuality = app.VisualQuality; runner.QualityIndex = 1;
            runner.DustMaterial = app.DustMaterial; runner.SparkMaterial = app.SparkMaterial; runner.SkidMaterial = app.SkidMaterial;
            runner.Stress = stress; runner.AutoStart = true; runner.BuildStageOnStart = true;
            runner.EnableAudio = true; runner.ReducedMotion = false; runner.LowQuality = false;
            runner.WarmupSeconds = 8; runner.SampleSeconds = 60; runner.RuntimeSourceRevision = revision;
            runner.OutputPath = "docs/p06/performance/editor-{profile}-{run}.json";
            if (!HasMarker(copy)) SceneManager.MoveGameObjectToScene(new GameObject(Marker), copy);
            EditorSceneManager.MarkSceneDirty(copy);
            Require(EditorSceneManager.SaveScene(copy), "Failed saving benchmark scene: " + destination);
        }

        /// <summary>Call in fresh Play Mode with benchmark AutoStart disabled. This is a functional pool check, not FPS evidence.</summary>
        public static string PlayModePoolSmoke(string runtimeSourceRevision)
        {
            Require(EditorApplication.isPlaying, "Pool smoke requires actual Play Mode.");
            var scene = SceneManager.GetActiveScene();
            Require(IsBenchmark(scene) && HasMarker(scene), "Open one generated benchmark scene first.");
            Require(Components<RaceBootstrap>(scene).All(item => !item.enabled), "RaceBootstrap must remain disabled during the isolated pool smoke.");
            var runner = Components<P06BenchmarkRunner>(scene).Single();
            Require(!runner.Running && !runner.Completed && !runner.AutoStart, "Use a fresh Play lifecycle and set AutoStart=false before entering Play.");
            var stage = runner.Stage;
            Require(stage != null && stage.PoolCreated == 0, "The pool smoke requires a fresh Stage, with no previously acquired actor pool entries.");
            var quality = runner.VisualQuality;
            Require(quality != null && runner.QualityIndex == 1, "Pool smoke expects the configured Medium quality controller.");
            var diagnostics = new List<string>();
            UnityEngine.Application.LogCallback collect = (message, trace, type) =>
            {
                if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert || type == LogType.Warning)
                    diagnostics.Add(type + ": " + message);
            };
            var began = DateTime.UtcNow;
            int initialCreated = 0, afterCreated = 0, reuseBefore = stage.PoolReused;
            const int generations = 24;
            UnityEngine.Application.logMessageReceived += collect;
            try
            {
                quality.Apply(1); stage.Road.SetSceneryQuality(1);
                stage.UseExternalEffects = true; stage.Build();
                Require(WeaponHand != null, "Weapon hand reset inspection could not locate its diagnostic field.");
                for (int generation = 0; generation < generations; generation++)
                {
                    var world = Fixture(generation);
                    Publish(stage, world);
                    AssertDensity(stage);
                    AssertWeaponState(stage, world, true, -1);
                    if (generation == 0) initialCreated = stage.PoolCreated;
                    Require(stage.PoolCreated == initialCreated, "Same-kind identity churn grew the actor pool after initial fill.");
                    foreach (var rider in world.Riders)
                    { rider.Weapon = WeaponKind.Fist; rider.Mode = RiderMode.Riding; rider.AttackSide = 0; }
                    world.Tick++; Publish(stage, world);
                    AssertWeaponState(stage, world, false, -1);

                    // Retire every ID, then reuse the same object kinds with new IDs and a neutral club pose.
                    stage.RenderFrame(null, default(RaceRiderReadModel), false, 1f / 60, true, true);
                    Require(stage.ActiveRiderCount == 0 && stage.ActiveTrafficCount == 0 && stage.ActivePedestrianCount == 0,
                        "Returning to the menu did not retire all actor dictionaries.");
                    foreach (var rider in world.Riders)
                    { rider.Id += 100; rider.Weapon = WeaponKind.Club; }
                    world.Tick++; Publish(stage, world);
                    AssertDensity(stage);
                    AssertWeaponState(stage, world, true, 1);
                    Require(stage.PoolCreated == initialCreated, "Reacquiring retired same-kind actors allocated extra pool entries.");
                    Require(stage.PoolRebalanced == 0, "Same-kind workload unexpectedly rebalanced the pool.");
                }
                afterCreated = stage.PoolCreated;
                Require(stage.PoolReused - reuseBefore >= (generations * 2 - 1) * 34, "Expected repeated real pool reuse was not observed.");
                Require(diagnostics.Count == 0, "Unity emitted diagnostics during smoke: " + string.Join(" | ", diagnostics));
            }
            finally { UnityEngine.Application.logMessageReceived -= collect; }
            var receipt = new PoolReceipt
            {
                status = "passed", startedUtc = began.ToString("O"), completedUtc = DateTime.UtcNow.ToString("O"),
                scope = "Actual Unity Play Mode; deterministic authoring fixture projected through production immutable read models; synchronous functional checks, not performance or network acceptance",
                runtimeSourceRevision = runtimeSourceRevision, scene = scene.path, unityVersion = UnityEngine.Application.unityVersion,
                generations = generations, riders = 16, traffic = 12, pedestrians = 6,
                poolCreatedAfterFirstFill = initialCreated, poolCreatedAtEnd = afterCreated,
                poolReusedDuringRun = stage.PoolReused - reuseBefore, poolRebalanced = stage.PoolRebalanced,
                warningsAndErrorsDuringInvocation = diagnostics.Count,
                checks = new[] { "bounded pool", "same-kind ID churn", "retire before replacement", "menu retirement", "left club visible", "fist hides club", "reacquired club resets to right hand", "finite transforms" },
                sourceFiles = Fingerprints(scene.path)
            };
            return WriteReceipt("pool-smoke", JsonUtility.ToJson(receipt, true));
        }

        private static GameplayWorld Fixture(int generation)
        {
            var world = RaceSimulation.CreateDefault(6061996, 0, 2);
            world.Tick = generation * 10L + 1;
            world.RiderCount = 16; world.TrafficCount = 12; world.PedestrianCount = 6;
            for (int i = 0; i < world.RiderCount; i++)
                world.Riders[i] = new RaceRider
                {
                    Id = 10000 + generation * 300 + i, Kind = i == 15 ? RiderKind.Police : i == 0 ? RiderKind.Player : RiderKind.Opponent,
                    Mode = RiderMode.Attacking, Weapon = WeaponKind.Club, AttackWeapon = WeaponKind.Club, AttackSide = -1, AttackAgeTicks = 8,
                    DistanceMillimeters = 80000 + i * 6500, BikeDistanceMillimeters = 80000 + i * 6500,
                    LateralMillimeters = i % 2 == 0 ? -1100 : 1100, BikeLateralMillimeters = i % 2 == 0 ? -1100 : 1100,
                    SpeedMillimetersPerSecond = 27000, Gear = 3
                };
            for (int i = 0; i < world.TrafficCount; i++)
            {
                var vehicle = world.Traffic[i]; vehicle.Id = 30000 + generation * 300 + i;
                vehicle.Active = true; vehicle.Oncoming = i % 3 == 0; vehicle.DistanceMillimeters = 110000 + i * 10000;
                vehicle.LateralMillimeters = i % 2 == 0 ? -3700 : 3700; vehicle.SpeedMillimetersPerSecond = vehicle.Oncoming ? -18000 : 22000;
                bool van = VehicleDimensions.IsVan(vehicle.Id);
                vehicle.WidthMillimeters = van ? VehicleDimensions.VanWidth : VehicleDimensions.CoupeWidth;
                vehicle.LengthMillimeters = van ? VehicleDimensions.VanLength : VehicleDimensions.CoupeLength;
                vehicle.HeightMillimeters = van ? VehicleDimensions.VanHeight : VehicleDimensions.CoupeHeight;
            }
            for (int i = 0; i < world.PedestrianCount; i++)
            {
                var pedestrian = world.Pedestrians[i]; pedestrian.Id = 60000 + generation * 300 + i;
                pedestrian.DistanceMillimeters = 95000 + i * 14000; pedestrian.LateralMillimeters = i % 2 == 0 ? -7600 : 7600;
                pedestrian.Mode = PedestrianMode.Walking; pedestrian.FacingSide = i % 2 == 0 ? 1 : -1;
            }
            return world;
        }

        private static void Publish(RaceStageView stage, GameplayWorld world)
        {
            stage.RenderFrame(BenchmarkReadModelProjection.World(world, Array.Empty<RaceEvent>()),
                BenchmarkReadModelProjection.Rider(world.Riders[0]), true, 1f / 60, true, true);
        }

        private static void AssertDensity(RaceStageView stage)
        {
            Require(stage.ActiveRiderCount == 16 && stage.ActiveTrafficCount == 12 && stage.ActivePedestrianCount == 6, "Maximum workload did not have all expected active actor views.");
            Require(stage.RiderPoolSize == 16 && stage.TrafficPoolSize == 12 && stage.PedestrianPoolSize == 6, "Pool sizes differ from maximum fixed actor capacities.");
            foreach (var transform in stage.GetComponentsInChildren<Transform>(true))
                Require(IsFinite(transform.position) && IsFinite(transform.localScale), "Non-finite view transform: " + transform.name);
        }

        private static void AssertWeaponState(RaceStageView stage, GameplayWorld world, bool visible, int hand)
        {
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = stage.transform.Find("Rider_" + world.Riders[i].Id);
                Require(rider != null && rider.gameObject.activeInHierarchy, "Missing active rider view.");
                var weapon = rider.GetComponent<WeaponGripView>();
                var club = rider.Find("EquippedClub");
                Require(weapon != null && club != null && club.gameObject.activeSelf == visible, "Club visibility did not follow authoritative equipment.");
                Require((int)WeaponHand.GetValue(weapon) == hand, "Reused weapon retained the previous actor's attack hand.");
            }
        }

        public static string ValidateSceneReferences(string runtimeSourceRevision)
        {
            Require(!EditorApplication.isPlayingOrWillChangePlaymode, "Reference validation requires stopped Play Mode.");
            var scene = SceneManager.GetActiveScene();
            var stage = Components<RaceStageView>(scene).Single();
            var app = Components<RaceBootstrap>(scene).Single();
            Require(stage.Road != null && stage.ViewCamera != null && app.Stage == stage, "Gameplay scene references are incomplete.");
            Require(app.AudioBank != null && app.AudioBank.IsComplete, "Audio bank is incomplete.");
            var audioFields = typeof(RaceAudioBank).GetFields(BindingFlags.Instance | BindingFlags.Public).Where(f => f.FieldType == typeof(AudioClip)).ToArray();
            foreach (var field in audioFields)
            {
                var clip = field.GetValue(app.AudioBank) as AudioClip;
                Require(clip != null && clip.length > 0 && clip.samples > 0, "Invalid audio clip: " + field.Name);
            }
            Require(stage.RiderClips != null && stage.RiderClips.Length == ClipNames.Length, "Expected exactly twelve rider clips.");
            foreach (string expected in ClipNames)
                Require(stage.RiderClips.Count(c => c != null && c.length > 0 && c.name.EndsWith(expected, StringComparison.Ordinal)) == 1, "Missing, empty or duplicated animation: " + expected);
            var prefabs = new[] { stage.MotorcyclePrefab, stage.PoliceMotorcyclePrefab, stage.RiderPrefab, stage.PoliceRiderPrefab, stage.CoupePrefab, stage.VanPrefab, stage.PedestrianPrefab, stage.ClubPrefab };
            var shaders = new HashSet<string>();
            int skins = 0;
            foreach (var prefab in prefabs)
            {
                Require(prefab != null, "An actor prefab reference is missing.");
                foreach (var transform in prefab.GetComponentsInChildren<Transform>(true))
                    Require(GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(transform.gameObject) == 0, "Missing script in " + prefab.name);
                foreach (var renderer in prefab.GetComponentsInChildren<Renderer>(true))
                    foreach (var material in renderer.sharedMaterials)
                    {
                        Require(material != null && material.shader != null && material.shader.isSupported, "Missing or unsupported Editor material on " + prefab.name);
                        shaders.Add(material.shader.name);
                    }
                foreach (var skin in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                {
                    skins++; Require(skin.sharedMesh != null && skin.rootBone != null && skin.bones.Length > 0 && skin.bones.All(b => b != null), "Broken skin references in " + prefab.name);
                    Require(skin.sharedMesh.bindposes.Length == skin.bones.Length, "Skin bindpose/bone count differs in " + prefab.name);
                }
            }
            Require(skins > 0, "No production skinned rider mesh is referenced.");
            return WriteReceipt("scene-references", JsonUtility.ToJson(new ReferenceReceipt
            {
                status = "passed", completedUtc = DateTime.UtcNow.ToString("O"), runtimeSourceRevision = runtimeSourceRevision,
                scope = "Actual saved-scene and imported-asset references in Unity Editor; shader support does not establish browser compilation or visual acceptance",
                scene = scene.path, audioClips = audioFields.Length, riderClips = stage.RiderClips.Length, actorPrefabs = prefabs.Length,
                skinnedMeshRenderers = skins, shaders = shaders.OrderBy(s => s, StringComparer.Ordinal).ToArray(), sourceFiles = Fingerprints(scene.path)
            }, true));
        }

        private static T[] Components<T>(Scene scene) where T : Component => scene.GetRootGameObjects().SelectMany(root => root.GetComponentsInChildren<T>(true)).ToArray();
        private static bool HasMarker(Scene scene) => scene.GetRootGameObjects().Any(root => root.name == Marker);
        private static bool IsBenchmark(Scene scene) => scene.path == ArtScene || scene.path == StressScene;
        private static bool IsFinite(Vector3 value) => !float.IsNaN(value.x) && !float.IsInfinity(value.x) && !float.IsNaN(value.y) && !float.IsInfinity(value.y) && !float.IsNaN(value.z) && !float.IsInfinity(value.z);
        private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
        private static string Hash(string path)
        {
            using (var sha = SHA256.Create()) using (var stream = File.OpenRead(path))
                return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
        private static Fingerprint[] Fingerprints(string scene)
        {
            var paths = new HashSet<string>(AssetDatabase.GetDependencies(scene, true), StringComparer.Ordinal);
            foreach (string path in new[] { "Assets/RacingBois/Editor/P06AcceptanceHarness.cs", "Assets/RacingBois/Client/Presentation/RaceStageView.cs", "Assets/RacingBois/Client/Presentation/WeaponGripView.cs", "Assets/RacingBois/Client/Application/BenchmarkReadModelProjection.cs" }) paths.Add(path);
            return paths.Where(File.Exists).OrderBy(path => path, StringComparer.Ordinal).Select(path => new Fingerprint { path = path, sha256 = Hash(path) }).ToArray();
        }
        private static string WriteReceipt(string kind, string json)
        {
            string directory = Path.GetFullPath(Path.Combine(UnityEngine.Application.dataPath, "../docs/p06/acceptance"));
            Directory.CreateDirectory(directory);
            string path = Path.Combine(directory, kind + "-" + DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffZ") + "-" + Guid.NewGuid().ToString("N").Substring(0, 8) + ".json");
            using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
            using (var writer = new StreamWriter(stream, new System.Text.UTF8Encoding(false))) writer.Write(json + "\n");
            return path;
        }
        [Serializable] private sealed class Fingerprint { public string path, sha256; }
        [Serializable] private sealed class PoolReceipt
        {
            public string status, startedUtc, completedUtc, scope, runtimeSourceRevision, scene, unityVersion;
            public int generations, riders, traffic, pedestrians, poolCreatedAfterFirstFill, poolCreatedAtEnd, poolReusedDuringRun, poolRebalanced, warningsAndErrorsDuringInvocation;
            public string[] checks; public Fingerprint[] sourceFiles;
        }
        [Serializable] private sealed class ReferenceReceipt
        {
            public string status, completedUtc, scope, runtimeSourceRevision, scene;
            public int audioClips, riderClips, actorPrefabs, skinnedMeshRenderers;
            public string[] shaders; public Fingerprint[] sourceFiles;
        }
    }
}
