using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using RacingBois.Gameplay.Definitions;

string root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../../../"));
if (!File.Exists(Path.Combine(root,"AGENTS.md"))) root = Directory.GetCurrentDirectory();
string tracePath = Path.Combine(root,"docs/p10/network/20260927T003126Z/probe.json");
using var trace = JsonDocument.Parse(File.ReadAllText(tracePath));
using var frozen = JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"tools/p10/pose-envelope-staging/production-before.json")));
var results = new List<object>(); var details = new List<object>(); int failures = 0;
void Check(bool condition,string message) { if(!condition)throw new InvalidOperationException(message); }
void Test(string name,Action action)
{
    try { action();results.Add(new{name,passed=true}); }
    catch(Exception error){failures++;results.Add(new{name,passed=false,error=error.Message});Console.WriteLine("FAIL "+name+": "+error.Message);}
}
string Hash(string file)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(file))).ToLowerInvariant();
bool FrozenMatches()=>frozen.RootElement.GetProperty("sources").EnumerateObject().All(p=>Hash(Path.Combine(root,p.Name))==p.Value.GetString());
Test("all163_frozen_sources_match_before",()=>Check(FrozenMatches(),"Frozen source drift before test"));
Test("real_f_wan_trace_hash_matches",()=>Check(Hash(tracePath)==frozen.RootElement.GetProperty("trace").GetProperty("sha256").GetString(),"Trace drift"));
var episodes=trace.RootElement.GetProperty("correctionTrace").GetProperty("episodes").EnumerateArray().ToArray();
Check(episodes.Length==39,"Expected the actual39 retained episodes");
for(int index=0;index<episodes.Length;index++)
{
    var episode=episodes[index];string label="episode_"+index.ToString("D2");
    foreach(string side in new[]{"Before","After"})
    Test(label+"_unchanged_production_replay_and_state_"+side,()=>
    {
        var state=episode.GetProperty(side);var clock=new FixtureClock{NowSeconds=state.GetProperty("At").GetDouble()};
        using var session=new MultiplayerSession(new NoNetwork(),new NoWire(),clock,null);
        session.SeedPresentation(state);session.SetFixtureEvents(state);
        Check(session.PresentationSessionEpoch==state.GetProperty("SessionEpoch").GetInt32(),"Read-only presentation lease differs from actual session epoch");
        string before=session.GameplayDigest();float raw=session.LastCorrectionMeters,maximum=session.MaximumCorrectionMeters;
        session.SamplePresentation();var sampled=session.LocalRider;
        var track=TrackDefinition.ForCourse(state.GetProperty("Course").GetInt32(),state.GetProperty("Level").GetInt32());
        var point=PoseGeometry.Point(track,sampled.LongitudinalMeters,sampled.LateralMeters,sampled.HeightMeters);
        var envelope=new VisualPoseEnvelope();envelope.Sample(point,Quaternion.Identity,clock.NowSeconds,100);
        envelope.Sample(point+Vector3.UnitY,Quaternion.Identity,clock.NowSeconds+.016,100,true);
        for(int step=1;step<40;step++)envelope.Sample(point+Vector3.UnitY,Quaternion.Identity,clock.NowSeconds+.016+step/60d,100);
        Check(session.GameplayDigest()==before,"Renderer changed authority/prediction/pending inputs");
        Check(session.LastCorrectionMeters==raw&&session.MaximumCorrectionMeters==maximum,"Renderer changed raw correction diagnostics");
        var authority=state.GetProperty("Authority");var publicRider=RemoteMotionSampler.Find(session.LatestAuthoritativeWorld.Riders,session.RiderId);
        Check(publicRider.Health==authority.GetProperty("Health").GetInt32()&&publicRider.BikeCondition==authority.GetProperty("BikeCondition").GetInt32()&&
              publicRider.Reward==authority.GetProperty("Reward").GetInt32()&&publicRider.Qualified==authority.GetProperty("Qualified").GetBoolean()&&
              publicRider.Mode==(RiderMode)authority.GetProperty("Mode").GetInt32()&&publicRider.Rank==authority.GetProperty("Rank").GetInt32()&&
              publicRider.FinishTick==authority.GetProperty("FinishTick").GetInt64(),"Public authoritative outcome changed");
    });
    var beforeState=episode.GetProperty("Before");var afterState=episode.GetProperty("After");
    var before=RecordedPose.Read(episode.GetProperty("PresentedBefore").GetProperty("Pose"),beforeState.GetProperty("Predicted"));
    var after=RecordedPose.Read(episode.GetProperty("PresentedAfter").GetProperty("Pose"),afterState.GetProperty("Predicted"));
    var track=TrackDefinition.ForCourse(beforeState.GetProperty("Course").GetInt32(),beforeState.GetProperty("Level").GetInt32());
    foreach(int fps in new[]{20,30,60,120})foreach(bool moving in new[]{false,true})
    Test(label+"_"+fps+"fps_"+(moving?"controlled_motion":"held_target"),()=>
    {
        var initial=PoseGeometry.Target(track,before);var target=PoseGeometry.Target(track,after);
        var rider=new VisualPoseEnvelope();var bike=new VisualPoseEnvelope();rider.Reset(initial.Rider,initial.RiderRotation,0);bike.Reset(initial.Bike,initial.BikeRotation,0);
        bool familyChanged=PoseGeometry.Detached(before.Mode)!=PoseGeometry.Detached(after.Mode);
        bool detachedCorrection=PoseGeometry.Detached(after.Mode)&&episode.GetProperty("Delta").GetDouble()>=1;
        Check(beforeState.GetProperty("Predicted").GetProperty("Tick").GetInt64()==afterState.GetProperty("Predicted").GetProperty("Tick").GetInt64(),"Retained correction is not equal-target");
        float riderBound=Math.Clamp(Math.Max(Math.Abs(before.Speed),Math.Abs(after.Speed))+10,10,100);
        double dt=1d/fps;var camera=PoseGeometry.Camera(track,before);var cameraPosition=camera.Position;
        var cameraRotation=PoseGeometry.LookRotation(camera.Look-camera.Position);Vector3 lastCameraOffset=Vector3.Zero;
        float firstRiderStep=0,firstBikeStep=0,maxRiderStep=0,maxBikeStep=0,maxCameraStep=0,maxCorrectionSpeed=0,maxOffset=0,minCameraDepth=float.PositiveInfinity;
        double settled=-1;Vector3 previousRiderOffset=Vector3.Zero,previousBikeOffset=Vector3.Zero;bool triggeredRider=false,triggeredBike=false;
        for(int frame=0;frame<=fps;frame++)
        {
            float seconds=(float)(frame*dt);float bikeSpeed=PoseGeometry.Detached(after.Mode)?Math.Max(0,after.BikeSpeed):after.Speed;
            var pose=after with{S=after.S+(moving?after.Speed*seconds:0),BikeS=after.BikeS+(moving?bikeSpeed*seconds:0)};
            var actual=PoseGeometry.Target(track,pose);var oldRider=rider.Position;var oldBike=bike.Position;var oldCamera=cameraPosition;
            double now=dt+frame*dt;
            rider.Sample(actual.Rider,actual.RiderRotation,now,riderBound,frame==0&&(familyChanged||detachedCorrection));
            bike.Sample(actual.Bike,actual.BikeRotation,now,100,frame==0&&(familyChanged||detachedCorrection));
            float rs=Vector3.Distance(oldRider,rider.Position),bs=Vector3.Distance(oldBike,bike.Position);
            if(frame==0)
            {
                firstRiderStep=rs;firstBikeStep=bs;triggeredRider=rider.BeganReconciliation;triggeredBike=bike.BeganReconciliation;
                if(triggeredRider)Check(rs<.00002,"Triggered rider envelope teleported on correction sample");
                if(triggeredBike)Check(bs<.00002,"Triggered bike envelope teleported on correction sample");
                if(familyChanged)Check(triggeredRider&&triggeredBike,"Observed attached/detached crossing was not caught");
            }
            else
            {
                float speed=Math.Max(Vector3.Distance(previousRiderOffset,rider.PositionOffset),Vector3.Distance(previousBikeOffset,bike.PositionOffset))/(float)dt;
                maxCorrectionSpeed=Math.Max(maxCorrectionSpeed,speed);
                Check(speed<=VisualPoseEnvelope.MaximumCorrectionSpeed+.03,"Additional correction velocity exceeded bound");
            }
            maxRiderStep=Math.Max(maxRiderStep,rs);maxBikeStep=Math.Max(maxBikeStep,bs);
            maxOffset=Math.Max(maxOffset,Math.Max(rider.PositionOffset.Length(),bike.PositionOffset.Length()));
            Check(maxOffset<=VisualPoseEnvelope.MaximumOffsetMeters+.001,"Visible error exceeded spatial bound");
            var desired=PoseGeometry.Camera(track,pose);Vector3 rawCamera=cameraPosition-lastCameraOffset;
            if(rider.BeganReconciliation)rawCamera+=rider.RawTargetShift;
            if(rider.ResetThisSample)rawCamera=desired.Position;
            float blend=1-MathF.Exp(-7*(float)dt);
            cameraPosition=Vector3.Lerp(rawCamera,desired.Position,blend)+rider.PositionOffset;
            cameraRotation=Quaternion.Slerp(cameraRotation,PoseGeometry.LookRotation(desired.Look-desired.Position),blend);
            minCameraDepth=Math.Min(minCameraDepth,Vector3.Transform(rider.Position-cameraPosition,Quaternion.Inverse(cameraRotation)).Z);
            maxCameraStep=Math.Max(maxCameraStep,Vector3.Distance(cameraPosition,oldCamera));lastCameraOffset=rider.PositionOffset;
            previousRiderOffset=rider.PositionOffset;previousBikeOffset=bike.PositionOffset;
            Check(float.IsFinite(rider.Position.LengthSquared())&&float.IsFinite(bike.Position.LengthSquared()),"Nonfinite visual pose");
            if(settled<0&&rider.RemainingSeconds==0&&bike.RemainingSeconds==0)settled=frame*dt;
        }
        Check(rider.HardResetCount==0&&bike.HardResetCount==0,"Known isolated episode unexpectedly exceeded envelope budget");
        Check(settled>=0&&settled<=VisualPoseEnvelope.MaximumDurationSeconds+dt+.0001,"Envelope failed to converge within finite window");
        Check(rider.PositionOffset==Vector3.Zero&&bike.PositionOffset==Vector3.Zero,"Residual offset did not reach exact zero");
        Check(minCameraDepth>.12,"Controlled camera crossed the rider root near plane");
        details.Add(new{episode=index,fps,moving,familyChanged,detachedCorrection,rawCorrectionMeters=episode.GetProperty("Delta").GetDouble(),
            actualRecordedPresentedDeltaMeters=episode.GetProperty("PresentedDelta").GetDouble(),
            rawRiderRootShiftMeters=Vector3.Distance(initial.Rider,target.Rider),rawBikeRootShiftMeters=Vector3.Distance(initial.Bike,target.Bike),
            triggeredRider,triggeredBike,firstRiderStep,firstBikeStep,maxRiderStep,maxBikeStep,maxCameraStep,maxCorrectionSpeed,maxOffset,settledSeconds=settled,minCameraDepth,
            scope="Recorded presented S/D/H/mode pair plus full-checkpoint bike height/lean and source-bound stage formulas. A synthetic once-only revision represents this real retained equal-target correction; f did not record this new metadata. Continuation and initial camera are controlled assumptions, not captured Unity frames."});
    });
}

