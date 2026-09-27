using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;

var results = new List<object>(); var details = new List<object>(); int failures = 0;
void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
void Test(string name, Action action)
{
    try { action(); results.Add(new { name, passed = true }); Console.WriteLine("PASS " + name); }
    catch (Exception error) { failures++; results.Add(new { name, passed = false, error = error.Message }); Console.WriteLine("FAIL " + name + ": " + error.Message); }
}
string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
var sources = new[] { "Assets/RacingBois/Client/Application/MultiplayerSession.cs", "Assets/RacingBois/Client/Application/MultiplayerSession.Messages.cs",
    "Assets/RacingBois/Client/Application/RemoteMotionSampler.cs", "Assets/RacingBois/Client/Presentation/RaceStageView.cs", "Assets/RacingBois/Client/Bootstrap/RaceBootstrap.cs" }.ToDictionary(p => p, Hash);
var fixtures = new[] { "maximum-correction-episode", "speculative-neighbor-episode" };
var loaded = fixtures.ToDictionary(name => name, name => JsonDocument.Parse(File.ReadAllText("docs/p09/releases/e/" + name + ".json")));

foreach (string fixture in fixtures)
{
    var root = loaded[fixture].RootElement; var episode = root.GetProperty("episode"); var before = episode.GetProperty("Before");
    Test(fixture + "_unchanged_production_replay_and_actual_sample", () =>
    {
        foreach (string path in sources.Keys.Where(p => p.Contains("/Application/"))) Check(Hash(path) == root.GetProperty("sources").GetProperty(path).GetString(), "Application source drift: " + path);
        var clock = new FixtureClock { NowSeconds = before.GetProperty("At").GetDouble() };
        using var session = new MultiplayerSession(new NoNetwork(), new NoWire(), clock, null);
        session.SeedPresentation(before); string digest = session.GameplayDigest();
        var withoutEvents = session.SamplePresentation(); var uncapped = session.LocalRider;
        session.SetFixtureEvents(before); session.SamplePresentation(); var capped = session.LocalRider;
        Check(session.GameplayDigest() == digest, "Presentation changed authority, prediction or pending input.");
        var recorded = before.GetProperty("CachedPose");
        Check(Math.Abs(capped.LongitudinalMeters - recorded.GetProperty("S").GetSingle()) < .005f, "Production cap does not reproduce captured cached pose.");
        float capDisplacement = Math.Abs(capped.LongitudinalMeters - uncapped.LongitudinalMeters);
        if (fixture == "maximum-correction-episode") Check(capDisplacement > 21 && capDisplacement < 21.2f, "Known event-cap discontinuity not reproduced.");
        else Check(capDisplacement < .005f, "Unexpected cap in neighbor case.");
        details.Add(new { fixture, productionRawS = uncapped.LongitudinalMeters, productionEventCappedS = capped.LongitudinalMeters,
            reproducedSameClockEventCapDisplacementMeters = capDisplacement, gameplayDigestUnchanged = true,
            rawEqualTargetCorrectionMeters = episode.GetProperty("Delta").GetDouble(),
            recordedPresentedPairDeltaMeters = episode.GetProperty("PresentedDelta").GetDouble(),
            scope = "Actual unchanged SamplePresentation with exact full-checkpoint replay. Event IDs are synthetic monotonic IDs; no wire/handshake validation is claimed. Reproduced cap step is not a captured previous Unity frame." });
    });
}

