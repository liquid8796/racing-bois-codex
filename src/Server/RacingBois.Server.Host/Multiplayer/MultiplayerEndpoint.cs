using System.Diagnostics;
using System.Net.WebSockets;
using System.Text.Json;
using RacingBois.Protocol;
using RacingBois.Server.Application;

namespace RacingBois.Server.Host.Multiplayer;

internal static class MultiplayerEndpoint
{
    public static void Map(WebApplication app, IConfiguration configuration)
    {
        app.Map("/multiplayer", async (HttpContext context, MultiplayerWorker worker) =>
        {
            if (configuration["RealmKind"] == "online" && !context.Request.IsHttps) { context.Response.StatusCode = 403; return; }
            if (!context.WebSockets.IsWebSocketRequest) { context.Response.StatusCode = 400; return; }
            string origin = context.Request.Headers.Origin.ToString(), expected = $"{context.Request.Scheme}://{context.Request.Host}";
            string[] extra = (configuration["AllowedOrigins"] ?? "").Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            if (origin.Length > 0 && !string.Equals(origin, expected, StringComparison.OrdinalIgnoreCase) && !extra.Contains(origin, StringComparer.OrdinalIgnoreCase))
            { context.Response.StatusCode = 403; return; }
            var peer = worker.Register(); if (peer == null) { context.Response.StatusCode = 503; return; }
            using var socket = await context.WebSockets.AcceptWebSocketAsync();
            using var lifetime = CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted);
            var receiveFinished = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            Task? sender = null;
            try
            {
                var buffer = new byte[MultiplayerProtocol.MaxMessageBytes];
                using var handshake = CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token); handshake.CancelAfter(TimeSpan.FromSeconds(5));
                var initial = await MultiplayerJson.Receive(socket, buffer, handshake.Token); if (initial == null) return;
                if (MultiplayerJson.Parse(initial) is not MpHello hello) throw new JsonException("Hello required.");
                if (!worker.Input(peer, hello)) throw new InvalidDataException("Ingress queue full.");
                sender = Task.Run(async () =>
                {
                    try
                    {
                        while (!lifetime.IsCancellationRequested)
                        {
                            byte[]? bytes = await peer.Mailbox.Read(lifetime.Token); if (bytes == null) break;
                            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token); timeout.CancelAfter(TimeSpan.FromSeconds(5));
                            await socket.SendAsync(bytes, WebSocketMessageType.Text, true, timeout.Token);
                        }
                        if (socket.State == WebSocketState.Open)
                        {
                            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(1));
                            await socket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, peer.Mailbox.CloseReason, timeout.Token);
                            // Keep the receive side alive until the peer acknowledges Close. Cancelling a
                            // pending ReceiveAsync here aborts the socket and can discard accepted/close frames.
                            try { await receiveFinished.Task.WaitAsync(TimeSpan.FromSeconds(2), lifetime.Token); }
                            catch (TimeoutException) { }
                        }
                    }
                    finally { await lifetime.CancelAsync(); }
                }, lifetime.Token);
                var budget = new InputRateBudget(); long began = Stopwatch.GetTimestamp();
                while (!lifetime.IsCancellationRequested && socket.State is WebSocketState.Open or WebSocketState.CloseSent)
                {
                    var bytes = await MultiplayerJson.Receive(socket, buffer, lifetime.Token); if (bytes == null) break;
                    if (socket.State != WebSocketState.Open) continue;
                    if (!budget.TryConsume(Stopwatch.GetElapsedTime(began).TotalSeconds)) throw new InvalidDataException("Ingress rate exceeded.");
                    if (!worker.Input(peer, MultiplayerJson.Parse(bytes))) throw new InvalidDataException("Ingress queue full.");
                }
            }
            catch (Exception error) when (error is WebSocketException or OperationCanceledException or JsonException or InvalidDataException)
            { app.Logger.LogInformation("Multiplayer peer closed: {Reason}", error.GetType().Name); }
            finally
            {
                receiveFinished.TrySetResult();
                await lifetime.CancelAsync();
                if (sender != null) { try { await sender; } catch (Exception error) when (error is WebSocketException or OperationCanceledException) { } }
                await worker.Unregister(peer); peer.Mailbox.Dispose();
                if (socket.State is WebSocketState.Open or WebSocketState.CloseReceived)
                {
                    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(1));
                    try { await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Session ended.", timeout.Token); }
                    catch (Exception error) when (error is WebSocketException or OperationCanceledException) { }
                }
            }
        }).RequireRateLimiting("multiplayer-handshake");
    }
}
