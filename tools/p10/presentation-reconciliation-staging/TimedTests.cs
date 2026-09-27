using System.Numerics;
using System.Text.Json;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;

internal static class TimedTests
{
    internal static void Run(Action<string, Action> test, Action<bool, string> check, Dictionary<string, JsonDocument> fixtures, List<object> details)
    {
        foreach (var entry in fixtures)
        foreach (int fps in new[] { 20, 30, 60, 120 })
        foreach (bool moving in new[] { false, true })
        {
            var e = entry.Value.RootElement.GetProperty("episode"); var before = Pose.Read(e.GetProperty("PresentedBefore").GetProperty("Pose")); var after = Pose.Read(e.GetProperty("PresentedAfter").GetProperty("Pose"));
            var track = TrackDefinition.ForCourse(e.GetProperty("Before").GetProperty("Course").GetInt32(), e.GetProperty("Before").GetProperty("Level").GetInt32());
            Exercise(entry.Key, before, after, track, fps, moving, test, check, details);
        }
        var max = fixtures["maximum-correction-episode"].RootElement.GetProperty("episode");
        var reverseBefore = Pose.Read(max.GetProperty("Before").GetProperty("RawPose")); var reverseAfter = Pose.Read(max.GetProperty("Before").GetProperty("CachedPose"));
        foreach (int fps in new[] { 20, 30, 60, 120 })
            Exercise("same-clock-event-cap", reverseBefore, reverseAfter, TrackDefinition.ForCourse(max.GetProperty("Before").GetProperty("Course").GetInt32(), max.GetProperty("Before").GetProperty("Level").GetInt32()), fps, false, test, check, details);
        test("timed_normal_motion_freeze_reset_and_repeat_continuity", () =>
        {
            var filter = new TimedVisualTransformReconciler();
            for (int i = 0; i < 120; i++) { var p = new Vector3(i, 0, 0); filter.Sample(p, Quaternion.Identity, 1f / 60, 100, false); check(filter.Position == p, "Normal motion was delayed."); }
            filter.Sample(new Vector3(140, 0, 0), Quaternion.Identity, 1f / 60, 100, true); var first = filter.Position;
            for (int i = 0; i < 30; i++) filter.Sample(new Vector3(140, 0, 0), Quaternion.Identity, 1f / 60, 100, false, frozen: true);
            check(filter.Position == first, "Freeze drift.");
            filter.Sample(new Vector3(125, 0, 0), Quaternion.Identity, 1f / 60, 100, false); check(filter.Position == first, "Resume jump.");
            filter.Sample(new Vector3(125, 0, 0), Quaternion.Identity, 1f / 60, 100, false); var second = filter.Position;
            filter.Sample(new Vector3(110, 0, 0), Quaternion.Identity, 1f / 60, 100, true); check(filter.Position == second, "Repeated correction jump.");
            filter.Sample(Vector3.Zero, Quaternion.Identity, 1f / 60, 100, false, reset: true); check(filter.Position == Vector3.Zero && filter.RemainingTranslation == 0, "Reset leaked a prior offset.");
        });
    }
    private static void Exercise(string name, Pose before, Pose after, TrackDefinition track, int fps, bool moving,
        Action<string, Action> test, Action<bool, string> check, List<object> details)
    {
        test("timed_" + name + "_" + fps + "fps_" + (moving ? "controlled_motion" : "hold"), () =>
        {
            float dt = 1f / fps; var old = StageGeometry.Target(track, before); var initialTarget = StageGeometry.Target(track, after);
            var rider = new TimedVisualTransformReconciler(); var bike = new TimedVisualTransformReconciler();
            rider.Reset(old.Rider, old.RiderRotation); bike.Reset(old.Bike, old.BikeRotation);
            var camera = StageGeometry.Camera(track, before); Vector3 cameraPosition = camera.Position, lastOffset = Vector3.Zero;
            var cameraRotation = StageGeometry.LookRotation(camera.Look - camera.Position);
            float previousSpeedFov = 60 + Math.Min(1, before.Speed / 58) * 8;
            float maximumRiderStep = 0, maximumBikeStep = 0, maximumCameraStep = 0, minimumDepth = float.PositiveInfinity, settled = -1;
            float maximumCorrectionSpeed = 0; Vector3 previousTarget = old.Rider;
            for (int frame = 0; frame <= fps; frame++)
            {
                // Real retained jump followed by a declared controlled continuation, not invented WAN frames.
                float displacement = moving ? after.Speed * frame * dt : 0;
                var pose = after with { S = after.S + displacement, BikeS = after.BikeS + displacement };
                var target = StageGeometry.Target(track, pose);
                Vector3 previousRider = rider.Position, previousBike = bike.Position, previousCamera = cameraPosition;
                rider.Sample(target.Rider, target.RiderRotation, dt, 100, frame == 0); bike.Sample(target.Bike, target.BikeRotation, dt, 100, frame == 0);
                Vector3 baseCamera = cameraPosition - lastOffset;
                if (rider.BeganReconciliation) baseCamera += rider.RawTargetShift;
                var desired = StageGeometry.Camera(track, pose);
                float blend = 1 - MathF.Exp(-7 * dt);
                cameraPosition = Vector3.Lerp(baseCamera, desired.Position, blend) + rider.PositionOffset;
                cameraRotation = Quaternion.Slerp(cameraRotation, StageGeometry.LookRotation(desired.Look - desired.Position), blend);
                previousSpeedFov += (60 + Math.Min(1, pose.Speed / 58) * 8 - previousSpeedFov) * (1 - MathF.Exp(-3 * dt));
                lastOffset = rider.PositionOffset;
                var view = Vector3.Transform(rider.Position - cameraPosition, Quaternion.Inverse(cameraRotation)); minimumDepth = Math.Min(minimumDepth, view.Z);
                float riderStep = Vector3.Distance(rider.Position, previousRider), bikeStep = Vector3.Distance(bike.Position, previousBike);
                maximumRiderStep = Math.Max(maximumRiderStep, riderStep); maximumBikeStep = Math.Max(maximumBikeStep, bikeStep);
                maximumCameraStep = Math.Max(maximumCameraStep, Vector3.Distance(cameraPosition, previousCamera));
                if (frame == 0) check(riderStep < .00001f && bikeStep < .00001f, "Timed variant teleported on first sample.");
                else maximumCorrectionSpeed = Math.Max(maximumCorrectionSpeed, ((rider.Position - previousRider) - (target.Rider - previousTarget)).Length() / dt);
                previousTarget = target.Rider;
                if (settled < 0 && rider.RemainingSeconds == 0 && bike.RemainingSeconds == 0) settled = frame * dt;
            }
            check(settled > 0 && settled <= .30f + dt + .0001f, "Visible offset exceeded the stated uninterrupted time budget.");
            check(minimumDepth > .12f, "Camera rebase crossed the rider-root near plane in controlled reconstruction.");
            details.Add(new { variant = "finite-duration-camera-rebase", fixture = name, fps, movingTarget = moving,
                rawRiderRootStepMeters = Vector3.Distance(old.Rider, initialTarget.Rider), rawBikeRootStepMeters = Vector3.Distance(old.Bike, initialTarget.Bike),
                firstCandidateRootStepMeters = 0, maximumRiderStepMeters = maximumRiderStep, maximumBikeStepMeters = maximumBikeStep,
                maximumCameraStepMeters = maximumCameraStep, maximumAdditionalCorrectionSpeedMetersPerSecond = maximumCorrectionSpeed,
                settledSeconds = settled, minimumControlledRiderDepthMeters = minimumDepth,
                scope = "Controlled road/transform reconstruction using the actual stage camera position Lerp7Hz and rotation Slerp7Hz formulas plus camera coordinate rebase. Initial camera assumes it had reached the old target; no captured Unity frame/camera state exists. Fast world motion and temporary relative errors remain visible risks." });
        });
    }
}