foreach (string fixture in fixtures)
foreach (int fps in new[] { 20, 30, 60, 120 })
{
    var episode = loaded[fixture].RootElement.GetProperty("episode");
    var before = Pose.Read(episode.GetProperty("PresentedBefore").GetProperty("Pose")); var after = Pose.Read(episode.GetProperty("PresentedAfter").GetProperty("Pose"));
    int course = episode.GetProperty("Before").GetProperty("Course").GetInt32(), level = episode.GetProperty("Before").GetProperty("Level").GetInt32();
    var track = TrackDefinition.ForCourse(course, level); var old = StageGeometry.Target(track, before); var target = StageGeometry.Target(track, after);
    Test(fixture + "_root_continuity_and_bounded_settle_" + fps + "fps", () =>
    {
        float dt = 1f / fps;
        var rider = new VisualTransformReconciler(); var bike = new VisualTransformReconciler();
        rider.Reset(old.Rider, old.RiderRotation); bike.Reset(old.Bike, old.BikeRotation);
        rider.Sample(target.Rider, target.RiderRotation, dt, 100, true); bike.Sample(target.Bike, target.BikeRotation, dt, 100, true);
        Check(Vector3.Distance(rider.Position, old.Rider) < .00001f && Vector3.Distance(bike.Position, old.Bike) < .00001f, "Discontinuity sample teleported a visual root.");
        float maximumRiderStep = 0, maximumBikeStep = 0, settled = -1;
        var camera = StageGeometry.Camera(track, before); float minimumRiderDepth = float.PositiveInfinity;
        for (int frame = 1; frame <= fps * 3; frame++)
        {
            Vector3 previousRider = rider.Position, previousBike = bike.Position;
            rider.Sample(target.Rider, target.RiderRotation, dt, 100, false); bike.Sample(target.Bike, target.BikeRotation, dt, 100, false);
            maximumRiderStep = Math.Max(maximumRiderStep, Vector3.Distance(rider.Position, previousRider));
            maximumBikeStep = Math.Max(maximumBikeStep, Vector3.Distance(bike.Position, previousBike));
            Check(Vector3.Distance(rider.Position, previousRider) <= 20 * dt + .001f, "Correction-only rider velocity exceeded the bound.");
            Check(Vector3.Distance(bike.Position, previousBike) <= 20 * dt + .001f, "Correction-only bike velocity exceeded the bound.");
            // Existing camera's seven-hertz damping, aimed at the displayed actor offset.
            var desired = StageGeometry.Camera(track, after); var offset = rider.Position - target.Rider;
            desired = desired with { Position = desired.Position + offset, Look = desired.Look + offset };
            camera = camera with { Position = Vector3.Lerp(camera.Position, desired.Position, 1 - MathF.Exp(-7 * dt)), Look = Vector3.Lerp(camera.Look, desired.Look, 1 - MathF.Exp(-7 * dt)) };
            var forward = Vector3.Normalize(camera.Look - camera.Position); minimumRiderDepth = Math.Min(minimumRiderDepth, Vector3.Dot(rider.Position - camera.Position, forward));
            if (settled < 0 && rider.RemainingTranslation <= .002f && bike.RemainingTranslation <= .002f && rider.RemainingAngle <= .002f && bike.RemainingAngle <= .002f) settled = frame * dt;
        }
        Check(settled > 0 && settled < 2, "Continuity budget failed to settle in two seconds.");
        Check(minimumRiderDepth > .12f, "Controlled camera fixture crossed the rider root near plane.");
        details.Add(new { fixture, fps, rawRiderRootStepMeters = Vector3.Distance(old.Rider, target.Rider), rawBikeRootStepMeters = Vector3.Distance(old.Bike, target.Bike),
            firstCandidateRootStepMeters = 0, maximumRiderCorrectionStepMeters = maximumRiderStep, maximumBikeCorrectionStepMeters = maximumBikeStep, settleSeconds = settled,
            controlledCameraMinimumRiderDepthMeters = minimumRiderDepth,
            scope = "Retained before/after poses mapped through current TrackDefinition and stage translation formulas, followed by a stationary-target step response. Camera initialization/look blend are controlled assumptions, not captured Unity camera history or native visual acceptance." });
    });
}

