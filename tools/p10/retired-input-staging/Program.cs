using System.Reflection;
using System.Text.Json;
using RacingBois.Client.Application;
using RacingBois.Gameplay.Definitions;
using RacingBois.Protocol;

var rows=new List<object>();var details=new List<object>();int failed=0;
void Check(bool ok,string why){if(!ok)throw new InvalidOperationException(why);}
void Test(string name,Action action){try{action();rows.Add(new{name,passed=true});Console.WriteLine("PASS "+name);}catch(Exception e){failed++;rows.Add(new{name,passed=false,error=e.Message});Console.WriteLine("FAIL "+name+": "+e.Message);}}
TestNetwork Network(int delay=0)=>new TestNetwork(delay){JitterSeconds=0,BlockClientUntil=0,InputController=null};
Test("real_delayed_inputs_follow_confirmed_results_without_persistent_user_error",()=>
{
    var net=Network(250);var peer=net.Add("Turnover fixture");peer.BlockUplinkUntil=0;peer.Attack=0;net.PrepareRace(peer);
    long resultLobbySequence=-1;int errors=0;bool order=true,backSent=false;int settled=0;var evidence=new List<object>();
    peer.Message+=text=>
    {
        string kind=net.Codec.Decode<MessageEnvelope>(text).kind;
        if(kind=="mpLobby"){var lobby=net.Codec.Decode<MpLobby>(text);if(lobby.state==(int)MultiplayerRoomState.Results)resultLobbySequence=lobby.reliableSequence;}
        if(kind!="mpError")return;var error=net.Codec.Decode<MpError>(text);if(error.code!="race_epoch")return;
        errors++;order&=resultLobbySequence>0&&error.reliableSequence>resultLobbySequence&&error.sequence>0&&error.requestId==0&&!error.terminal;
        if(evidence.Count<32)evidence.Add(new{at=net.Clock.NowSeconds,error.sequence,error.reliableSequence,resultLobbySequence,phase=peer.Session.Room?.Phase.ToString(),userErrorPresent=peer.Session.Error.Length>0});
    };
    net.InputController=who=>
    {
        var rider=who.Session.LocalRider;var room=who.Session.Room;
        var track=TrackDefinition.ForCourse(room?.CourseIndex??0,room?.LevelIndex??0);float speed=rider.SpeedMetersPerSecond*1000;
        float lateral=Math.Clamp((-1.8f-rider.LateralMeters)*2000,-6500,6500);
        who.Throttle=1;who.Steer=Math.Clamp((lateral+speed*track.CurvatureAt((long)(rider.LongitudinalMeters*1000))/100000)/(1200+speed/6),-1,1);
    };
    for(int tick=0;tick<20000;tick++)
    {
        net.Run(1);
        if(peer.Session.Room?.Phase==LobbyPhase.Results&&peer.Session.Result!=null&&!backSent){peer.Session.ReturnToLobby();backSent=true;}
        if(backSent&&peer.Session.Room?.Phase==LobbyPhase.Lobby&&++settled>=90)break;
    }
    details.Add(new{kind="actualServerTurnover",errors,order,evidence,finalPhase=peer.Session.Room?.Phase.ToString(),userError=peer.Session.Error.Length==0?"none":"present"});
    Check(backSent&&settled>=90,"Real driving inputs did not complete a race and return to lobby.");
    Check(errors>0&&order,"No proven post-Results in-flight input rejection ordering.");
    Check(peer.Session.Status==SessionStatus.Connected&&!peer.Session.IsReconnecting&&peer.Session.Error=="","Expected retired inputs polluted persistent Session.Error.");
});
#if CANDIDATE
object Field(object target,string name)=>target.GetType().GetField(name,BindingFlags.Instance|BindingFlags.NonPublic)!.GetValue(target)!;
void SetField(object target,string name,object value)=>target.GetType().GetField(name,BindingFlags.Instance|BindingFlags.NonPublic)!.SetValue(target,value);
(TestNetwork,TestPeer) Setup()
{
    var net=Network();var peer=net.Add("Scope fixture");peer.BlockUplinkUntil=0;peer.Attack=0;net.PrepareRace(peer);
    SetField(peer.Session,"sequence",30);SetField(peer.Session,"processedSequence",20);
    typeof(MultiplayerSession).GetMethod("RetireRaceInputs",BindingFlags.Instance|BindingFlags.NonPublic)!.Invoke(peer.Session,null);
    Phase(peer,LobbyPhase.Results);return(net,peer);
}
void Phase(TestPeer peer,LobbyPhase phase,int epochDelta=0,string roomOverride=null)
{
    var room=peer.Session.Room;var value=new LobbyReadModel(roomOverride??room.RoomId,room.Code,room.Name,room.HostPlayerId,room.MatchId,phase,
        room.Revision,room.RaceEpoch+epochDelta,room.BotCount,room.MaxPlayers,room.StartServiceTick,room.Members.ToArray(),room.PublicRoom,room.CourseIndex,room.LevelIndex);
    typeof(MultiplayerSession).GetProperty("Room")!.SetValue(peer.Session,value);
}
MpError Error(TestPeer peer,int input=25,int request=0,bool terminal=false,string code="race_epoch")=>new MpError{code=code,message=code,sequence=input,requestId=request,terminal=terminal,
    sessionEpoch=(int)Field(peer.Session,"sessionEpoch"),reliableSequence=(long)Field(peer.Session,"reliableSequence")+1};
