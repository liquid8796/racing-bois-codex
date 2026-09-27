using System.Net;
using System.Net.WebSockets;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
var builder=WebApplication.CreateBuilder(args);builder.Logging.ClearProviders();builder.WebHost.ConfigureKestrel(k=>k.Listen(IPAddress.Loopback,0));
var app=builder.Build();app.UseWebSockets();app.Run(async context=>
{
    if(!context.WebSockets.IsWebSocketRequest){context.Response.StatusCode=400;return;}
    using var socket=await context.WebSockets.AcceptWebSocketAsync();var buffer=new byte[32768];
    try{while(socket.State==WebSocketState.Open){var r=await socket.ReceiveAsync(buffer,context.RequestAborted);if(r.MessageType==WebSocketMessageType.Close)break;await socket.SendAsync(buffer.AsMemory(0,r.Count),r.MessageType,r.EndOfMessage,context.RequestAborted);}}
    catch(Exception e)when(e is WebSocketException or OperationCanceledException){}
});
await app.StartAsync();string address=app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.Single();
File.WriteAllText(args[0],"ws"+address.Substring(4));await app.WaitForShutdownAsync();
