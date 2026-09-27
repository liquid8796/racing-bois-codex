// Test reconstruction of the source-bound current stage formulas. This is not
// a captured Unity transform or camera history; native comparison remains open.
using System.Numerics;
using System.Text.Json;
using RacingBois.Gameplay.Definitions;

readonly record struct RecordedPose(float S, float D, float H, float BikeS, float BikeD, float BikeH,
    float Speed, float Lean, RiderMode Mode, int ModeAge, float BikeSpeed)
{
    public static RecordedPose Read(JsonElement pose, JsonElement checkpoint) => new(
        pose.GetProperty("S").GetSingle(), pose.GetProperty("D").GetSingle(), pose.GetProperty("H").GetSingle(),
        pose.GetProperty("BikeS").GetSingle(), pose.GetProperty("BikeD").GetSingle(),
        checkpoint.GetProperty("BikeHeightMillimeters").GetInt32() / 1000f,
        pose.GetProperty("Speed").GetSingle(), checkpoint.GetProperty("LeanMillidegrees").GetInt32() / 1000f,
        Enum.Parse<RiderMode>(pose.GetProperty("Mode").GetString()!), pose.GetProperty("ModeAge").GetInt32(),
        checkpoint.GetProperty("BikeSpeed").GetInt32() / 1000f);
}
readonly record struct StageTargets(Vector3 Rider, Vector3 Bike, Quaternion RiderRotation, Quaternion BikeRotation);
readonly record struct CameraTarget(Vector3 Position, Vector3 Look);
static class PoseGeometry
{
    internal static Vector3 Point(TrackDefinition track, float s, float d = 0, float h = 0)
    { var p = track.Sample((long)(s * 1000)); return new Vector3(p.CenterX + p.ForwardZ * d, p.CenterY + h, p.CenterZ - p.ForwardX * d); }
    internal static Quaternion Heading(TrackDefinition track, float s)
    { var p = track.Sample((long)(s * 1000)); return LookRotation(new Vector3(p.ForwardX, p.GradePermille / 1000f, p.ForwardZ)); }
    internal static bool Detached(RiderMode mode) => mode == RiderMode.Falling || mode == RiderMode.Detached || mode == RiderMode.Running || mode == RiderMode.Remounting || mode == RiderMode.Wrecked;
    public static StageTargets Target(TrackDefinition track, RecordedPose p)
    {
        bool detached = Detached(p.Mode); float bs = detached ? p.BikeS : p.S, bd = detached ? p.BikeD : p.D;
        float u = Math.Clamp(p.ModeAge / (float)GameplayRules.RemountDurationTicks, 0, 1);
        float mounting = p.Mode == RiderMode.Remounting ? u * u * (3 - 2 * u) : 0;
        float fall = detached ? 1 - mounting : 0;
        var heading = Heading(track, bs); var bike = Point(track, bs, bd, (detached ? p.BikeH : p.H) + fall * .48f);
        var rider = detached ? Point(track, p.S, p.D, p.H) : bike + Vector3.Transform(new Vector3(0, -.08f, -.32f), heading);
        if (p.Mode == RiderMode.Falling || p.Mode == RiderMode.Detached || p.Mode == RiderMode.Wrecked) rider.Y -= .55f;
        if (p.Mode == RiderMode.Remounting) rider = Vector3.Lerp(rider, Point(track, bs, bd) + Vector3.Transform(new Vector3(0, -.08f, -.32f), heading), mounting);
        return new StageTargets(rider, bike,
            Heading(track, p.S) * Quaternion.CreateFromAxisAngle(Vector3.UnitZ, (detached ? 0 : p.Lean * .65f) * MathF.PI / 180),
            heading * Quaternion.CreateFromAxisAngle(Vector3.UnitZ, (detached ? 76 * fall : p.Lean) * MathF.PI / 180));
    }
    public static CameraTarget Camera(TrackDefinition track, RecordedPose p)
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
