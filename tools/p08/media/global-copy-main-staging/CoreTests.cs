using System.Globalization;
using System.Text.Json;
using System.Xml.Linq;
using RacingBois.Client.Application;

int checks = 0;
void Check(bool value,string why) { if(!value)throw new Exception(why);checks++; }
void Reject(Action action,string why) { bool threw=false;try{action();}catch(ArgumentException){threw=true;}Check(threw,why); }
string stage="tools/p08/media/global-copy-main-staging";
using var source=JsonDocument.Parse(File.ReadAllText(stage+"/canonical-source.json"));
foreach(string locale in new[]{"ENU","DEU","ESP","FRA","ITA","VI"})
{
 using var data=JsonDocument.Parse(File.ReadAllText(stage+"/locales/"+locale+".json"));var strings=data.RootElement.GetProperty("strings");
 foreach(var entry in source.RootElement.GetProperty("entries").EnumerateArray())
 {
  string key=entry.GetProperty("key").GetString(), expected=strings.GetProperty(key).GetString();
  Check(UiText.Contains(key)&&UiText.Get(locale,key)==expected,"Exact authored value "+locale+"/"+key);
  var arguments=entry.GetProperty("arguments").EnumerateArray().Select((x,i)=>new UiTextArgument(x.GetString(),"VALUE"+i+" {unparsed} <name>")).ToArray();
  // Expected substitution touches the trusted template only, not inserted opaque user/catalog values.
  string projected=System.Text.RegularExpressions.Regex.Replace(expected,@"\{([A-Za-z][A-Za-z0-9]*)\}",m=>arguments.Single(a=>a.Name==m.Groups[1].Value).Value);
  Check(UiText.Format(locale,key,arguments)==projected,"Opaque value projection "+key);
 }
 Check(UiText.Format(locale,"menu.level",new UiTextArgument("level",null))==UiText.Get(locale,"menu.level").Replace("{level}",""),"Null concat compatibility");
}
Reject(()=>UiText.Format("VI","menu.level"),"Missing named argument rejected");
Reject(()=>UiText.Format("VI","menu.level",new UiTextArgument("level","1"),new UiTextArgument("level","2")),"Duplicate named argument rejected");
Reject(()=>UiText.Format("VI","menu.level",new UiTextArgument("level","1"),new UiTextArgument("other","2")),"Extra named argument rejected");
Check(DisplayLanguage.FromArguments(Array.Empty<string>())=="VI","VI default");
foreach(var pair in new[]{("fr-CA","FRA"),("de_Latn_DE","DEU"),("it-IT","ITA"),("es-419","ESP"),("vi","VI"),("unknown","ENU")})
 Check(DisplayLanguage.FromArguments(new[]{"--language="+pair.Item1})==pair.Item2,"Global locale normalization");
foreach(string invalid in new[]{"--language=","--language=fr-???","--language=DEU-","--language"})
 Check(DisplayLanguage.FromArguments(new[]{invalid})=="ENU","Explicit invalid fallback");
Check(DisplayLanguage.FromArguments(new[]{"--language=VI","--language=DEU"})=="ENU","Duplicate language fallback");
Check(CinematicText.LocaleFromArguments(new[]{"--language=FRA"})=="FRA","Cinematics use global language");
Check(CinematicText.LocaleFromArguments(new[]{"--language=FRA","--cinematic-language=DEU"})=="DEU","Explicit legacy override retained");
Check(CinematicText.LocaleFromArguments(new[]{"--language=FRA","--cinematic-language="})=="ENU","Malformed explicit override fallback");
Check(UiText.ClientMessage("FRA","opaque {player} room_full") == "opaque {player} room_full","Unknown client data remains opaque");
Check(UiText.ClientMessage("FRA","Máy chủ từ chối: room_full") == "Máy chủ từ chối: room_full","Protocol routing prefix not translated here");
var originalCulture=CultureInfo.CurrentCulture;
try
{
 foreach(string culture in new[]{"en-US","vi-VN","de-DE","fr-FR"})
 {
  CultureInfo.CurrentCulture=CultureInfo.GetCultureInfo(culture);
  foreach(int rank in new[]{1,3,14}) foreach(float seconds in new[]{0,123.45f,9999.9f}) foreach(int reward in new[]{0,750,5000})
  {
   string old="Hạng "+rank+" · "+seconds.ToString("0.0")+" giây\nThưởng luyện tập trong phiên: $"+reward;
   string current=UiText.Format("VI","results.finishDetail",new UiTextArgument("rank",rank.ToString()),new UiTextArgument("seconds",seconds.ToString("0.0")),new UiTextArgument("reward",reward.ToString()));
   Check(old==current,"VI exact result output in "+culture);
  }
 }
}
finally { CultureInfo.CurrentCulture=originalCulture; }
var before=XDocument.Load("Assets/RacingBois/UI/Race.uxml");var after=XDocument.Load(stage+"/Race.uxml");
Check(before.Descendants().Count()==after.Descendants().Count(),"UXML element count retained");
foreach(var pair in before.Descendants().Zip(after.Descendants()))
{
 var attribute=pair.Second.Attribute("name");
 if(pair.First.Attribute("name")==null && attribute!=null && (attribute.Value.StartsWith("copy-",StringComparison.Ordinal)||attribute.Value.StartsWith("mp-copy-",StringComparison.Ordinal)))attribute.Remove();
}
Check(XNode.DeepEquals(before,after),"UXML differs only by new display-copy anchors; no hierarchy/default text/value/layout change");
foreach(string locale in new[]{"ENU","DEU","ESP","FRA","ITA","VI"})
{
 string career="tools/p08/media/global-copy-career-staging/"+(locale=="VI"?"VI.json":"locales/"+locale+".json");
 using var careerDoc=JsonDocument.Parse(File.ReadAllText(career));
 foreach(var row in careerDoc.RootElement.GetProperty("strings").EnumerateObject())Check(UiText.Get(locale,row.Name)==row.Value.GetString(),"Composed Career value "+locale+"/"+row.Name);
 string mp="tools/p08/media/global-copy-multiplayer-staging/"+(locale=="VI"?"canonical-source.json":"locales/"+locale+".json");
 using var mpDoc=JsonDocument.Parse(File.ReadAllText(mp));
 if(locale=="VI")foreach(var row in mpDoc.RootElement.GetProperty("entries").EnumerateArray())Check(UiText.Get(locale,row.GetProperty("key").GetString())==row.GetProperty("vi").GetString(),"Composed MP exactVI");
 else foreach(var row in mpDoc.RootElement.GetProperty("entries").EnumerateObject())Check(UiText.Get(locale,row.Name)==row.Value.GetString(),"Composed MP value "+locale+"/"+row.Name);
 using var clientDoc=JsonDocument.Parse(File.ReadAllText("tools/p08/media/global-copy-client-staging/"+locale+".json"));
 foreach(var row in clientDoc.RootElement.GetProperty("strings").EnumerateObject())Check(UiText.Get(locale,row.Name)==row.Value.GetString(),"Composed client value "+locale+"/"+row.Name);
}
Console.WriteLine($"PASS {checks} main/source/format/language/structure controls; no native or gamewide localization acceptance.");
