using System.Diagnostics;
using System.Net.WebSockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using RacingBois.Client.Adapters;

var tests = new List<object>(); int failed = 0;
void Check(bool valid, string message) { if (!valid) throw new InvalidOperationException(message); }
async Task Pump(BrowserSocketTransport transport, Func<bool> done, int timeoutMs=3000)
{
    var clock=Stopwatch.StartNew();
    while(!done()&&clock.ElapsedMilliseconds<timeoutMs){transport.Poll();await Task.Delay(5);}
    transport.Poll();Check(done(),"Transport fixture timeout");
}
async Task Test(string name, Func<Task> run)
{
    try {await run();tests.Add(new{name,passed=true});Console.WriteLine("PASS "+name);}
    catch(Exception error){failed++;tests.Add(new{name,passed=false,error=error.Message});Console.WriteLine("FAIL "+name+": "+error.Message);}
}
var builder=WebApplication.CreateBuilder(new WebApplicationOptions{Args=Array.Empty<string>()});
builder.Logging.ClearProviders();builder.WebHost.UseUrls("http://127.0.0.1:0");
await using var fixture=builder.Build();fixture.UseWebSockets();
string fragment="{\"unicode\":\"Đua xe 🏍\",\"data\":\""+new string('x',32000)+"\"}";
var fragmentsSent=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
var burstEnded=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
fixture.Run(async context=>
{
    if(!context.WebSockets.IsWebSocketRequest){context.Response.StatusCode=400;return;}
    if(context.Request.Path=="/frame-context")await Task.Delay(50,context.RequestAborted);
    using var socket=await context.WebSockets.AcceptWebSocketAsync();
    try
    {
        if(context.Request.Path=="/fragments")
        {
            byte[] bytes=Encoding.UTF8.GetBytes(fragment);
            await socket.SendAsync(bytes.AsMemory(0,18),WebSocketMessageType.Text,false,context.RequestAborted);
            await socket.SendAsync(bytes.AsMemory(18),WebSocketMessageType.Text,true,context.RequestAborted);
            fragmentsSent.TrySetResult();
        }
        else if(context.Request.Path=="/burst")
        {
            for(int i=0;i<400;i++)await socket.SendAsync(Encoding.UTF8.GetBytes("snapshot-"+i),WebSocketMessageType.Text,true,context.RequestAborted);
            burstEnded.TrySetResult();
        }
        else if(context.Request.Path=="/binary")
            await socket.SendAsync(Encoding.UTF8.GetBytes("binary is not JSON text framing"),WebSocketMessageType.Binary,true,context.RequestAborted);
        else if(context.Request.Path=="/close")
        {
            await socket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure,"fixture closed",context.RequestAborted);return;
        }
        var buffer=new byte[32768];
        while(socket.State==WebSocketState.Open)
        {
            int count=0;WebSocketReceiveResult result;
            do{result=await socket.ReceiveAsync(new ArraySegment<byte>(buffer,count,buffer.Length-count),context.RequestAborted);count+=result.Count;}while(!result.EndOfMessage&&result.MessageType!=WebSocketMessageType.Close);
            if(result.MessageType==WebSocketMessageType.Close)break;
            await socket.SendAsync(new ArraySegment<byte>(buffer,0,count),WebSocketMessageType.Text,true,context.RequestAborted);
        }
    }
    catch(Exception error) when(error is WebSocketException||error is OperationCanceledException){ }
    finally{if(context.Request.Path=="/burst")burstEnded.TrySetResult();}
});
await fixture.StartAsync();
string address=fixture.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>().Addresses.Single();
string endpoint="ws"+address.Substring(4);
await Test("actual_native_branch_reassembles_fragmented_utf8_and_serializes_outgoing_messages",async()=>
{
    using var transport=new BrowserSocketTransport();int opened=0;var messages=new List<string>();var closed=new List<string>();
    transport.Opened+=()=>opened++;transport.Message+=messages.Add;transport.Closed+=closed.Add;
    transport.Connect(endpoint+"/fragments");await Pump(transport,()=>messages.Count==1);
    Check(opened==1&&messages[0]==fragment,"Fragmented Unicode message changed");
    for(int i=0;i<30;i++)transport.Send("input-"+i);
    await Pump(transport,()=>messages.Count==31);
    Check(messages.Skip(1).SequenceEqual(Enumerable.Range(0,30).Select(i=>"input-"+i)),"Send gate reordered/interleaved text");
    Check(closed.Count==0,"Unexpected close");
});
await Test("reconnect_discards_unpolled_callbacks_from_old_socket_generation",async()=>
{
    using var transport=new BrowserSocketTransport();int opened=0;var messages=new List<string>();var closed=new List<string>();
    transport.Opened+=()=>opened++;transport.Message+=messages.Add;transport.Closed+=closed.Add;
    transport.Connect(endpoint+"/fragments");await Task.Delay(150);
    transport.Connect(endpoint+"/echo");await Pump(transport,()=>opened==1);transport.Send("new generation");
    await Pump(transport,()=>messages.Count>0);
    Check(messages.SequenceEqual(new[]{"new generation"})&&closed.Count==0,"Stale socket callback leaked into new generation");
});
await Test("receive_backlog_fails_closed_at_bounded_budget_without_unbounded_dispatch",async()=>
{
    using var transport=new BrowserSocketTransport();int received=0;string reason="";
    transport.Message+=_=>received++;transport.Closed+=value=>reason=value;
    transport.Connect(endpoint+"/burst");await Task.WhenAny(burstEnded.Task,Task.Delay(3000));await Task.Delay(100);
    transport.Poll();transport.Poll();transport.Poll();
    Check(reason==nameof(InvalidOperationException)&&received<=256,"Receive backlog did not fail closed at budget");
});
await Test("native_transport_rejects_binary_frames_for_the_text_only_protocol",async()=>
{
    using var transport=new BrowserSocketTransport();int received=0;string reason="";
    transport.Message+=_=>received++;transport.Closed+=value=>reason=value;
    transport.Connect(endpoint+"/binary");await Pump(transport,()=>reason.Length>0||received>0);
    Check(received==0&&reason==nameof(InvalidOperationException),"Binary WebSocket frame accepted as protocol text");
});
await Test("remote_close_and_dispose_cancel_without_late_callbacks",async()=>
{
    using var transport=new BrowserSocketTransport();int callbacks=0;string reason="";
    transport.Opened+=()=>callbacks++;transport.Message+=_=>callbacks++;transport.Closed+=value=>{callbacks++;reason=value;};
    transport.Connect(endpoint+"/close");await Pump(transport,()=>reason.Length>0);
    Check(reason=="fixture closed","Remote close reason lost");
    transport.Connect(endpoint+"/echo");await Task.Delay(30);transport.Dispose();int prior=callbacks;
    await Task.Delay(50);transport.Poll();Check(callbacks==prior,"Callback after Dispose");
    bool rejected=false;try{transport.Connect(endpoint+"/echo");}catch(ObjectDisposedException){rejected=true;}Check(rejected,"Disposed transport reconnect accepted");
});
await Test("native_io_never_waits_for_the_frame_synchronization_context",async()=>
{
    using var transport=new BrowserSocketTransport();var context=new HeldFrameContext();int opened=0;string received="";
    transport.Opened+=()=>opened++;transport.Message+=value=>received=value;
    var previous=SynchronizationContext.Current;
    try{SynchronizationContext.SetSynchronizationContext(context);transport.Connect(endpoint+"/frame-context");}
    finally{SynchronizationContext.SetSynchronizationContext(previous);}
    // The actual network handshake is deliberately asynchronous. No simulated
    // frame continuations are pumped: I/O completion must remain independent.
    await Pump(transport,()=>opened==1);
    try{SynchronizationContext.SetSynchronizationContext(context);transport.Send("frame-independent input");}
    finally{SynchronizationContext.SetSynchronizationContext(previous);}
    await Pump(transport,()=>received.Length>0);
    Check(received=="frame-independent input"&&context.Posts==0,"Native I/O captured frame context or required its pump");
});
await fixture.StopAsync();
string[] paths={"Assets/RacingBois/Client/Adapters/BrowserSocketTransport.cs","tools/p10/native-transport-diagnosis/BaselineTransportTestProgram.cs","src/Tests/RacingBois.NativeTransport.Tests/UnityShell.cs","tools/p10/native-transport-diagnosis/BaselineTransportTests.csproj"};
string report=args.Length==2&&args[0]=="--report"?args[1]:"docs/p08/desktop/native-transport-tests.json";
Directory.CreateDirectory(Path.GetDirectoryName(report));
File.WriteAllText(report,JsonSerializer.Serialize(new{generatedUtc=DateTimeOffset.UtcNow,passed=tests.Count-failed,failed,tests,sources=paths.Select(path=>new{path,sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant()}),scope="Staged native BrowserSocketTransport / ClientWebSocket branch in .NET 10, with an empty test-only MonoBehaviour shell and in-process ephemeral loopback Kestrel fixture. Not Unity lifecycle, Unity Mono/IL2CPP, packaged player, trusted TLS, OCI, physical LAN/WAN or rendering acceptance."},new JsonSerializerOptions{WriteIndented=true}));
return failed==0?0:1;

sealed class HeldFrameContext:SynchronizationContext
{
    private readonly System.Collections.Concurrent.ConcurrentQueue<Action> held=new();
    public int Posts;
    public override void Post(SendOrPostCallback callback,object state)
    {Interlocked.Increment(ref Posts);held.Enqueue(()=>callback(state));}
}
