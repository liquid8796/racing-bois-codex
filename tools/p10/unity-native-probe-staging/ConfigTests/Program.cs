using RacingBois.Diagnostics.NativeProbe;
using System.Text.Json;
var rows=new List<object>();int failed=0;
void Test(string name,Action action){try{action();rows.Add(new{name,passed=true});}catch(Exception e){failed++;rows.Add(new{name,passed=false,error=e.GetType().Name});}}
void Check(bool yes){if(!yes)throw new InvalidOperationException();}
string[] Valid(string endpoint="wss://localhost:7443/multiplayer")=>new[]{"probe.exe","--rb-native-probe","--rb-native-endpoint",endpoint,"--rb-native-report",Path.GetFullPath("_local/native-probe-config-test.json"),"--rb-native-fingerprint",new string('a',64)};
void Reject(string[] input){bool rejected=false;try{NativeProbeConfiguration.Parse(input);}catch(ArgumentException){rejected=true;}Check(rejected);}
Test("no_flag_no_connection_configuration",()=>Check(!NativeProbeConfiguration.Parse(new[]{"probe.exe","-batchmode"}).Enabled));
Test("explicit_wss_defaults_and_hash",()=>{var x=NativeProbeConfiguration.Parse(Valid());Check(x.Enabled&&x.Seconds==90&&x.Endpoint=="wss://localhost:7443/multiplayer");});
Test("ws_and_wrong_routes_rejected",()=>{foreach(var url in new[]{"ws://localhost/multiplayer","https://localhost/multiplayer","wss://localhost/other","wss://localhost/multiplayer?token=x","wss://user:pass@localhost/multiplayer","wss://localhost/multiplayer#secret"})Reject(Valid(url));});
Test("custom_options_require_opt_in",()=>Reject(Valid().Where(a=>a!="--rb-native-probe").ToArray()));
Test("duplicate_and_unknown_options_rejected",()=>{Reject(Valid().Concat(new[]{"--rb-native-probe"}).ToArray());Reject(Valid().Concat(new[]{"--rb-native-unsafe-cert","true"}).ToArray());});
Test("duration_boundaries",()=>{foreach(int n in new[]{60,600})Check(NativeProbeConfiguration.Parse(Valid().Concat(new[]{"--rb-native-seconds",n.ToString()}).ToArray()).Seconds==n);foreach(string n in new[]{"0","59","601","-1","NaN"})Reject(Valid().Concat(new[]{"--rb-native-seconds",n}).ToArray());});
Test("absolute_report_and_fingerprint_required",()=>{var x=Valid();x[5]="relative.json";Reject(x);x=Valid();x[7]="bad";Reject(x);});
Test("unity_flags_do_not_enable_or_change_probe",()=>Check(NativeProbeConfiguration.Parse(Valid().Concat(new[]{"-batchmode","-nographics","-logFile","safe.log"}).ToArray()).Enabled));
string path=args.Length>0?args[0]:"_local/native-probe-config-tests.json";Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
File.WriteAllText(path,JsonSerializer.Serialize(new{passed=failed==0,tests=rows.Count,failed,results=rows,scope="Pure argument policy only; no Unity lifecycle/network execution."},new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine($"CONFIG {(failed==0?"PASS":"FAIL")} {rows.Count} groups");return failed==0?0:1;
