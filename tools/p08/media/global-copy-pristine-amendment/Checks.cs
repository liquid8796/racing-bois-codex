using System.Text.Json;
using RacingBois.Client.Application;
string folder="tools/p08/media/global-copy-pristine-amendment";
using var before=JsonDocument.Parse(File.ReadAllText(folder+"/before/authored-text-union.json"));
using var after=JsonDocument.Parse(File.ReadAllText(folder+"/authored-text-union.json"));
int checks=0,changes=0;
foreach(var locale in after.RootElement.GetProperty("texts").EnumerateObject())
foreach(var boundary in locale.Value.EnumerateObject())
foreach(var entry in boundary.Value.EnumerateObject())
{
 string old=before.RootElement.GetProperty("texts").GetProperty(locale.Name).GetProperty(boundary.Name).GetProperty(entry.Name).GetString();
 string current=entry.Value.GetString();
 if(old!=current)
 {
  if(locale.Name!="ENU"||boundary.Name!="global"||entry.Name!="career.garage.pristine"||old!="BIKE FULLY REPAIRED"||current!="BIKE UNDAMAGED")throw new Exception("Unexpected copy difference");
  changes++;
 }
 if(boundary.Name=="global"&&UiText.Get(locale.Name,entry.Name)!=current)throw new Exception("Generated lookup differs from amended authored union");
 checks++;
}
if(changes!=1)throw new Exception("Expected exactly one amended cell");
Console.WriteLine($"PASS {checks} frozen-union cell comparisons; all2364 global lookups match, one explicit ENU change, no native/visual acceptance.");
