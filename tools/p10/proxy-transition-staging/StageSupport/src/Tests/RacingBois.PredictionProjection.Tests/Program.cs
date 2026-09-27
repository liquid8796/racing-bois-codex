using System.Reflection;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.NetworkMapping;
using RacingBois.Protocol;
using RacingBois.Simulation;

var rows=new List<object>();int failed=0;
void Check(bool ok,string why){if(!ok)throw new InvalidOperationException(why);}
void Test(string name,Action act){try{act();rows.Add(new{name,passed=true});Console.WriteLine("PASS "+name);}catch(Exception e){failed++;rows.Add(new{name,passed=false,error=e.Message});Console.WriteLine("FAIL "+name+": "+e.Message);}}
void Reject(Action act){bool rejected=false;try{act();}catch(ArgumentException){rejected=true;}Check(rejected,"Invalid context accepted.");}
MpSnapshot Packet()
{
    var w=RaceSimulation.CreateDefault(1996,0);var r=RaceSimulation.AddPlayer(w,1);
    return new MpSnapshot{tick=100,resolvedThroughTick=100,riderId=1,own=CheckpointMapper.CaptureDto(r,100),lastAppliedInputTick=100,serverServiceTick=280,
        level=0,courseIndex=0,trackLengthMillimeters=w.Track.LengthMillimeters,
        pedestrians=new[]{new NumericRow{values=new[]{4008,10000,0,0,0,0,59,1,1,60,1237,59}}}};
}
MultiplayerSnapshotReadModel Project(MpSnapshot m)=>MultiplayerProjection.World(m,0,0,Array.Empty<RaceEventReadModel>());
Test("protocol6_context_reaches_predictor_without_speed_quantization_loss",()=>
{
    var packet=Packet();var projected=Project(packet);var metadata=projected.PedestrianContexts[4008];
    Check(MultiplayerProtocol.Version==6 && metadata.WaitTicks==60 && metadata.DesiredWalkingSpeed==1237 && metadata.MotionRemainder==59,"Context was truncated.");
    var n=new PredictionNeighbors();PredictionNeighborBuilder.Fill(n,projected.World,null,1,projected.CollisionUntilByRider,projected.PedestrianContexts,projected.RiderCombatContexts);
    Check(PedestrianCheckpoints.CapturePredictionContext(n.Pedestrians[0]).DesiredWalkingSpeed==1237,"Proxy lost exact desired speed.");
    var predictor=new RiderPredictor(0);predictor.SetNeighbors(n);predictor.Restore(CheckpointMapper.ToCheckpoint(packet.own));predictor.Advance(101,default);
    var sandbox=(GameplayWorld)typeof(RiderPredictor).GetField("sandbox",BindingFlags.Instance|BindingFlags.NonPublic)!.GetValue(predictor)!;var p=sandbox.Pedestrians[0];
    Check(p.Mode==PedestrianMode.Walking && p.ModeAgeTicks==0 && p.WalkingSpeedMillimetersPerSecond==1237 && p.LateralMillimeters==21 && p.MotionRemainder==36,"Exact waiting transition/motion integration lost metadata.");
    packet.pedestrians[0].values[9]=359;Check(projected.PedestrianContexts[4008].WaitTicks==60,"Wire array aliased immutable context.");
});
Test("cm_visual_velocity_and_exact_desired_velocity_have_consistent_units",()=>
{
    foreach(int facing in new[]{-1,1})
    {var m=Packet();var v=m.pedestrians[0].values;v[4]=facing*123;v[5]=1;v[6]=5;v[7]=facing;var p=Project(m);Check(p.PedestrianContexts[4008].DesiredWalkingSpeed==1237,"Exact speed lost.");v[4]=facing*124;Reject(()=>Project(m));}
});
Test("hostile_or_incoherent_pedestrian_metadata_rejected",()=>
{
    foreach(var pair in new[]{(9,59),(9,360),(10,1199),(10,1601),(11,-60),(11,60),(7,0),(7,int.MaxValue),(6,60)})
    {var m=Packet();m.pedestrians[0].values[pair.Item1]=pair.Item2;Reject(()=>Project(m));}
    var stumbled=Packet();stumbled.pedestrians[0].values[5]=2;stumbled.pedestrians[0].values[6]=180;Reject(()=>Project(stumbled));
    var wrongWalking=Packet();wrongWalking.pedestrians[0].values[5]=1;wrongWalking.pedestrians[0].values[4]=123;wrongWalking.pedestrians[0].values[6]=300;wrongWalking.pedestrians[0].values[8]=0;Reject(()=>Project(wrongWalking));
});
Test("old_protocol_and_pedestrian_row_shapes_fail_closed",()=>
{
    foreach(int count in new[]{9,10,11,13}){var p=Packet();Array.Resize(ref p.pedestrians[0].values,count);Reject(()=>Project(p));}
    var old=Packet();old.protocolVersion=5;Reject(()=>Project(old));
    var duplicate=Packet();duplicate.pedestrians=new[]{duplicate.pedestrians[0],duplicate.pedestrians[0]};Reject(()=>Project(duplicate));
});
Test("missing_prediction_context_is_atomic",()=>
{
    var p=Project(Packet());var target=new PredictionNeighbors{PedestrianCount=1};
    Reject(()=>PredictionNeighborBuilder.Fill(target,p.World,null,1,p.CollisionUntilByRider,new Dictionary<int,PedestrianPredictionContext>(),p.RiderCombatContexts));Check(target.PedestrianCount==1,"Partial proxy mutation occurred.");
});
Test("authority_private_context_capture_is_validated_and_value_only",()=>
{
    var p=new RacePedestrian{WaitTicks=359,DesiredWalkingSpeed=1600,MotionRemainder=-59};var context=PedestrianCheckpoints.CapturePredictionContext(p);p.WaitTicks=60;
    Check(context.WaitTicks==359,"Live private state aliased context.");var copy=new RacePedestrian();PedestrianCheckpoints.RestorePredictionContext(copy,context);Check(copy.WaitTicks==359&&copy.DesiredWalkingSpeed==1600&&copy.MotionRemainder==-59,"Context restore lost fields.");
    p.DesiredWalkingSpeed=1601;Reject(()=>PedestrianCheckpoints.CapturePredictionContext(p));
});
MpSnapshot CombatPacket()
{
    var p=Packet();p.riders=new[]{new NumericRow{values=new[]{2001,2,1,1,1,10000,0,0,0,0,10000,0,0,4096,100,7,2,-1,0,0,1,7,7,1,0,0,0,744,0,90,300}}};return p;
}
Test("remote_combat_metadata_is_immutable_bounded_and_reaches_predictor",()=>
{
    var packet=CombatPacket();var p=Project(packet);var c=p.RiderCombatContexts[2001];
    Check(c.Endurance==744&&!c.AttackResolved&&c.HitUntilTick==190&&c.StealUntilTick==400,"Combat metadata changed units.");
    var n=new PredictionNeighbors();PredictionNeighborBuilder.Fill(n,p.World,null,1,p.CollisionUntilByRider,p.PedestrianContexts,p.RiderCombatContexts);
    var d=RiderCheckpoints.Capture(n.Riders[0],100).Data;Check(d.Endurance==744&&!d.AttackResolved&&d.HitUntilTick==190&&d.StealUntilTick==400,"Validated combat state was lost in neighbor projection.");
    packet.riders[0].values[27]=1000;packet.riders[0].values[28]=1;Check(p.RiderCombatContexts[2001].Endurance==744&&!p.RiderCombatContexts[2001].AttackResolved,"Wire mutation aliased context.");
    foreach(int e in new[]{500,1000})foreach(int hit in new[]{0,90})foreach(int steal in new[]{0,300})
    {var m=CombatPacket();m.riders[0].values[27]=e;m.riders[0].values[28]=1;m.riders[0].values[29]=hit;m.riders[0].values[30]=steal;Check(Project(m).RiderCombatContexts[2001].AttackResolved,"Valid boundary rejected.");}
});
Test("hostile_combat_metadata_and_legacy_shapes_fail_closed",()=>
{
    foreach(var pair in new[]{(27,499),(27,1001),(28,-1),(28,2),(29,-1),(29,91),(30,-1),(30,301)})
    {var m=CombatPacket();m.riders[0].values[pair.Item1]=pair.Item2;Reject(()=>Project(m));}
    foreach(int count in new[]{26,27,28,29,30,32}){var m=CombatPacket();Array.Resize(ref m.riders[0].values,count);Reject(()=>Project(m));}
    Reject(()=>new RiderCombatPredictionContext(long.MaxValue,1000,false,1,0));
    var p=Project(CombatPacket());var n=new PredictionNeighbors{RiderCount=1};
    Reject(()=>PredictionNeighborBuilder.Fill(n,p.World,null,1,p.CollisionUntilByRider,p.PedestrianContexts,new Dictionary<int,RiderCombatPredictionContext>()));Check(n.RiderCount==1,"Missing combat context partially mutated proxies.");
    var invalid=new Dictionary<int,RiderCombatPredictionContext>{{2001,default}};
    Reject(()=>PredictionNeighborBuilder.Fill(n,p.World,null,1,p.CollisionUntilByRider,p.PedestrianContexts,invalid));Check(n.RiderCount==1,"Invalid combat context partially mutated proxies.");
});
Test("predicted_fatal_pose_keeps_authority_health_inventory_and_outcome",()=>
{
    var p=Project(Packet());var authority=p.World.Riders.Single(r=>r.Id==1);var predicted=CheckpointMapper.ToCheckpoint(Packet().own).Data;
    predicted.Health=0;predicted.BikeCondition=0;predicted.Mode=RiderMode.Wrecked;predicted.Reward=999999;predicted.Qualified=true;predicted.FinishTick=101;
    var visual=RemoteMotionSampler.WithMotion(authority,new RiderCheckpoint(predicted));
    Check(visual.Mode==RiderMode.Falling&&visual.Health==authority.Health&&visual.BikeCondition==authority.BikeCondition&&visual.Reward==authority.Reward&&visual.Qualified==authority.Qualified&&visual.FinishTick==authority.FinishTick,"Predicted combat committed an authority outcome.");
});
Test("same_tick_remote_forecast_motion_preserves_authority_and_clears_on_restore",()=>
{
    var packet=CombatPacket();packet.pedestrians=Array.Empty<NumericRow>();var owner=packet.own.rider;owner.distanceMillimeters=owner.bikeDistanceMillimeters=100000;owner.mode=(int)RiderMode.Attacking;
    owner.weapon=owner.attackWeapon=(int)WeaponKind.Club;owner.attackSide=1;owner.attackAgeTicks=owner.modeAgeTicks=7;
    var row=packet.riders[0].values;row[2]=(int)RiderMode.Riding;row[6]=row[11]=150;row[13]=512;row[20]=row[21]=row[22]=0;row[26]=90;row[29]=0;
    var projected=Project(packet);var n=new PredictionNeighbors();PredictionNeighborBuilder.Fill(n,projected.World,null,1,projected.CollisionUntilByRider,projected.PedestrianContexts,projected.RiderCombatContexts);
    var predictor=new RiderPredictor(0);predictor.SetNeighbors(n);var checkpoint=CheckpointMapper.ToCheckpoint(packet.own);predictor.Restore(checkpoint);
    Check(!predictor.TryGetForecastedNeighborMotion(2001,100,out _),"An uncreated remote transition was exposed.");
    predictor.Advance(101,default);predictor.Advance(102,default);
    Check(predictor.TryGetForecastedNeighborMotion(2001,102,out var forecast)&&forecast.Data.Mode==RiderMode.Falling&&forecast.Data.ModeAgeTicks==1,"Created crash did not advance on shared recovery.");
    Check(!predictor.TryGetForecastedNeighborMotion(2001,101,out _),"Mismatched sample tick accepted.");
    var sampler=new RemoteMotionSampler();sampler.Add(projected.World);var auth=projected.World.Riders.Single(r=>r.Id==2001);
    var sampled=sampler.Sample(102,projected.World.Riders.Single(r=>r.Id==1),Array.Empty<RaceEventReadModel>(),predictor).Riders.Single(r=>r.Id==2001);
    Check(sampled.Mode==RiderMode.Falling&&sampled.Health==auth.Health&&sampled.BikeCondition==auth.BikeCondition&&sampled.Weapon==auth.Weapon&&sampled.Reward==auth.Reward,"Remote pose published predicted health/inventory/outcome.");
    var noForecast=sampler.Sample(102,projected.World.Riders.Single(r=>r.Id==1),Array.Empty<RaceEventReadModel>()).Riders.Single(r=>r.Id==2001);
    Check(noForecast.Mode==RiderMode.Riding,"Disabled forecast changed baseline remote state.");
    predictor.Restore(checkpoint);Check(!predictor.TryGetForecastedNeighborMotion(2001,100,out _),"Checkpoint restore retained a speculative transition.");
    n.Riders[0].Mode=RiderMode.Falling;predictor.Restore(checkpoint);predictor.Advance(101,default);
    Check(!predictor.TryGetForecastedNeighborMotion(2001,101,out _),"Old non-driving proxy with missing recovery context was claimed exact.");
    n.Riders[0].Mode=RiderMode.Riding;predictor.Restore(checkpoint);for(int tick=101;tick<=131;tick++)predictor.Advance(tick,default);
    Check(!predictor.TryGetForecastedNeighborMotion(2001,131,out _),"Remote pose outlived bounded forecast horizon.");
});
string output=args.Length>0?args[0]:"docs/p10/prediction-projection-regression.json";Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output,JsonSerializer.Serialize(new{schema=1,passed=failed==0,failed,tests=rows.Count,results=rows,scope="Actual protocol/client/foundation sources compiled together for value projection, hostile metadata and pose boundary tests; no live network, server or Unity acceptance."},new JsonSerializerOptions{WriteIndented=true}));
return failed==0?0:1;
