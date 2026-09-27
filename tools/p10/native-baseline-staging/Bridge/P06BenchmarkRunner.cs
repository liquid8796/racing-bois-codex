using System;
using System.Collections.Generic;
using System.IO;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;
using RacingBois.Simulation;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityApplication = UnityEngine.Application;

namespace RacingBois.Client.Bootstrap
{
    /// <summary>Editor workload measurement, sharing the real simulation, projection and gameplay chase-camera view.</summary>
    public sealed class P06BenchmarkRunner : MonoBehaviour
    {
        public RaceStageView Stage;
        public RaceVisualQuality VisualQuality;
        [Range(0, 2)] public int QualityIndex = 1;
        public RaceAudioBank AudioBank;
        public Material DustMaterial, SparkMaterial, SkidMaterial;
        public bool Stress, AutoStart = true, EnableAudio = true, ReducedMotion, LowQuality;
        public bool BuildStageOnStart = true;
        public int Seed = 6061996;
        public float WarmupSeconds = 8, SampleSeconds = 60;
        public string RuntimeSourceRevision = "unbound";
        public string OutputPath = "docs/p06/performance/editor-{profile}-{run}.json";
        public bool Running { get; private set; }
        public bool Completed { get; private set; }
        public float Progress { get; private set; }
        public string LastReceiptJson { get; private set; } = "";
        public string LastReceiptPath { get; private set; } = "";
        public string Error { get; private set; } = "";
        public long CurrentTick => world == null ? 0 : world.Tick;
        public bool IsMeasuring => measuring;
        public double MeasurementStarted => measurementBegan;
        public int CurrentCycle => cycles;
        public long DiagnosticMeasuredTicks => measuredTicks;
        private bool nativeDiagnostic;
        private bool nativeTimingApplied;
        private int originalDiagnosticVSync;
        /// <summary>Explicit bounded Windows diagnostic; ordinary benchmark Begin remains 60-120 seconds.</summary>
        public void BeginNativeDiagnostic()
        {
            if (UnityApplication.isEditor || UnityApplication.platform != RuntimePlatform.WindowsPlayer || Running || Completed)
                throw new InvalidOperationException("A fresh native Windows diagnostic instance is required.");
            nativeDiagnostic = true;
            frames = new float[1000000];
            Begin();
        }
        public void RestoreNativeDiagnosticTiming()
        {
            if (!nativeTimingApplied) return;
            UnityApplication.targetFrameRate = originalTargetFrameRate;
            QualitySettings.vSyncCount = originalDiagnosticVSync;
            nativeTimingApplied = false;
        }

        private const int FrameCapacity = 65536;
        private float[] frames = new float[FrameCapacity];
        private readonly List<RaceEvent> events = new List<RaceEvent>(128);
        private readonly FrameTiming[] timings = new FrameTiming[1];
        private readonly CounterSample gc = new CounterSample(), draws = new CounterSample(), batches = new CounterSample();
        private readonly CounterSample setPass = new CounterSample(), triangles = new CounterSample(), vertices = new CounterSample();
        private readonly CounterSample unityMemory = new CounterSample(), managedMemory = new CounterSample();
        private readonly CounterSample cpuFrame = new CounterSample(), gpuFrame = new CounterSample(), updateCpu = new CounterSample();
        private readonly CounterSample riderCounts = new CounterSample(), trafficCounts = new CounterSample(), pedestrianCounts = new CounterSample();
        private ProfilerRecorder gcRecorder, drawRecorder, batchRecorder, setPassRecorder, triangleRecorder, vertexRecorder;
        private RaceAudio audioView;
        private RaceEffectsView effects;
        private GameplayWorld world;
        private RaceWorldReadModel projected;
        private RaceRiderReadModel local;
        private Receipt receipt;
        private double previousTime, warmupBegan, measurementBegan, accumulator;
        private long measuredTicks, droppedTicks;
        private int frameCount, cycles, fixtureRespawns, measuredAttacks, measuredHits, measuredCrashes;
        private bool measuring, capacityExceeded, built;
        private int originalTargetFrameRate;
        private UniversalRenderPipelineAsset appliedPipeline;