Test("ordinary_motion_is_exact_without_extra_input_lag", () =>
{
    var value = new VisualTransformReconciler();
    for (int frame = 0; frame < 600; frame++)
    {
        var target = new Vector3(frame, MathF.Sin(frame * .01f) * .2f, .15f * MathF.Sin(frame * .03f));
        value.Sample(target, Quaternion.Identity, 1f / 60, 100, false);
        Check(value.Position == target && value.RemainingTranslation == 0, "Ordinary sixty-metre-per-second motion was delayed.");
    }
    Check(value.ReconciliationCount == 0, "Continuous motion triggered reconciliation.");
});
Test("event_cap_large_reverse_step_is_continuous_and_converges", () =>
{
    var value = new VisualTransformReconciler(); value.Reset(new Vector3(2146.83f, 0, 0), Quaternion.Identity);
    var target = new Vector3(2125.688f, 0, 0); value.Sample(target, Quaternion.Identity, 1f / 60, 100, false);
    Check(value.Position.X == 2146.83f && value.BeganReconciliation, "Event-cap jump escaped the renderer guard.");
    float maximum = 0; float settled = -1;
    for (int frame = 1; frame <= 180; frame++)
    {
        var previous = value.Position; value.Sample(target, Quaternion.Identity, 1f / 60, 100, false);
        maximum = Math.Max(maximum, Vector3.Distance(value.Position, previous));
        if (settled < 0 && value.RemainingTranslation < .002f) settled = frame / 60f;
    }
    Check(maximum <= 20f / 60 + .001f && settled > 0 && settled < 2, "Large reverse correction exceeded its bounded convergence budget.");
    details.Add(new { fixture = "same-clock-event-cap", rawDisplacementMeters = 21.142f, firstCandidateStep = 0, maximumStepMeters = maximum, settledSeconds = settled,
        limitation = "Requires visible positional error for over one second at this cap; this is not invisibility or immediate authority-position fidelity." });
});
Test("repeat_correction_freeze_resume_and_reset_lifecycle", () =>
{
    var value = new VisualTransformReconciler(); value.Reset(Vector3.Zero, Quaternion.Identity);
    value.Sample(new Vector3(12, 0, 0), Quaternion.Identity, 1f / 60, 100, true);
    value.Sample(new Vector3(12, 0, 0), Quaternion.Identity, 1f / 60, 100, false); var visible = value.Position;
    value.Sample(new Vector3(-6, 0, 0), Quaternion.Identity, 1f / 60, 100, true); Check(value.Position == visible, "Repeated correction jumps.");
    for (int i = 0; i < 60; i++) value.Sample(new Vector3(-6, 0, 0), Quaternion.Identity, 1f / 60, 100, false, frozen: true);
    Check(value.Position == visible, "A frozen presentation continued to drift.");
    value.Sample(new Vector3(4, 0, 0), Quaternion.Identity, 1f / 60, 100, false); Check(value.Position == visible, "Resume teleported.");
    value.Sample(new Vector3(100, 0, 0), Quaternion.Identity, 1f / 60, 100, false, reset: true); Check(value.Position.X == 100 && value.RemainingTranslation == 0, "Explicit scene/rider reset leaked the prior offset.");
});

TimedTests.Run(Test, Check, loaded, details);
Test("production_sources_unchanged", () => Check(sources.All(pair => Hash(pair.Key) == pair.Value), "Production source changed during the isolated test."));
string output = args.Length > 0 ? args[0] : "docs/p10/presentation-reconciliation-staging/validation.json";
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output, JsonSerializer.Serialize(new { passed = failures == 0, failures, tests = results.Count, results, details, sources,
    candidate = "Two isolated renderer-only variants. Speed-capped variant exposes1.25–1.8s offset; finite-duration variant limits uninterrupted offset to300ms and rebases the camera filter coordinate before applying the same display offset. Neither is visually accepted.",
    nativeUnityRendered = false, productionApplied = false, scope = "Isolated sample-path and render-transform mathematics. Inputs, authority and prediction remain unchanged. Native frame capture, terrain/occlusion, VFX alignment, animation and human comfort remain separate gates." }, new JsonSerializerOptions { WriteIndented = true, IncludeFields = true }));
return failures == 0 ? 0 : 1;