Test("ordinary_motion_remains_direct_at_all_frame_rates",()=>
{
    foreach(int fps in new[]{20,30,60,120})
    {
        var value=new VisualPoseEnvelope();
        for(int frame=0;frame<fps*5;frame++)
        {float s=frame*55f/fps;var target=new Vector3(s,MathF.Sin(s*.02f),s*.1f);value.Sample(target,Quaternion.Identity,frame/(double)fps,65);Check(value.Position==target,"Ordinary motion gained delay");}
        Check(value.ReconciliationCount==0,"Ordinary movement triggered envelope");
    }
});
Test("same_mode_vertical_and_independent_bike_correction",()=>
{
    var rider=new VisualPoseEnvelope();var bike=new VisualPoseEnvelope();rider.Reset(Vector3.Zero,Quaternion.Identity,0);bike.Reset(Vector3.Zero,Quaternion.Identity,0);
    rider.Sample(new Vector3(0,2,0),Quaternion.Identity,.01,10);bike.Sample(new Vector3(3,0,0),Quaternion.Identity,.01,10);
    Check(rider.Position==Vector3.Zero&&bike.Position==Vector3.Zero,"Independent XYZ correction jumped");
    Check(rider.PositionOffset!=bike.PositionOffset,"Rider and bike incorrectly share one offset");
});
Test("over_budget_teleport_resets_without_clamping_target",()=>
{
    var value=new VisualPoseEnvelope();value.Reset(Vector3.Zero,Quaternion.Identity,0);var target=new Vector3(80,2,30);
    value.Sample(target,Quaternion.Identity,.01,100,true);
    Check(value.Position==target&&value.ResetReason==VisualPoseResetReason.Teleport&&value.PositionOffset==Vector3.Zero,"Teleport retained a misleading offset");
});
Test("repeated_corrections_cannot_extend_forever",()=>
{
    var value=new VisualPoseEnvelope();value.Reset(Vector3.Zero,Quaternion.Identity,0);bool budgetReset=false;
    for(int i=1;i<=60;i++)
    {value.Sample(new Vector3(3+i*.05f,0,0),Quaternion.Identity,i*.04,10,true);budgetReset|=value.ResetReason==VisualPoseResetReason.BurstBudget;Check(value.PositionOffset.Length()<=10,"Repeated offset escaped bound");}
    Check(budgetReset,"Repeated corrections hid persistent error indefinitely");
});
Test("scope_reset_and_long_frozen_resume_clear_offsets",()=>
{
    var value=new VisualPoseEnvelope();value.Reset(Vector3.Zero,Quaternion.Identity,0);value.Sample(new Vector3(5,0,0),Quaternion.Identity,.01,100,true);
    var held=value.Position;value.Sample(new Vector3(5,0,0),Quaternion.Identity,.02,100,frozen:true);
    value.Sample(new Vector3(5,0,0),Quaternion.Identity,.30,100,frozen:true);Check(value.Position==held,"Frozen presentation drifted");
    value.Sample(new Vector3(6,0,0),Quaternion.Identity,.31,100);Check(value.ResetReason==VisualPoseResetReason.FrozenResume&&value.Position.X==6,"Long resume kept old correction");
    value.Sample(new Vector3(3,0,0),Quaternion.Identity,.32,100,true);value.Sample(new Vector3(200,1,2),Quaternion.Identity,.33,100,reset:true);
    Check(value.Position==new Vector3(200,1,2)&&value.PositionOffset==Vector3.Zero,"Explicit epoch reset leaked a prior offset");
});
Test("clock_gap_and_rewind_are_explicit",()=>
{
    var value=new VisualPoseEnvelope();value.Reset(Vector3.Zero,Quaternion.Identity,2);value.Sample(Vector3.One,Quaternion.Identity,1,100);
    Check(value.ResetReason==VisualPoseResetReason.ClockRewind,"Clock rewind not reset");value.Sample(Vector3.One*2,Quaternion.Identity,2,100);
    Check(value.ResetReason==VisualPoseResetReason.ClockGap,"Large frame gap was silently smoothed");
});
Test("room_race_lease_and_rider_identity_require_new_envelope",()=>
{
    var first=new PresentationContinuityScope(2,5,"room-a",101,false);
    Check(first.SameIdentity(new PresentationContinuityScope(2,5,"room-a",101,true)),"Freeze incorrectly changes identity");
    foreach(var other in new[]{new PresentationContinuityScope(3,5,"room-a",101,false),new PresentationContinuityScope(2,6,"room-a",101,false),
        new PresentationContinuityScope(2,5,"room-b",101,false),new PresentationContinuityScope(2,5,"room-a",102,false),default})
        Check(!first.SameIdentity(other),"Room/race/lease/rider lifetime reused a stale correction");
});
Test("detached_observation_triggers_once_without_ordinary_riding_lag",()=>
{
    var observation=new PresentationContinuityScope(2,5,"room",101,false,17,3.9f);
    Check(observation.DetachedCorrectionSince(16,true),"New detached correction was lost");
    Check(!observation.DetachedCorrectionSince(17,true),"Same observation rebased every frame");
    Check(!observation.DetachedCorrectionSince(16,false),"Ordinary riding was delayed");
    Check(!new PresentationContinuityScope(2,5,"room",101,false,18,.2f).DetachedCorrectionSince(17,true),"Quantization rebased detached body");
});
Test("invalid_data_rejected_without_position_mutation",()=>
{
    var value=new VisualPoseEnvelope();value.Reset(Vector3.One,Quaternion.Identity,0);
    foreach(var bad in new[]{new Vector3(float.NaN,0,0),new Vector3(0,float.PositiveInfinity,0),new Vector3(float.MaxValue,0,0)})
    {bool rejected=false;try{value.Sample(bad,Quaternion.Identity,.01,100);}catch(ArgumentException){rejected=true;}Check(rejected&&value.Position==Vector3.One,"Invalid position changed display");}
    bool qRejected=false;try{value.Sample(Vector3.Zero,new Quaternion(0,0,0,0),.01,100);}catch(ArgumentException){qRejected=true;}Check(qRejected,"Zero quaternion accepted");
    foreach(double bad in new[]{double.NaN,double.PositiveInfinity,-1d})
    {bool rejected=false;try{value.Sample(Vector3.Zero,Quaternion.Identity,bad,100);}catch(ArgumentException){rejected=true;}Check(rejected&&value.Position==Vector3.One,"Invalid clock changed display");}
});
Test("short_freeze_holds_both_roots_and_resumes_without_jump",()=>
{
    var value=new VisualPoseEnvelope();value.Reset(Vector3.Zero,Quaternion.Identity,0);value.Sample(new Vector3(5,0,0),Quaternion.Identity,.01,100,true);
    value.Sample(new Vector3(5,0,0),Quaternion.Identity,.03,100);var held=value.Position;
    value.Sample(new Vector3(5,0,0),Quaternion.Identity,.04,100,frozen:true);
    value.Sample(new Vector3(5,0,0),Quaternion.Identity,.09,100,frozen:true);Check(value.Position==held,"Short freeze drift");
    value.Sample(new Vector3(5.2f,0,0),Quaternion.Identity,.10,100);Check(value.Position==held&&value.BeganReconciliation,"Short resume jumped");
});
Test("separate_instances_do_not_share_correction_state",()=>
{
    var first=new VisualPoseEnvelope();var second=new VisualPoseEnvelope();first.Reset(Vector3.Zero,Quaternion.Identity,0);second.Reset(Vector3.One,Quaternion.Identity,0);
    first.Sample(new Vector3(4,0,0),Quaternion.Identity,.01,100,true);
    Check(second.Position==Vector3.One&&second.PositionOffset==Vector3.Zero&&second.ReconciliationCount==0,"One rider changed another envelope");
});
Test("pure_envelope_steady_sampling_allocates_no_managed_heap",()=>
{
    var value=new VisualPoseEnvelope();
    for(int i=0;i<1024;i++)value.Sample(new Vector3(i*.8f,0,0),Quaternion.Identity,i/60d,60);
    long before=GC.GetAllocatedBytesForCurrentThread();
    for(int i=1024;i<13024;i++)value.Sample(new Vector3(i*.8f,0,0),Quaternion.Identity,i/60d,60);
    Check(GC.GetAllocatedBytesForCurrentThread()==before,"Pure steady envelope allocated managed memory");
});
Test("all163_frozen_sources_match_after",()=>Check(FrozenMatches(),"Frozen source drift during test"));
string output=args.Length>0?args[0]:"docs/p10/pose-envelope-staging/validation.json";
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output,JsonSerializer.Serialize(new{passed=failures==0,failures,tests=results.Count,results,details,
    trace=tracePath,traceSha256=Hash(tracePath),episodes=episodes.Length,productionApplied=false,nativeUnityRendered=false,
    rawDiagnosticScope="Original correction magnitudes/outcomes/authority checkpoints are unchanged. No raw acceptance threshold was widened.",
    limits="Generated step/constant-motion continuations and reconstructed camera are mathematics only; clipping, animation/VFX alignment and perceived comfort require actual rendered Unity QA."},new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine($"POSE ENVELOPE {(failures==0?"PASS":"FAIL")} {results.Count-failures}/{results.Count}; episodes{episodes.Length}; scenarios{details.Count}");
return failures==0?0:1;

sealed class FixtureClock:IMonotonicClock{public double NowSeconds{get;set;}}
sealed class NoNetwork:IRealtimeTransport
{
    public event Action Opened{add{}remove{}}public event Action<string> Message{add{}remove{}}public event Action<string> Closed{add{}remove{}}
    public void Connect(string endpoint)=>throw new InvalidOperationException("Network forbidden in fixture");
    public void Send(string text)=>throw new InvalidOperationException("Network forbidden in fixture");
    public void Close(){}public void Poll(){}public void Dispose(){}
}
sealed class NoWire:IWireCodec{public string Encode(object value)=>throw new InvalidOperationException();public T Decode<T>(string text)where T:class=>throw new InvalidOperationException();}