        private void Start() { if (AutoStart) Begin(); }

        public void Begin()
        {
            if (Running || Completed) return;
            if (!UnityApplication.isPlaying) { Error = "Benchmark quality and workload require actual Play Mode."; return; }
            if (receipt != null) { Error = "Start a fresh Play Mode run after an interrupted benchmark."; return; }
            if (Stage == null || Stage.Road == null || Stage.ViewCamera == null || AudioBank == null || !AudioBank.IsComplete || DustMaterial == null || SparkMaterial == null || SkidMaterial == null)
            { Error = "Benchmark requires Stage, a complete audio bank, and all three effect materials."; return; }
            var bootstrap = GetComponent<RaceBootstrap>();
            if (bootstrap != null && bootstrap.enabled)
            { Error = "Disable RaceBootstrap before starting this authoring benchmark."; return; }
            if (VisualQuality == null || VisualQuality.ViewCamera != Stage.ViewCamera || QualityIndex < 0 || QualityIndex > 2)
            { Error = "Benchmark requires its existing camera quality controller and QualityIndex 0, 1 or 2."; return; }
            VisualQuality.Apply(QualityIndex);
            Stage.Road.SetSceneryQuality(QualityIndex);
            appliedPipeline = GraphicsSettings.defaultRenderPipeline as UniversalRenderPipelineAsset;
            float expectedScale = QualityIndex == 0 ? .78f : 1f;
            if (appliedPipeline == null || VisualQuality.Index != QualityIndex || !Mathf.Approximately(appliedPipeline.renderScale, expectedScale))
            { Error = "Runtime URP quality did not match the requested benchmark tier and render scale."; return; }
            LowQuality = QualityIndex == 0;
            WarmupSeconds = Mathf.Clamp(WarmupSeconds, 5, 30);
            SampleSeconds = nativeDiagnostic ? 600 : Mathf.Clamp(SampleSeconds, 60, 120);
            originalTargetFrameRate = UnityApplication.targetFrameRate;
            UnityApplication.targetFrameRate = nativeDiagnostic ? -1 : 60;
            if (nativeDiagnostic) { originalDiagnosticVSync = QualitySettings.vSyncCount; nativeTimingApplied = true; QualitySettings.vSyncCount = 0; }
            if (BuildStageOnStart && !built) { Stage.Build(); built = true; }
            audioView = gameObject.AddComponent<RaceAudio>(); audioView.Initialize(AudioBank);
#if UNITY_EDITOR
            audioView.UnlockFromUserGesture();
#endif
            effects = gameObject.AddComponent<RaceEffectsView>();
            effects.Initialize(Stage.Road, DustMaterial, SparkMaterial, SkidMaterial); effects.SetQuality(LowQuality);
            gcRecorder = StartRecorder(ProfilerCategory.Memory, "GC Allocated In Frame");
            drawRecorder = StartRecorder(ProfilerCategory.Render, "Draw Calls Count");
            batchRecorder = StartRecorder(ProfilerCategory.Render, "Batches Count");
            setPassRecorder = StartRecorder(ProfilerCategory.Render, "SetPass Calls Count");
            triangleRecorder = StartRecorder(ProfilerCategory.Render, "Triangles Count");
            vertexRecorder = StartRecorder(ProfilerCategory.Render, "Vertices Count");
            receipt = new Receipt
            {
                runId = DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffZ"), profile = Stress ? "stress" : "standard",
                runtimeSourceRevision = RuntimeSourceRevision, seed = Seed, warmupSeconds = WarmupSeconds, requestedSampleSeconds = SampleSeconds,
                editor = UnityApplication.isEditor, scope = UnityApplication.isEditor ? "Unity Editor Game View; global Editor counters" : "Player authoring benchmark",
                unityVersion = UnityApplication.unityVersion, productVersion = UnityApplication.version,
                operatingSystem = SystemInfo.operatingSystem, processor = SystemInfo.processorType, graphicsDevice = SystemInfo.graphicsDeviceName,
                graphicsApi = SystemInfo.graphicsDeviceType.ToString(), deviceMemoryMiB = SystemInfo.systemMemorySize,
                graphicsMemoryMiB = SystemInfo.graphicsMemorySize, qualityLevel = QualitySettings.names[QualitySettings.GetQualityLevel()],
                graphicsQualityIndex = VisualQuality.Index, renderScale = appliedPipeline.renderScale,
                reducedMotion = ReducedMotion, lowEffectsQuality = LowQuality, audioEnabled = EnableAudio,
                targetFrameRate = UnityApplication.targetFrameRate, vSyncCount = QualitySettings.vSyncCount,
                expectedRiders = Stress ? 16 : 8, expectedTraffic = Stress ? 12 : -1, expectedPedestrians = Stress ? 6 : -1,
                workload = Stress ? "8 scripted players + 7 AI + police; maintained 12 traffic / 6 pedestrians; benchmark fixture recycling" : "1 scripted player + 6 AI + police; normal gameplay traffic and pedestrian spawn flow",
                limits = "This is not a browser, networking, full UI, or 16-online-player benchmark. Counters can include Editor/Scene View overhead. Fixture recycle costs are included. No unavailable counter is reported as zero."
            };
            CreateWorld();
            previousTime = warmupBegan = Time.realtimeSinceStartupAsDouble;
            Running = true;
        }

