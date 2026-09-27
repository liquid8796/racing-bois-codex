using System.Text.Json;
using RacingBois.Client.Application;
const string stage="tools/p08/media/global-copy-fit2-amendment/";
using var prior=JsonDocument.Parse(File.ReadAllText("tools/p08/media/global-copy-fit-amendment/authored-text-union.json"));
using var current=JsonDocument.Parse(File.ReadAllText(stage+"authored-text-union.json"));
int cells=0,changed=0;
foreach(var locale in current.RootElement.GetProperty("texts").EnumerateObject())
foreach(var group in locale.Value.EnumerateObject())
foreach(var item in group.Value.EnumerateObject())
{
 string value=item.Value.GetString(),old=prior.RootElement.GetProperty("texts").GetProperty(locale.Name).GetProperty(group.Name).GetProperty(item.Name).GetString();
 if(value!=old){if(locale.Name!="DEU"||group.Name!="global"||item.Name!="multiplayer.browser.invite-heading"||value!="CODE VON FREUNDEN?")throw new Exception("Unreviewed cell");changed++;}
 if(group.Name=="global"&&UiText.Get(locale.Name,item.Name)!=value)throw new Exception("Effective lookup differs");
 cells++;
}
if(cells!=5550||changed!=1)throw new Exception("Effective chain cell coverage changed");
foreach(var pair in new[]{("ENU","BIKE UNDAMAGED"),("DEU","UNBESCHÄDIGT"),("ESP","SIN DAÑOS"),("FRA","MOTO INTACTE"),("ITA","MOTO INTEGRA"),("VI","XE NGUYÊN VẸN")})
 if(UiText.Get(pair.Item1,"career.garage.pristine")!=pair.Item2)throw new Exception("Prior Career amendment lost");
Console.WriteLine("PASS 5550 union cells,2364 generated lookups; exactly1 Multiplayer cell; all six Career pristine cells retained. Native fit remains unverified.");