Test("retired_input_ack_cursor_advances_without_erasing_unrelated_error",()=>
{
    var (_,peer)=Setup();var error=Error(peer);peer.Inject(error);Check(peer.Session.Error==""&&(long)Field(peer.Session,"reliableSequence")==error.reliableSequence,"Retired rejection was not consumed/acknowledged.");
    typeof(MultiplayerSession).GetProperty("Error")!.SetValue(peer.Session,"Unrelated existing error");error=Error(peer);peer.Inject(error);
    Check(peer.Session.Error=="Unrelated existing error"&&(long)Field(peer.Session,"reliableSequence")==error.reliableSequence,"Ignoring retired input erased another error or reliable cursor.");
});
Test("running_race_mismatch_remains_visible",()=>{var(_,peer)=Setup();Phase(peer,LobbyPhase.Racing);peer.Inject(Error(peer));Check(peer.Session.Error.Contains("race_epoch"),"Running-race error hidden.");});
Test("unknown_or_acknowledged_input_sequences_remain_visible",()=>
{
    foreach(int input in new[]{0,20,31,int.MaxValue}){var(_,peer)=Setup();peer.Inject(Error(peer,input));Check(peer.Session.Error.Contains("race_epoch"),"Unproven input range hidden: "+input);}
});
Test("control_terminal_and_other_error_codes_keep_original_behavior",()=>
{
    var(_,control)=Setup();control.Inject(Error(control,request:1));Check(control.Session.Error.Contains("race_epoch"),"Control error hidden.");
    var(_,terminal)=Setup();terminal.Inject(Error(terminal,terminal:true));Check(terminal.Session.Status==SessionStatus.Failed,"Terminal error hidden.");
    var(_,other)=Setup();other.Inject(Error(other,code:"input_sequence"));Check(other.Session.Error.Contains("input_sequence"),"Unrelated input error hidden.");
});
Test("countdown_sequence_overlap_and_any_new_input_remain_visible",()=>
{
    foreach(int newlySent in new[]{1,25,30})
    {var(_,peer)=Setup();Phase(peer,LobbyPhase.Countdown,1);SetField(peer.Session,"sequence",newlySent);peer.Inject(Error(peer));Check(peer.Session.Error.Contains("race_epoch"),"New-race ambiguity was suppressed.");}
    var(_,clear)=Setup();Phase(clear,LobbyPhase.Countdown,1);SetField(clear.Session,"sequence",0);clear.Inject(Error(clear));Check(clear.Session.Error=="","Unambiguous pre-input turnover error surfaced.");
});
Test("different_room_or_current_session_cannot_borrow_retired_range",()=>
{
    var(_,room)=Setup();Phase(room,LobbyPhase.Lobby,0,"other-room");room.Inject(Error(room));Check(room.Session.Error.Contains("race_epoch"),"Another room borrowed range.");
    var(_,session)=Setup();SetField(session.Session,"sessionEpoch",(int)Field(session.Session,"sessionEpoch")+1);session.Inject(Error(session));Check(session.Session.Error.Contains("race_epoch"),"Another session borrowed range.");
});
Test("ordinary_race_reset_discards_retired_context",()=>
{
    var(_,peer)=Setup();typeof(MultiplayerSession).GetMethod("ClearRace",BindingFlags.Instance|BindingFlags.NonPublic)!.Invoke(peer.Session,new object[]{false});
    Phase(peer,LobbyPhase.Results);peer.Inject(Error(peer));Check(peer.Session.Error.Contains("race_epoch"),"Reset retained old input range.");
});
#endif
string output=args.Length>0?args[0]:"_local/retired-input-tests.json";Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output,JsonSerializer.Serialize(new{schema=1,passed=failed==0,failed,tests=rows.Count,results=rows,details,scope="Isolated staged client plus actual server application and ordered latency fixture; raw errors remain observed. No live source/wire/server-policy changes."},new JsonSerializerOptions{WriteIndented=true}));return failed==0?0:1;