        private static ProfilerRecorder StartRecorder(ProfilerCategory category, string name)
        {
            try { return ProfilerRecorder.StartNew(category, name, 1); }
            catch (Exception) { return default; }
        }

        private void CreateWorld()
        {
            world = RaceSimulation.CreateDefault(Seed + cycles * 17, 6, 2);
            int playerCount = Stress ? 8 : 1;
            for (int i = 1; i <= playerCount; i++) RaceSimulation.AddPlayer(world, i);
            if (Stress)
            {
                world.Riders[world.RiderCount++] = new RaceRider { Id = 1007, Kind = RiderKind.Opponent, Weapon = WeaponKind.Club };
                Array.Sort(world.Riders, 0, world.RiderCount, RiderOrder.Instance);
            }
            long start = 80000 + cycles % 3 * 500000L;
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = world.Riders[i];
                long distance = start + (i / 2) * 7500;
                int lateral = i % 2 == 0 ? -700 : 700;
                if (rider.Kind == RiderKind.Police) { distance = start - 20000; lateral = 4500; }
                SetSpawn(rider, distance, lateral);
            }
            if (Stress)
            {
                world.TrafficCount = GameplayRules.MaxTraffic;
                world.PedestrianCount = GameplayRules.MaxPedestrians;
                for (int i = 0; i < world.TrafficCount; i++) ConfigureTraffic(world.Traffic[i], i, start + 55000 + i * 14000);
                for (int i = 0; i < world.PedestrianCount; i++) ConfigurePedestrian(world.Pedestrians[i], i, start + 35000 + i * 19000);
            }
            events.Clear(); projected = BenchmarkReadModelProjection.World(world, events);
            local = BenchmarkReadModelProjection.Rider(RaceSimulation.FindRider(world, 1));
            Stage.ResetInterpolation(); effects.ResetEvents(); audioView.ResetEvents();
        }

        private static void SetSpawn(RaceRider rider, long distance, int lateral)
        {
            rider.DistanceMillimeters = rider.BikeDistanceMillimeters = distance;
            rider.LateralMillimeters = rider.BikeLateralMillimeters = lateral;
            rider.SpeedMillimetersPerSecond = 27000; rider.Gear = 3; rider.Weapon = WeaponKind.Club;
        }

        private static void ConfigureTraffic(RaceTraffic traffic, int index, long distance)
        {
            if (traffic.Id <= 0) traffic.Id = 3301 + index;
            traffic.Active = true; traffic.Oncoming = index % 3 == 0;
            traffic.DistanceMillimeters = distance; traffic.LateralMillimeters = index % 2 == 0 ? -3600 : 3600;
            traffic.SpeedMillimetersPerSecond = traffic.Oncoming ? -18000 : 22000;
            bool van = VehicleDimensions.IsVan(traffic.Id);
            traffic.WidthMillimeters = van ? VehicleDimensions.VanWidth : VehicleDimensions.CoupeWidth;
            traffic.LengthMillimeters = van ? VehicleDimensions.VanLength : VehicleDimensions.CoupeLength;
            traffic.HeightMillimeters = van ? VehicleDimensions.VanHeight : VehicleDimensions.CoupeHeight;
        }

