using System.Numerics;
using System.Text.Json;
using RacingBois.Diagnostics.PoseEnvelopePreview;
using RacingBois.Diagnostics.PoseEnvelopePreview.Editor;

var results=new List<object>();int failures=0;
void Check(bool value,string message){if(!value)throw new InvalidOperationException(message);}
void Test(string name,Action action){try{action();results.Add(new{name,passed=true});}catch(Exception e){failures++;results.Add(new{name,passed=false,error=e.Message});Console.WriteLine("FAIL "+name+": "+e.Message);}}
var scratch=Path.GetFullPath(Path.Combine("_local","p10-pose-preview-tests",Guid.NewGuid().ToString("N")));
Directory.CreateDirectory(scratch);string fresh=Path.Combine(scratch,"never-created");
string[] Valid()=>new[]{"--rb-pose-preview","--rb-pose-output",fresh,"--rb-pose-fingerprint",new string('a',64)};
void Reject(string[] args){bool rejected=false;try{PreviewConfiguration.Parse(args);}catch(ArgumentException){rejected=true;}Check(rejected,"Invalid launch accepted");}
Test("disabled_has_no_output_side_effect",()=>{Check(!PreviewConfiguration.Parse(Array.Empty<string>()).Enabled,"Opted in by default");Check(!Directory.Exists(fresh),"Created output while disabled");});
Test("valid_bounded_preview",()=>{var c=PreviewConfiguration.Parse(Valid());Check(c.Enabled&&!c.Include20&&c.Output==fresh,"Valid configuration differs");Check(!Directory.Exists(fresh),"Parse created output");});
Test("20m_comparison_is_explicit",()=>Check(PreviewConfiguration.Parse(Valid().Concat(new[]{"--rb-pose-include20"}).ToArray()).Include20,"Explicit comparison lost"));
Test("options_without_optin_rejected",()=>Reject(Valid().Skip(1).ToArray()));
Test("duplicate_option_rejected",()=>Reject(Valid().Concat(new[]{"--rb-pose-preview"}).ToArray()));
Test("unknown_option_rejected",()=>Reject(Valid().Concat(new[]{"--rb-pose-unknown","x"}).ToArray()));
Test("relative_output_rejected",()=>{var a=Valid();a[2]="relative";Reject(a);});
Test("existing_output_rejected",()=>{var a=Valid();a[2]=scratch;Reject(a);});
Test("nonhex_fingerprint_rejected",()=>{var a=Valid();a[4]=new string('x',64);Reject(a);});
Test("missing_value_rejected",()=>Reject(new[]{"--rb-pose-preview","--rb-pose-output"}));
Test("empty_journal_performs_no_setters",()=>{var s=new PreviewBuildScope();Check(s.Restore().Length==0&&!s.Changed,"Preflight rejection changed state");});
Test("journal_arms_before_throwing_setter",()=>
{int value=7;var s=new PreviewBuildScope();try{s.Change("setting",()=>{value=8;throw new InvalidOperationException();},()=>value=7);}catch(InvalidOperationException){}Check(s.Restore().Length==0&&value==7,"Partial setter was not restored");});
Test("journal_failure_does_not_skip_other_cleanup",()=>
{var seen=new List<int>();var s=new PreviewBuildScope();s.Own("one",()=>seen.Add(1));s.Own("bad",()=>throw new IOException());s.Own("three",()=>seen.Add(3));var errors=s.Restore();Check(errors.Length==1&&seen.SequenceEqual(new[]{3,1}),"Reverse independent restoration failed");});
Test("journal_restore_is_idempotent",()=>{int count=0;var s=new PreviewBuildScope();s.Own("one",()=>count++);s.Restore();s.Restore();Check(count==1,"Restoration repeated setter");});
Test("journal_rejects_mutation_after_restore",()=>{var s=new PreviewBuildScope();s.Restore();bool rejected=false;try{s.Change("late",()=>{},()=>{});}catch(InvalidOperationException){rejected=true;}Check(rejected,"Restored scope mutated");});
Test("20m_variant_has_explicit_speed_duration_tradeoff",()=>
{
    var fast=new VisualPoseEnvelope();var slow=new VisualPoseEnvelope20Comparison();var target=new Vector3(7.2f,.4f,0);
    fast.Reset(Vector3.Zero,Quaternion.Identity,0);slow.Reset(Vector3.Zero,Quaternion.Identity,0);
    fast.Sample(target,Quaternion.Identity,.01,100,true);slow.Sample(target,Quaternion.Identity,.01,100,true);
    var previousFast=fast.PositionOffset;var previousSlow=slow.PositionOffset;float maxFast=0,maxSlow=0;double settledFast=-1,settledSlow=-1;
    for(int i=1;i<=120;i++)
    {
        double now=.01+i/120d;fast.Sample(target,Quaternion.Identity,now,100);slow.Sample(target,Quaternion.Identity,now,100);
        maxFast=Math.Max(maxFast,Vector3.Distance(previousFast,fast.PositionOffset)*120);maxSlow=Math.Max(maxSlow,Vector3.Distance(previousSlow,slow.PositionOffset)*120);
        previousFast=fast.PositionOffset;previousSlow=slow.PositionOffset;
        if(settledFast<0&&fast.RemainingSeconds==0)settledFast=i/120d;if(settledSlow<0&&slow.RemainingSeconds==0)settledSlow=i/120d;
    }
    Check(maxFast<=40.001&&maxSlow<=20.001,"Comparison speed bounds fail");Check(settledFast<=.375&&settledSlow>.5&&settledSlow<=.75,"Comparison does not expose longer offset duration");
    Check(fast.Position==target&&slow.Position==target,"Variants did not converge to unchanged target");
});
string output=args.Length>0?args[0]:"docs/p10/pose-envelope-native-staging/config-scope-tests.json";
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);File.WriteAllText(output,JsonSerializer.Serialize(new{passed=failures==0,tests=results.Count,failures,results,
    scope="Configuration/restoration journal and isolated20/40m numerical comparison only; no native Unity run.",nativeRendered=false},new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine($"PREVIEW CONTRACT {(failures==0?"PASS":"FAIL")} {results.Count-failures}/{results.Count}");return failures==0?0:1;
