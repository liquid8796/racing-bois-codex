using System.Text.Json;
using RacingBois.Client.Application;
const string stage="tools/p08/media/global-copy-fit-amendment/";
using var prior=JsonDocument.Parse(File.ReadAllText("tools/p08/media/global-copy-pristine-amendment/authored-text-union.json"));
using var current=JsonDocument.Parse(File.ReadAllText(stage+"authored-text-union.json"));
using var authored=JsonDocument.Parse(File.ReadAllText(stage+"changes.json"));
var changes=authored.RootElement.EnumerateArray().ToDictionary(x=>(x.GetProperty("locale").GetString(),x.GetProperty("key").GetString()),x=>x.GetProperty("after").GetString());
int cells=0,changed=0;
foreach(var locale in current.RootElement.GetProperty("texts").EnumerateObject())
foreach(var group in locale.Value.EnumerateObject())
foreach(var item in group.Value.EnumerateObject())
{
 string value=item.Value.GetString(),old=prior.RootElement.GetProperty("texts").GetProperty(locale.Name).GetProperty(group.Name).GetProperty(item.Name).GetString();
 if(value!=old){if(group.Name!="global"||!changes.TryGetValue((locale.Name,item.Name),out var expected)||value!=expected)throw new Exception("Unreviewed cell");changed++;}
 if(group.Name=="global"&&UiText.Get(locale.Name,item.Name)!=value)throw new Exception("Effective lookup differs");
 cells++;
}
if(cells!=5550||changed!=3||UiText.Get("ENU","career.garage.pristine")!="BIKE UNDAMAGED")throw new Exception("Effective chain coverage/English amendment lost");
Console.WriteLine("PASS 5550 union cells,2364 generated lookups; exactly3 fit cells; prior ENU amendment retained. Native fit remains unverified.");