        private static void ConfigurePedestrian(RacePedestrian pedestrian, int index, long distance)
        {
            if (pedestrian.Id <= 0) pedestrian.Id = 4301 + index;
            pedestrian.DistanceMillimeters = distance;
            pedestrian.LateralMillimeters = index % 2 == 0 ? -7700 : 7700;
            pedestrian.FacingSide = index % 2 == 0 ? 1 : -1; pedestrian.IsCrossing = index % 3 == 0;
            pedestrian.Mode = PedestrianMode.Walking; pedestrian.ModeAgeTicks = 0; pedestrian.HeightMillimeters = 0;
        }

        private void Update()
        {
            if (!Running) return;
            double began = Time.realtimeSinceStartupAsDouble;
            double frameSeconds = Math.Max(0, began - previousTime); previousTime = began;
            accumulator += frameSeconds;
            int steps = 0;
            const double step = 1.0 / GameplayRules.TickRate;
            while (accumulator >= step && steps < 6)
            {
                StepWorld(); accumulator -= step; steps++;
                if (measuring) measuredTicks++;
            }
            if (accumulator >= step)
            {
                long dropped = (long)(accumulator / step); accumulator -= dropped * step;
                if (measuring) droppedTicks += dropped;
            }
            local = BenchmarkReadModelProjection.Rider(RaceSimulation.FindRider(world, 1));
            float dt = Mathf.Min((float)frameSeconds, .1f);
            Stage.RenderFrame(projected, local, true, dt, ReducedMotion);
            effects.Render(projected, local, true, dt, ReducedMotion);
            audioView.Render(projected, local, true, EnableAudio, dt);
            FrameTimingManager.CaptureFrameTimings();
            if (!measuring)
            {
                Progress = (float)((began - warmupBegan) / (WarmupSeconds + SampleSeconds));
                if (began - warmupBegan >= WarmupSeconds) BeginMeasurement();
                return;
            }
            if (frameCount < frames.Length) frames[frameCount++] = (float)(frameSeconds * 1000);
            else capacityExceeded = true;
            if (Stage.ViewCamera.pixelWidth != receipt.width || Stage.ViewCamera.pixelHeight != receipt.height)
                receipt.resolutionChangedDuringSample = true;
            if (VisualQuality.Index != receipt.graphicsQualityIndex || GraphicsSettings.defaultRenderPipeline != appliedPipeline ||
                !Mathf.Approximately(appliedPipeline.renderScale, receipt.renderScale)) receipt.qualityChangedDuringSample = true;
            Record(gcRecorder, gc); Record(drawRecorder, draws); Record(batchRecorder, batches);
            Record(setPassRecorder, setPass); Record(triangleRecorder, triangles); Record(vertexRecorder, vertices);
            if (FrameTimingManager.GetLatestTimings(1, timings) > 0)
            {
                if (timings[0].cpuFrameTime > 0) cpuFrame.Add(timings[0].cpuFrameTime);
                if (timings[0].gpuFrameTime > 0) gpuFrame.Add(timings[0].gpuFrameTime);
            }
            riderCounts.Add(world.RiderCount); trafficCounts.Add(world.TrafficCount); pedestrianCounts.Add(world.PedestrianCount);
            if (frameCount % 30 == 0)
            {
                long allocated = Profiler.GetTotalAllocatedMemoryLong();
                if (allocated > 0) unityMemory.Add(allocated);
                long managed = GC.GetTotalMemory(false);
                if (managed > 0) managedMemory.Add(managed);
            }
            updateCpu.Add((Time.realtimeSinceStartupAsDouble - began) * 1000);
            double elapsed = began - measurementBegan;
            Progress = Mathf.Clamp01((float)((WarmupSeconds + elapsed) / (WarmupSeconds + SampleSeconds)));
            if (elapsed >= SampleSeconds) Complete(elapsed);
        }