sealed class FixtureClock : IMonotonicClock { public double NowSeconds { get; set; } }
sealed class NoNetwork : IRealtimeTransport
{
    public event Action Opened { add { } remove { } } public event Action<string> Message { add { } remove { } } public event Action<string> Closed { add { } remove { } }
    public void Connect(string endpoint) => throw new InvalidOperationException("Network is forbidden in this fixture.");
    public void Send(string text) => throw new InvalidOperationException("Network is forbidden in this fixture.");
    public void Close() { } public void Poll() { } public void Dispose() { }
}
sealed class NoWire : IWireCodec { public string Encode(object value) => throw new InvalidOperationException(); public T Decode<T>(string text) where T : class => throw new InvalidOperationException(); }
readonly record struct Pose(float S, float D, float H, float BikeS, float BikeD, float Speed, RiderMode Mode)
{
    public static Pose Read(JsonElement value) => new(value.GetProperty("S").GetSingle(), value.GetProperty("D").GetSingle(), value.GetProperty("H").GetSingle(),
        value.GetProperty("BikeS").GetSingle(), value.GetProperty("BikeD").GetSingle(), value.GetProperty("Speed").GetSingle(), Enum.Parse<RiderMode>(value.GetProperty("Mode").GetString()!));
}
readonly record struct StageTargets(Vector3 Rider, Vector3 Bike, Quaternion RiderRotation, Quaternion BikeRotation);
readonly record struct CameraTarget(Vector3 Position, Vector3 Look);
static class StageGeometry
{
    internal static Vector3 Point(TrackDefinition track, float s, float d = 0, float h = 0)
    { var p = track.Sample((long)(s * 1000)); return new Vector3(p.CenterX + p.ForwardZ * d, p.CenterY + h, p.CenterZ - p.ForwardX * d); }
    internal static Quaternion Heading(TrackDefinition track, float s)
    {
        var p = track.Sample((long)(s * 1000)); var forward = Vector3.Normalize(new Vector3(p.ForwardX, p.GradePermille / 1000f, p.ForwardZ));
        var right = Vector3.Normalize(Vector3.Cross(Vector3.UnitY, forward)); var up = Vector3.Cross(forward, right);
        return Quaternion.CreateFromRotationMatrix(new Matrix4x4(right.X, right.Y, right.Z, 0, up.X, up.Y, up.Z, 0, forward.X, forward.Y, forward.Z, 0, 0, 0, 0, 1));
    }
    public static StageTargets Target(TrackDefinition track, Pose p)
    {
        bool detached = p.Mode == RiderMode.Falling; float bs = detached ? p.BikeS : p.S, bd = detached ? p.BikeD : p.D;
        var heading = Heading(track, bs); var bike = Point(track, bs, bd, detached ? .48f : p.H);
        var rider = detached ? Point(track, p.S, p.D, p.H) - Vector3.UnitY * .55f : bike + Vector3.Transform(new Vector3(0, -.08f, -.32f), heading);
        return new StageTargets(rider, bike, Heading(track, p.S), heading * Quaternion.CreateFromAxisAngle(Vector3.UnitZ, detached ? 76 * MathF.PI / 180 : 0));
    }
    public static CameraTarget Camera(TrackDefinition track, Pose p)
    {
        var position = Point(track, p.S, p.D, Math.Min(1.5f, p.H)) + Vector3.Transform(new Vector3(0, 2.65f, -6.5f), Heading(track, p.S));
        position.Y = Math.Max(position.Y, Point(track, p.S - 7).Y + 1.5f);
        return new CameraTarget(position, Point(track, p.S + 17, p.D * .5f, 1.1f));
    }
    internal static Quaternion LookRotation(Vector3 forward)
    {
        forward = Vector3.Normalize(forward); var right = Vector3.Normalize(Vector3.Cross(Vector3.UnitY, forward)); var up = Vector3.Cross(forward, right);
        return Quaternion.CreateFromRotationMatrix(new Matrix4x4(right.X, right.Y, right.Z, 0, up.X, up.Y, up.Z, 0, forward.X, forward.Y, forward.Z, 0, 0, 0, 0, 1));
    }
}
