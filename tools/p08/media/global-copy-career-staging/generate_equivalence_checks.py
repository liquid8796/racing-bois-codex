"""Compile original/replacement expressions against the real shared formatter in VI."""
import json
from pathlib import Path

STAGE=Path(__file__).resolve().parent
canonical=json.loads((STAGE/'canonical-source.json').read_text(encoding='utf-8'))
bindings=json.loads((STAGE/'source-bindings.json').read_text(encoding='utf-8'))
CHECKS=STAGE/'checks'; CHECKS.mkdir(exist_ok=True)
entries=canonical['entries']+bindings['commonBindings']
fixture='''// VI-only managed test fixture. Empty other-locale cells are never shipped or claimed as translations.
using System.Collections.Generic;
namespace RacingBois.Client.Application {
 public static partial class UiText {
  static partial void AddCareer(Dictionary<string,string[]> rows) {
'''
for entry in entries:
    fixture+='   rows.Add('+json.dumps(entry['key'])+', new[] { "", "", "", "", "", '+json.dumps(entry['vi'],ensure_ascii=False)+' });\n'
fixture+='  }\n }\n}\n'
(CHECKS/'CareerVietnameseFixture.cs').write_text(fixture,encoding='utf-8',newline='\n')

head='''using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text.Json;
using RacingBois.Client.Application;

static class Program {
 private static readonly HashSet<string> UsedKeys = new HashSet<string>();
 private static string T(string key) { UsedKeys.Add(key); return UiText.Get("VI",key); }
 private static string F(string key,params UiTextArgument[] args) { UsedKeys.Add(key); return UiText.Format("VI",key,args); }
 private static UiTextArgument A(string name,string value) => new UiTextArgument(name,value);
 private static string ErrorText(string code) => "[error:"+code+"]";
 private static string SuccessText(string notice) => "[notice:"+notice+"]";
 private static void Require(bool condition,string failure) { if(!condition) throw new InvalidOperationException(failure); }
 private static void Main(string[] args) {
  long assertions=0; int scenarios=0;
  foreach(string culture in new[] {"vi-VN","en-US","de-DE","fr-FR"}) {
   CultureInfo.CurrentCulture=CultureInfo.GetCultureInfo(culture);
   for(int flags=0;flags<512;flags++) {
    var s=new Scenario();
    s.inRoom=(flags&1)!=0; s.equipped=(flags&2)!=0; s.shop=(flags&4)!=0;
    s.owned=(flags&8)!=0; s.isOwned=(flags&16)!=0; s.selected=(flags&32)!=0;
    s.available=(flags&64)!=0; s.qualified=(flags&128)!=0;
    s.bike.HasDistinctArt=(flags&256)!=0; s.inspected.HasDistinctArt=s.bike.HasDistinctArt;
    s.route.IsPlayable=(flags&256)!=0;
    s.profile.SelectedBikeId=(flags&2)!=0?s.bike.Id:"other";
    s.profile.RealmKind=flags%3==0?"offline":flags%3==1?"online":"custom{realm}";
    s.profile.DisplayName=flags%7==0?null:flags%7==1?"{credits}<name>":"Tay đua Ω";
    s.profile.Username=flags%7==2?"user{code}":"rider_01";
    s.profile.Credits=flags%5==0?int.MaxValue:flags%5==1?0:1234567;
    s.condition=flags%3==0?100:flags%3==1?0:37;
    s.level=flags%3; s.profile.LevelIndex=(flags/3)%3;
    s.session.Busy=(flags&1)!=0; s.session.ErrorCode=flags%3==0?"":flags%3==1?"network_unavailable":"{unknown}";
    s.session.Notice=flags%2==0?"view":"buy";
    s.session.Endpoint=flags%2==0?"wss://example.invalid/game":"ws://127.0.0.1:7777/";
    s.difference=flags%3==0?-12.345f:flags%3==1?0:12.345f;
    s.bike.DisplayName=flags%7==3?"Bike {cost}":"Spark 450";
    s.inspected.DisplayName=s.bike.DisplayName; s.selectedDefinition.DisplayName=s.bike.DisplayName;
    s.current.DisplayName=flags%7==4?"Apex <R5>":"Spark 450";
    s.code=flags%7==5?null:flags%7==6?"{bike}{cost}":"invalid_operation";
    s.value=flags%2==0?"2026-09-28T01:02:03Z":"not-a-timestamp";
    for(int site=0;site<Sites.Length;site++) {
     string original=Original(site,s),replacement=Replacement(site,s);
     Require(original==replacement,"VI expression mismatch at source span "+Sites[site]+" culture "+culture+" flags "+flags);
     assertions++;
    }
    scenarios++;
   }
  }
  var empty=new Scenario(); empty.profile=null;
  int summary=Array.IndexOf(Sites,8182);
  Require(Original(summary,empty)==Replacement(summary,empty),"Null profile summary changed.");assertions++;
  string opaque="{bike}<b>name</b>";
  Require(UiText.Format("VI","career.garage.previewTooltip",new UiTextArgument("bike",opaque))=="Xem trước "+opaque,"Inserted values were rescanned.");assertions++;
  foreach(string failure in new[]{"missing","extra","duplicate"}) {
   bool rejected=false;
   try {
    if(failure=="missing") UiText.Format("VI","career.garage.previewTooltip");
    else if(failure=="extra") UiText.Format("VI","career.garage.previewTooltip",A("bike","x"),A("extra","y"));
    else UiText.Format("VI","career.garage.previewTooltip",A("bike","x"),A("bike","y"));
   } catch(ArgumentException) { rejected=true; }
   Require(rejected,"Expected named-argument rejection: "+failure);assertions++;
  }
  Require(UsedKeys.Count==156,"Not every Career/common template variant was exercised.");
  var result=new {passed=true,scope="Managed original-vs-template VI expression equivalence using real staged UiText formatter; not native UI, translation or layout acceptance.",
   expressionSites=Sites.Length,compositionSites=30,cultures=4,scenarios,assertions,templateKeysCovered=UsedKeys.Count,
   opaqueArgumentControlPassed=true,namedArgumentNegativeControls=3};
  string json=JsonSerializer.Serialize(result,new JsonSerializerOptions {WriteIndented=true});
  if(args.Length==1) File.WriteAllText(args[0],json+"\\n");
  Console.WriteLine(json);
 }
'''
aliases='''  var profile=s.profile; var session=s.session; var bike=s.bike; var inspected=s.inspected;
  var selectedDefinition=s.selectedDefinition; var current=s.current; var tuning=s.tuning; var route=s.route; var entry=s.entry;
  bool inRoom=s.inRoom,equipped=s.equipped,shop=s.shop,owned=s.owned,isOwned=s.isOwned,selected=s.selected,available=s.available,qualified=s.qualified;
  int condition=s.condition,tradeValue=s.tradeValue,level=s.level; float difference=s.difference; string code=s.code,value=s.value;
'''
program=head+' private static readonly int[] Sites={'+','.join(str(site['expressionStart']) for site in bindings['sites'])+'};\n'
for name,field in [('Original','sourceExpression'),('Replacement','replacementExpression')]:
    program+=' private static string '+name+'(int site,Scenario s) {\n'+aliases+'  switch(site) {\n'
    for index,site in enumerate(bindings['sites']):
        program+='   case '+str(index)+': return '+site[field]+';\n'
    program+='   default: throw new ArgumentOutOfRangeException(nameof(site));\n  }\n }\n'