        private void StepWorld()
        {
            var own = RaceSimulation.FindRider(world, 1);
            if ((GameplayRules.IsTerminal(own.Mode) && own.ModeAgeTicks >= 120) || own.DistanceMillimeters > world.Track.LengthMillimeters - 30000)
            { cycles++; CreateWorld(); own = RaceSimulation.FindRider(world, 1); }
            if (Stress) MaintainStress(own);
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = world.Riders[i];
                if (rider.Kind == RiderKind.Player) RaceSimulation.SetInput(world, rider.Id, ScriptedInput(rider));
            }
            RaceSimulation.Step(world);
            if (Stress)
            {
                // Core can retire actors near the course end; refill the benchmark fixture before publishing its workload.
                for (int i = world.TrafficCount; i < GameplayRules.MaxTraffic; i++)
                { ConfigureTraffic(world.Traffic[i], i, own.DistanceMillimeters + 95000 + i * 8500); if (measuring) fixtureRespawns++; }
                world.TrafficCount = GameplayRules.MaxTraffic;
                for (int i = world.PedestrianCount; i < GameplayRules.MaxPedestrians; i++)
                { ConfigurePedestrian(world.Pedestrians[i], i, own.DistanceMillimeters + 70000 + i * 15000); if (measuring) fixtureRespawns++; }
                world.PedestrianCount = GameplayRules.MaxPedestrians;
            }
            for (int i = 0; i < world.EventCount; i++)
            {
                var item = world.Events[i];
                if (events.Count == 128) events.RemoveAt(0);
                events.Add(item);
                if (!measuring) continue;
                if (item.Kind == RaceEventKind.Attack) measuredAttacks++;
                if (item.Kind == RaceEventKind.Hit) measuredHits++;
                if (item.Kind == RaceEventKind.Crash) measuredCrashes++;
            }
            while (events.Count > 0 && events[0].Tick < world.Tick - 120) events.RemoveAt(0);
            if (world.Tick % 3 == 0) projected = BenchmarkReadModelProjection.World(world, events);
        }

        private RaceInput ScriptedInput(RaceRider rider)
        {
            int pairLane = rider.Id % 2 == 0 ? 700 : -700;
            // Integer triangular lane weave, shared by each combat pair; no wall-clock/random input.
            int phase = (int)(world.Tick % 600), triangle = phase < 300 ? phase : 600 - phase;
            int target = pairLane + (triangle - 150) * 4;
            int curve = world.Track.CurvatureAt(rider.DistanceMillimeters + rider.SpeedMillimetersPerSecond / 5);
            int drift = (int)((long)rider.SpeedMillimetersPerSecond * curve / 100000);
            int lateralVelocity = Math.Max(-5500, Math.Min(5500, (target - rider.LateralMillimeters) * 2));
            int steer = Math.Max(-1000, Math.Min(1000, (lateralVelocity + drift) * 1000 / (1200 + rider.SpeedMillimetersPerSecond / 6)));
            int speedTarget = 37000 - (Math.Abs(curve) > 6500 ? 5000 : 0);
            int throttle = rider.SpeedMillimetersPerSecond < speedTarget ? 1000 : 300;
            int brake = rider.SpeedMillimetersPerSecond > speedTarget + 1200 ? 200 : 0;
            int attack = world.Tick % 90 == rider.Id % 3 * 12 ? (rider.Id % 2 == 0 ? -1 : 1) : 0;
            return new RaceInput(throttle, brake, steer, attack, world.Tick % 720 > 600);
        }

        private void MaintainStress(RaceRider own)
        {
            for (int i = 0; i < world.RiderCount; i++)
            {
                var rider = world.Riders[i];
                if (rider.Id == 1) continue;
                long delta = rider.DistanceMillimeters - own.DistanceMillimeters;
                if (!GameplayRules.IsTerminal(rider.Mode) && delta > -65000 && delta < 170000) continue;
                var replacement = new RaceRider { Id = rider.Id, Kind = rider.Kind };
                SetSpawn(replacement, own.DistanceMillimeters + 8000 + i / 2 * 6500, i % 2 == 0 ? -700 : 700);
                world.Riders[i] = replacement; if (measuring) fixtureRespawns++;
            }
            for (int i = 0; i < world.TrafficCount; i++)
            {
                long delta = world.Traffic[i].DistanceMillimeters - own.DistanceMillimeters;
                if (delta > -35000 && delta < 250000) continue;
                ConfigureTraffic(world.Traffic[i], i, own.DistanceMillimeters + 95000 + i * 8500);
                if (measuring) fixtureRespawns++;
            }
            for (int i = world.TrafficCount; i < GameplayRules.MaxTraffic; i++)
            { ConfigureTraffic(world.Traffic[i], i, own.DistanceMillimeters + 95000 + i * 8500); if (measuring) fixtureRespawns++; }
            world.TrafficCount = GameplayRules.MaxTraffic;
            for (int i = 0; i < world.PedestrianCount; i++)
            {
                long delta = world.Pedestrians[i].DistanceMillimeters - own.DistanceMillimeters;
                if (delta > -35000 && delta < 190000) continue;
                ConfigurePedestrian(world.Pedestrians[i], i, own.DistanceMillimeters + 70000 + i * 15000);
                if (measuring) fixtureRespawns++;
            }
            for (int i = world.PedestrianCount; i < GameplayRules.MaxPedestrians; i++)
            { ConfigurePedestrian(world.Pedestrians[i], i, own.DistanceMillimeters + 70000 + i * 15000); if (measuring) fixtureRespawns++; }
            world.PedestrianCount = GameplayRules.MaxPedestrians;
        }

        private void BeginMeasurement()
        {
            receipt.width = Stage.ViewCamera == null ? Screen.width : Stage.ViewCamera.pixelWidth;
            receipt.height = Stage.ViewCamera == null ? Screen.height : Stage.ViewCamera.pixelHeight;
            receipt.stageMeshRendererComponents = Stage.GetComponentsInChildren<MeshRenderer>(true).Length;
            receipt.roadMeshRendererComponents = Stage.Road.GetComponentsInChildren<MeshRenderer>(true).Length;
            var filters = Stage.GetComponentsInChildren<MeshFilter>(true);
            var distinct = new HashSet<Mesh>();
            foreach (var filter in filters) if (filter.sharedMesh != null) distinct.Add(filter.sharedMesh);
            foreach (var filter in Stage.Road.GetComponentsInChildren<MeshFilter>(true)) if (filter.sharedMesh != null) distinct.Add(filter.sharedMesh);
            receipt.distinctStageAndRoadMeshes = distinct.Count;
            foreach (var mesh in distinct) receipt.verticesAcrossDistinctStageAndRoadMeshes += mesh.vertexCount;
            var stageParticles = Stage.GetComponentsInChildren<ParticleSystem>(true);
            receipt.legacyStageParticleSystems = stageParticles.Length;
            foreach (var particles in stageParticles) if (particles.isPlaying) receipt.legacyStagePlayingParticleSystems++;
            receipt.effectsParticleSystems = effects.GetComponentsInChildren<ParticleSystem>(true).Length;
            receipt.effectsTrailRenderers = effects.GetComponentsInChildren<TrailRenderer>(true).Length;
            receipt.effectsParticleHardLimit = effects.MaximumParticleBudget;
            receipt.audioSourceCount = audioView.GetComponentsInChildren<AudioSource>(true).Length;
            receipt.startedUtc = DateTime.UtcNow.ToString("O");
            receipt.startTick = world.Tick;
            measurementBegan = previousTime = Time.realtimeSinceStartupAsDouble;
            receipt.gcCollectionsStart = new[] { GC.CollectionCount(0), GC.CollectionCount(1), GC.CollectionCount(2) };
            measuring = true;
        }

        private static void Record(ProfilerRecorder recorder, CounterSample target)
        { if (recorder.Valid && recorder.Count > 0) target.Add(recorder.LastValue); }

        private void Complete(double elapsed)
        {
            if (!measuring || elapsed < SampleSeconds || frameCount == 0) return;
            Running = false; Completed = true; Progress = 1;
            Array.Sort(frames, 0, frameCount);
            receipt.status = "completed"; receipt.completedUtc = DateTime.UtcNow.ToString("O");
            receipt.measuredSeconds = elapsed; receipt.frames = frameCount;
            receipt.frameP50Ms = frames[(frameCount - 1) / 2]; receipt.frameP95Ms = frames[(int)Math.Ceiling(frameCount * .95) - 1];
            receipt.frameMaxMs = frames[frameCount - 1]; receipt.meanFps = frameCount / elapsed;
            receipt.frameBudgetMs = 1000.0 / 60; receipt.frameP95WithinBudget = receipt.frameP95Ms <= receipt.frameBudgetMs;
            receipt.endTick = world.Tick; receipt.measuredSimulationTicks = measuredTicks; receipt.droppedSimulationTicks = droppedTicks;
            receipt.simulationCoverage = measuredTicks / (elapsed * GameplayRules.TickRate);
            receipt.sampleCapacityExceeded = capacityExceeded;
            receipt.measurementCoverageValid = elapsed >= 60 && frameCount >= 600 && !capacityExceeded &&
                !receipt.resolutionChangedDuringSample && !receipt.qualityChangedDuringSample && receipt.simulationCoverage >= .95;
            receipt.measuredAttacks = measuredAttacks; receipt.measuredHits = measuredHits; receipt.measuredCrashes = measuredCrashes;
            receipt.worldRestarts = cycles; receipt.measuredFixtureRecycles = fixtureRespawns;
            receipt.riders = riderCounts.Export(); receipt.traffic = trafficCounts.Export(); receipt.pedestrians = pedestrianCounts.Export();
            receipt.requiredDensityPresentEverySample = riderCounts.Minimum == receipt.expectedRiders &&
                (!Stress || (trafficCounts.Minimum == receipt.expectedTraffic && pedestrianCounts.Minimum == receipt.expectedPedestrians));
            receipt.gcAllocatedBytesPerFrame = gc.Export(); receipt.drawCalls = draws.Export(); receipt.batches = batches.Export();
            receipt.setPassCalls = setPass.Export(); receipt.triangles = triangles.Export(); receipt.vertices = vertices.Export();
            receipt.unityAllocatedBytes = unityMemory.Export(); receipt.managedBytes = managedMemory.Export();
            receipt.cpuFrameMs = cpuFrame.Export(); receipt.gpuFrameMs = gpuFrame.Export(); receipt.benchmarkUpdateMs = updateCpu.Export();
            receipt.gcCollectionsDuringSample = new[] { GC.CollectionCount(0) - receipt.gcCollectionsStart[0],
                GC.CollectionCount(1) - receipt.gcCollectionsStart[1], GC.CollectionCount(2) - receipt.gcCollectionsStart[2] };
            LastReceiptJson = JsonUtility.ToJson(receipt, true);
#if UNITY_EDITOR
            try { LastReceiptPath = WriteEditorReceipt(LastReceiptJson); }
            catch (Exception exception) { Error = "Measurement completed; receipt write failed: " + exception.Message; }
#endif
            Debug.Log("RB_P06_BENCHMARK_COMPLETE " + receipt.profile + " frames=" + frameCount + " p95Ms=" + receipt.frameP95Ms.ToString("0.000") + " coverage=" + receipt.simulationCoverage.ToString("0.000"));
            StopRecorders(); audioView.SetMuted(true); effects.ResetEvents(); if (!nativeDiagnostic) UnityApplication.targetFrameRate = originalTargetFrameRate;
        }

