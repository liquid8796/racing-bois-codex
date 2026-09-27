using System.Text.Json;
using RacingBois.Diagnostics.NativeProbe;

var results = new List<object>();
void Check(bool value, string message) { if (!value) throw new Exception(message); }
void Test(string name, Action action) { try { action(); results.Add(new { name, passed = true }); } catch (Exception error) { results.Add(new { name, passed = false, error = error.Message }); } }
NativeProbeObservations Planned()
{
    var o = new NativeProbeObservations();
    o.State(0,"Connecting","Connecting","",false,0,0,0,0); o.Opened(1,"Connecting","Connecting");
    o.State(2,"Driving","Connected","",false,5,2,3,4); o.State(15,"Suspended","Offline","",false,0,2,3,4);
    o.PlanResume(); o.State(16,"Suspended","Connecting","Đang khôi phục phiên…",true,0,2,3,4);
    o.Opened(17,"Resuming","Connecting"); o.State(18,"Resuming","Connected","",false,0,2,3,4); return o;
}
Test("only_one_planned_resume_passes", () => { Check(Planned().OnlyPlannedReconnect,"Planned resume rejected"); });
Test("spontaneous_reconnect_after_resume_fails", () => { var o=Planned(); o.State(20,"Driving","Connecting","Mất xác nhận từ máy chủ.",true,0,8,3,12); o.Opened(21,"Driving","Connecting"); Check(!o.OnlyPlannedReconnect && o.unexpectedReconnectTransitions==1 && o.unexpectedConnectionOpens==1,"Unexpected reconnect passed"); });
Test("spontaneous_reconnect_before_planned_resume_fails", () => { var o=new NativeProbeObservations(); o.Opened(1,"Connecting","Connecting"); o.State(3,"Driving","Connecting","Kết nối bị gián đoạn.",true,0,0,0,0); o.Opened(4,"Driving","Connecting"); Check(!o.OnlyPlannedReconnect && o.unexpectedReconnectTransitions==1 && o.unexpectedConnectionOpens==1,"Unexpected pre-plan reconnect passed"); });
Test("repeated_state_notification_does_not_double_count", () => { var o=Planned(); o.State(20,"Driving","Connecting","Mất xác nhận từ máy chủ.",true,0,0,0,0); for(int i=0;i<100;i++)o.State(21,"Driving","Connecting","Mất xác nhận từ máy chủ.",true,0,0,0,0); Check(o.unexpectedReconnectTransitions==1 && o.sessionCodes.Single(c=>c.code=="ack_or_snapshot_stalled").count==1,"Repeated Changed inflated counts"); });
Test("allowlist_scrubs_unknown_data", () => { const string secret="private-token-not-to-serialize"; var o=Planned(); o.Closed(secret,1,"Driving","Connected"); o.ServerError(secret,1,"Driving","Connected"); o.State(1,"Driving","Connected","Máy chủ từ chối: "+secret,false,3,2,1,0); var json=JsonSerializer.Serialize(o,new JsonSerializerOptions {IncludeFields=true}); Check(!json.Contains(secret) && o.transportCodes[0].code=="other" && o.serverCodes[0].code=="other" && o.latestSessionCode=="server_other","Raw unknown value escaped"); });
Test("actual_close_and_input_codes_remain_distinct", () => { foreach(string code in new[]{"reliable_overflow","slow_reader","logout","heartbeat_timeout","session_replaced"})Check(NativeProbeObservations.TransportCode(code)==code,"Close code lost"); var o=Planned(); o.ServerError("input_late",1,"Driving","Connected"); o.ServerError("input_future",1,"Driving","Connected"); Check(o.serverCodes.Length==2,"Timing errors combined"); });
Test("bounded_lifecycle_and_previous_pending", () => { var o=Planned(); o.State(20,"Driving","Connected","",false,119,12,5,14); o.State(21,"Driving","Connecting","Mất xác nhận từ máy chủ.",true,0,12,5,14); Check(o.lifecycle.Last().previousPending==119 && o.maximumPending==119 && o.maximumLate==12 && o.maximumFuture==5,"Pre-reconnect values lost"); for(int i=0;i<10000;i++)o.Closed("slow_reader",i,"Driving","Connecting"); Check(o.lifecycle.Length==64 && o.transportCodes.Single().count==10000,"History is unbounded or count lost"); });
Test("exact_error_literals_no_fuzzy_matching", () => { Check(NativeProbeObservations.SessionCode("Thiếu thông điệp trạng thái. Đang khôi phục…")=="reliable_gap","Known literal missing"); Check(NativeProbeObservations.SessionCode("Đã đóng kết nối; máy chủ chưa xác nhận thoát phiên.")=="logout_ack_timeout","Logout cause missing"); Check(NativeProbeObservations.SessionCode("Mất xác nhận từ máy chủ. malicious_suffix")=="other","Unsafe fuzzy match"); });
string output=JsonSerializer.Serialize(new { passed=results.All(r=>(bool)r.GetType().GetProperty("passed")!.GetValue(r)!), tests=results.Count, results },new JsonSerializerOptions {WriteIndented=true});
Console.WriteLine(output); if(args.Length>0)File.WriteAllText(args[0],output); return results.All(r=>(bool)r.GetType().GetProperty("passed")!.GetValue(r)!)?0:1;