program+='''}
sealed class Scenario {
 public Profile profile=new Profile(); public Session session=new Session();
 public Bike bike=new Bike(),inspected=new Bike(),selectedDefinition=new Bike(),current=new Bike();
 public Tuning tuning=new Tuning(); public Route route=new Route(); public Entry entry=new Entry();
 public bool inRoom,equipped,shop,owned,isOwned,selected,available,qualified;
 public int condition=37,tradeValue=12345,level=0; public float difference=0; public string code="x",value="";
}
sealed class Profile { public string DisplayName="rider",RealmKind="offline",SelectedBikeId="spark",Username="rider"; public int Credits=1234567,LevelIndex=0; }
sealed class Session { public string Endpoint="",ErrorCode="",Notice=""; public bool Busy; }
sealed class Bike { public string Id="spark",DisplayName="Spark 450"; public bool HasDistinctArt=true; public int CatalogIndex=0,PriceCredits=2147483647,RepairCredits=12345; }
sealed class Tuning { public int MaximumSpeedMillimetersPerSecond=54321,EnginePermille=1234,BrakeDeceleration=6789,CorneringPermille=987; }
sealed class Route { public bool IsPlayable=true; }
sealed class Entry { public int Balance=1234567; }
'''
(CHECKS/'ExpressionEquivalence.cs').write_text(program,encoding='utf-8',newline='\n')
print('Generated141 whole-expression comparisons and a nonshipping VI-only fixture against the real shared formatter.')