#if UNITY_EDITOR
        private string WriteEditorReceipt(string json)
        {
            string root = Path.GetFullPath(Path.Combine(UnityApplication.dataPath, ".."));
            string relative = OutputPath.Replace("{profile}", receipt.profile).Replace("{run}", receipt.runId);
            if (Path.IsPathRooted(relative)) throw new InvalidOperationException("Receipt path must be relative to this project.");
            string target = Path.GetFullPath(Path.Combine(root, relative));
            if (!target.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Receipt path must stay inside this project.");
            Directory.CreateDirectory(Path.GetDirectoryName(target));
            using (var stream = new FileStream(target, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
            using (var writer = new StreamWriter(stream, new System.Text.UTF8Encoding(false))) writer.Write(json + "\n");
            return target;
        }
#endif

        private void StopRecorders()
        { gcRecorder.Dispose(); drawRecorder.Dispose(); batchRecorder.Dispose(); setPassRecorder.Dispose(); triangleRecorder.Dispose(); vertexRecorder.Dispose(); }

        private void OnDisable()
        {
            if (Running) { Error = "Benchmark interrupted before a complete measurement; no receipt written."; Running = false; }
            StopRecorders(); if (audioView != null) audioView.SetMuted(true);
            if (effects != null) effects.ResetEvents();
            if (nativeDiagnostic) RestoreNativeDiagnosticTiming(); else if (receipt != null) UnityApplication.targetFrameRate = originalTargetFrameRate;
        }

        private sealed class RiderOrder : IComparer<RaceRider>
        {
            public static readonly RiderOrder Instance = new RiderOrder();
            public int Compare(RaceRider first, RaceRider second) => first.Id.CompareTo(second.Id);
        }
        private sealed class CounterSample
        {
            private int count;
            private double sum, maximum = double.MinValue, minimum = double.MaxValue;
            public double Minimum => count == 0 ? -1 : minimum;
            public void Add(double value) { count++; sum += value; maximum = Math.Max(maximum, value); minimum = Math.Min(minimum, value); }
            public CounterReceipt Export() => new CounterReceipt { available = count > 0, samples = count,
                mean = count > 0 ? sum / count : -1, minimum = count > 0 ? minimum : -1, maximum = count > 0 ? maximum : -1 };
        }
        [Serializable] private sealed class CounterReceipt
        { public bool available; public int samples; public double mean, minimum, maximum; }
        [Serializable] private sealed class Receipt
        {
            public string runId, profile, status, runtimeSourceRevision, scope, startedUtc, completedUtc, unityVersion, productVersion;
            public string operatingSystem, processor, graphicsDevice, graphicsApi, qualityLevel, workload, limits;
            public bool editor, reducedMotion, lowEffectsQuality, audioEnabled, frameP95WithinBudget, measurementCoverageValid;
            public bool sampleCapacityExceeded, requiredDensityPresentEverySample, resolutionChangedDuringSample;
            public bool qualityChangedDuringSample;
            public int graphicsQualityIndex;
            public float renderScale;
            public int seed, targetFrameRate, vSyncCount, width, height, deviceMemoryMiB, graphicsMemoryMiB, expectedRiders, expectedTraffic, expectedPedestrians;
            public int frames, measuredAttacks, measuredHits, measuredCrashes, worldRestarts, measuredFixtureRecycles;
            public int stageMeshRendererComponents, roadMeshRendererComponents, distinctStageAndRoadMeshes, legacyStageParticleSystems, legacyStagePlayingParticleSystems;
            public int effectsParticleSystems, effectsTrailRenderers, effectsParticleHardLimit, audioSourceCount;
            public long verticesAcrossDistinctStageAndRoadMeshes, startTick, endTick, measuredSimulationTicks, droppedSimulationTicks;
            public float warmupSeconds, requestedSampleSeconds, frameP50Ms, frameP95Ms, frameMaxMs;
            public double measuredSeconds, meanFps, frameBudgetMs, simulationCoverage;
            public int[] gcCollectionsStart, gcCollectionsDuringSample;
            public CounterReceipt riders, traffic, pedestrians, gcAllocatedBytesPerFrame, drawCalls, batches, setPassCalls, triangles, vertices;
            public CounterReceipt unityAllocatedBytes, managedBytes, cpuFrameMs, gpuFrameMs, benchmarkUpdateMs;
        }
    }
}
