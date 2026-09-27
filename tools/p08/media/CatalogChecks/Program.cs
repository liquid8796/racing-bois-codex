using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using RacingBois.Client.Application;

var failures = new List<string>();
int checkedBeats = 0, checkedActorCues = 0;
void Check(bool condition, string description) { if (!condition) failures.Add(description); }
var expected = new Dictionary<CinematicRole, int> {
    [CinematicRole.Showcase]=15, [CinematicRole.Busted]=6, [CinematicRole.Start]=6,
    [CinematicRole.Win]=6, [CinematicRole.Lose]=10, [CinematicRole.Wreck]=6,
    [CinematicRole.Level]=6, [CinematicRole.Intro]=1, [CinematicRole.Duel]=1,
    [CinematicRole.Rival]=1, [CinematicRole.FinalWin]=1
};
var actions = new HashSet<string> { "Idle", "Ride", "LeanLeft", "LeanRight", "AttackLeft", "AttackRight", "KickLeft", "KickRight", "Hit", "Fall", "Run", "Remount", "Celebrate", "Inspect", "Converse", "Busted", "PitWork" };
Check(CinematicCatalog.All.Count==59, "Expected 59 sequences");
Check(CinematicCatalog.All.Select(x=>x.Id).Distinct().Count()==59, "Duplicate cinematic IDs");
Check(CinematicCatalog.All.Sum(x=>x.DurationSeconds)>=1660, "Reference duration baseline not reached");
Check(!CinematicCatalog.TryGet("missing", out _), "Unknown ID must not resolve");
try { CinematicCatalog.Get("missing"); failures.Add("Get must reject unknown ID"); } catch (ArgumentException) { }
var choreographies = new HashSet<string>();
foreach (var definition in CinematicCatalog.All)
{
    Check(ReferenceEquals(definition, CinematicCatalog.Get(definition.Id)), "Get identity mismatch: " + definition.Id);
    Check(definition.BikeIndex is >=0 and <15 && definition.CharacterIndex is >=0 and <8, "Invalid actor asset index");
    Check(definition.AudioId==definition.MusicId && !string.IsNullOrWhiteSpace(definition.AudioId), "Missing music binding");
    Check(definition.Beats.Count>=4, "Insufficient direction: " + definition.Id);
    float cursor=0;
    var choreography = new StringBuilder().Append(definition.BikeIndex).Append('|').Append(definition.CharacterIndex);
    foreach (var beat in definition.Beats)
    {
        checkedBeats++;
        Check(MathF.Abs(beat.StartSeconds-cursor)<.001f, "Beat gap or overlap: " + definition.Id);
        Check(beat.DurationSeconds>.6f && beat.DurationSeconds<12, "Static hold or invalid duration: " + definition.Id);
        Check(beat.EndSeconds<=definition.DurationSeconds+.001f, "Beat exceeds sequence: " + definition.Id);
        Check(beat.FieldOfViewFrom is >=25 and <=75 && beat.FieldOfViewTo is >=25 and <=75, "Invalid framing FOV");
        Check(beat.CameraFrom.Y>.1f && beat.CameraTo.Y>.1f, "Camera is underground");
        Check(beat.Actors.Count>0 && beat.Actors.Select(x=>x.Slot).Distinct().Count()==beat.Actors.Count, "Invalid participant slots");
        Check(beat.Actors.Any(x=>x.Slot==beat.SpeakerSlot), "Speaker missing from stage");
        Check(!string.IsNullOrWhiteSpace(beat.Dialogue), "Undirected empty beat");
        choreography.Append('|').Append(beat.Shot).Append(':').Append(beat.CameraFrom.X).Append(':').Append(beat.DurationSeconds);
        foreach (var actor in beat.Actors)
        {
            checkedActorCues++;
            Check(actor.Slot is >=0 and <=3 && (beat.ParticipantMask & (1<<actor.Slot))!=0, "Participant mask mismatch");
            Check(actions.Contains(actor.Action), "Unknown director action: " + actor.Action);
            Check(actor.PositionFrom.Y>=0 && actor.PositionTo.Y>=0, "Actor below stage");
            choreography.Append(':').Append(actor.Action).Append(':').Append(actor.PositionTo.Z);
        }
        cursor=beat.EndSeconds;
    }
    Check(MathF.Abs(cursor-definition.DurationSeconds)<.001f, "Final duration not exactly covered: " + definition.Id);
    Check(choreographies.Add(Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(choreography.ToString())))), "Identical asset/choreography timing: " + definition.Id);
}
foreach (var pair in expected)
{
    Check(CinematicCatalog.ForRole(pair.Key).Count==pair.Value, "Role count mismatch: " + pair.Key);
    Check(CinematicCatalog.ForEvent(pair.Key, int.MinValue).Role==pair.Key, "Negative event variant failed");
}
var result = new {
    passed=failures.Count==0, sequenceCount=CinematicCatalog.All.Count, beatCount=checkedBeats,
    actorCueCount=checkedActorCues, totalSeconds=CinematicCatalog.All.Sum(x=>x.DurationSeconds),
    uniqueAssetChoreographySignatures=choreographies.Count, failures,
    scope="Compiled C# identity, timing, camera/actor bounds, role counts, supported actions and lookup checks; visual playback and subjective story quality remain pending."
};
Console.WriteLine(JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented=true }));
if (args.Length==1) File.WriteAllText(args[0], JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented=true }) + Environment.NewLine);
return failures.Count==0 ? 0 : 1;
