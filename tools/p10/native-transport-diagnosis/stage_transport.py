"""Stage async I/O context fix and source-bound transport tests, outside Assets."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'Transport';OUT.mkdir(exist_ok=True)
source=ROOT/'Assets/RacingBois/Client/Adapters/BrowserSocketTransport.cs';text=source.read_text(encoding='utf8')
for call in ['current.ConnectAsync(new Uri(endpoint), tokenSource.Token)','current.ReceiveAsync(new ArraySegment<byte>(bytes, total, bytes.Length - total), tokenSource.Token)','sendGate.WaitAsync(token.Token)','current.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, token.Token)']:
    anchor='await '+call+';'
    if anchor not in text:raise RuntimeError('Await source changed')
    text=text.replace(anchor,'await '+call+'.ConfigureAwait(false);',1)
text=text.replace('        private async void ConnectNative(string endpoint)','''        // Native I/O must not capture UnitySynchronizationContext: one async
        // continuation per frame can make60Hz input/ack traffic fall behind.
        // Unity-facing callbacks remain queued and execute only through Poll.
        private async void ConnectNative(string endpoint)''')
out=OUT/source.name;out.write_text(text,encoding='utf8')
manifest={'schema':1,'scope':'Native async context only. No protocol, timeout, queue limit, game simulation or main-thread callback semantics change.',
          'changes':[{'path':source.relative_to(ROOT).as_posix(),'before':hashlib.sha256(source.read_bytes()).hexdigest(),'staged':out.relative_to(ROOT).as_posix(),'after':hashlib.sha256(out.read_bytes()).hexdigest()}]}
(HERE/'transport-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
program=(ROOT/'src/Tests/RacingBois.NativeTransport.Tests/Program.cs').read_text(encoding='utf8')
program=program.replace('Assets/RacingBois/Client/Adapters/BrowserSocketTransport.cs','tools/p10/native-transport-diagnosis/Transport/BrowserSocketTransport.cs')
program=program.replace('Actual linked native BrowserSocketTransport','Staged native BrowserSocketTransport')
program=program.replace('src/Tests/RacingBois.NativeTransport.Tests/Program.cs','tools/p10/native-transport-diagnosis/TransportTestProgram.cs')
program=program.replace('src/Tests/RacingBois.NativeTransport.Tests/RacingBois.NativeTransport.Tests.csproj','tools/p10/native-transport-diagnosis/TransportTests.csproj')
program=program.replace('    using var socket=await context.WebSockets.AcceptWebSocketAsync();','    if(context.Request.Path=="/frame-context")await Task.Delay(50,context.RequestAborted);\n    using var socket=await context.WebSockets.AcceptWebSocketAsync();')
anchor='await fixture.StopAsync();'
test='''await Test("native_io_never_waits_for_the_frame_synchronization_context",async()=>
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
'''
assert anchor in program;program=program.replace(anchor,test+anchor)
program+='''
sealed class HeldFrameContext:SynchronizationContext
{
    private readonly System.Collections.Concurrent.ConcurrentQueue<Action> held=new();
    public int Posts;
    public override void Post(SendOrPostCallback callback,object state)
    {Interlocked.Increment(ref Posts);held.Enqueue(()=>callback(state));}
}
'''
(HERE/'TransportTestProgram.cs').write_text(program,encoding='utf8')
baseline=program.replace('tools/p10/native-transport-diagnosis/Transport/BrowserSocketTransport.cs','Assets/RacingBois/Client/Adapters/BrowserSocketTransport.cs')
baseline=baseline.replace('TransportTestProgram.cs','BaselineTransportTestProgram.cs').replace('TransportTests.csproj','BaselineTransportTests.csproj')
(HERE/'BaselineTransportTestProgram.cs').write_text(baseline,encoding='utf8')
print('STAGED_TRANSPORT',manifest['changes'][0]['after'])
