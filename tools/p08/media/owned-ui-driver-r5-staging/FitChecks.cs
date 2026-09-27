using System.Text.Json;
using System.Security.Cryptography;
using RacingBois.Tools.NativeUi;
var bytes=File.ReadAllBytes("docs/p08/ui-owned-render/20260928-ui-render-05-driver.json");
if(Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant()!="dc9e8eb9f9fa966831c598b321f0a35a046b810d8a22932d426931044e0b2c09")throw new Exception("Frozen run05 receipt changed");
using var receipt=JsonDocument.Parse(File.ReadAllText("docs/p08/ui-owned-render/20260928-ui-render-05-driver.json"));
if(receipt.RootElement.GetProperty("passed").GetBoolean())throw new Exception("Historical FAIL must remain FAIL");
int cases=0,strictFailures=0;
foreach(var row in receipt.RootElement.GetProperty("singleLineActionMeasurements").EnumerateArray())
{
 float measured=row.GetProperty("measuredWidth").GetSingle(),available=row.GetProperty("contentWidth").GetSingle(),x=row.GetProperty("worldX").GetSingle();
 // Old rows retain origin and widths, not full rectangle endpoints. This uses
 // only the recorded lower estimate of the involved coordinate magnitude.
 float coordinate=Math.Max(Math.Abs(x),Math.Abs(x+Math.Max(measured,available)));
 double pixelsPerLogical=row.GetProperty("width").GetInt32()/1600.0;
 var result=TextFit.Compare(measured,available,coordinate,pixelsPerLogical);
 if(!result.Valid||!result.Fits||result.PixelBound>TextFit.MaximumOutputPixelError)throw new Exception("Recorded rounding-scale sample rejected or cap exceeded");
 if(!row.GetProperty("fitsWidth").GetBoolean())strictFailures++;
 cases++;
}
if(cases!=963||strictFailures!=162)throw new Exception("Frozen historical sample count differs");
int negatives=0;
foreach(var row in receipt.RootElement.GetProperty("checks").EnumerateArray())
 if(row.GetProperty("name").GetString()=="historical-overflow-negative-control")
 {
  var result=TextFit.Compare(row.GetProperty("beforeMeasuredWidth").GetSingle(),row.GetProperty("contentWidth").GetSingle(),1600,1.2);
  if(!result.Valid||result.Fits)throw new Exception("Strong historical negative absorbed");negatives++;
 }
if(negatives!=3)throw new Exception("Historical negatives missing");
foreach(var scale in new[]{0.25,0.85375,1.2,4.0})
{
 // Large coordinates force the pixel cap to bind. A two-thousandths pixel
 // overflow must still fail; this is far below one visible output pixel.
 var capped=TextFit.Compare((float)(100+0.002/scale),100,1000000,scale);
 if(capped.Fits||capped.PixelBound>0.001)throw new Exception("Pixel cap swallowed a real delta");
 if(!TextFit.Compare(100,100,1000000,scale).Fits)throw new Exception("Exact equality rejected");
}
if(TextFit.Compare(float.NaN,10,10,1).Valid||TextFit.Compare(10,0,10,1).Valid||TextFit.Compare(10,10,float.PositiveInfinity,1).Valid||TextFit.Compare(10,10,10,0).Valid)
 throw new Exception("Invalid measurement accepted");
if(TextFit.Float32Ulp(1024)!=1.0/8192||TextFit.Float32Ulp(1)!=1.0/8388608)throw new Exception("Incorrect IEEE754ULP");
Console.WriteLine("PASS 963 historical samples including 162 strict failures; 3 strong negative controls; 4 output-scale cap/equality pairs; 4 invalid-input cases; 2 known float32 ULPs. No native execution or rewrite of historical FAIL.");
