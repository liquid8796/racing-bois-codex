using System;
using System.Runtime.InteropServices;
using RacingBois.Client.Application;
using UnityEngine;
#if !UNITY_WEBGL || UNITY_EDITOR
using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
#endif

namespace RacingBois.Client.Adapters
{
    public sealed class BrowserSocketTransport : MonoBehaviour, IRealtimeTransport
    {
        public event Action Opened;
        public event Action<string> Message;
        public event Action<string> Closed;
        private bool disposed;
#if UNITY_WEBGL && !UNITY_EDITOR
        [DllImport("__Internal")] private static extern void RB_Connect(string receiver, string endpoint);
        [DllImport("__Internal")] private static extern void RB_Send(string text);
        [DllImport("__Internal")] private static extern void RB_Close();
        [DllImport("__Internal")] private static extern void RB_Report(string text);
#else
        private ClientWebSocket socket;
        private CancellationTokenSource cancellation;
        private readonly ConcurrentQueue<Action> callbacks = new ConcurrentQueue<Action>();
        private readonly SemaphoreSlim sendGate = new SemaphoreSlim(1, 1);
#endif
        public void Connect(string endpoint)
        {
            if (disposed) throw new ObjectDisposedException(nameof(BrowserSocketTransport));
            if (!Uri.TryCreate(endpoint, UriKind.Absolute, out var uri) || (uri.Scheme != "ws" && uri.Scheme != "wss"))
            { Closed?.Invoke("Địa chỉ máy chủ không hợp lệ."); return; }
#if UNITY_WEBGL && !UNITY_EDITOR
            RB_Connect(gameObject.name, endpoint);
#else
            ConnectNative(endpoint);
#endif
        }

#if !UNITY_WEBGL || UNITY_EDITOR
        // Native I/O must not capture UnitySynchronizationContext: one async
        // continuation per frame can make60Hz input/ack traffic fall behind.
        // Unity-facing callbacks remain queued and execute only through Poll.
        private async void ConnectNative(string endpoint)
        {
            Close();
            var current = new ClientWebSocket(); socket = current;
            var tokenSource = new CancellationTokenSource(); cancellation = tokenSource;
            try
            {
                await current.ConnectAsync(new Uri(endpoint), tokenSource.Token).ConfigureAwait(false);
                callbacks.Enqueue(() => { if (socket == current && !disposed) Opened?.Invoke(); });
                var bytes = new byte[32768];
                while (current.State == WebSocketState.Open)
                {
                    int total = 0;
                    WebSocketReceiveResult result;
                    do
                    {
                        result = await current.ReceiveAsync(new ArraySegment<byte>(bytes, total, bytes.Length - total), tokenSource.Token).ConfigureAwait(false);
                        if (result.MessageType == WebSocketMessageType.Close) break;
                        if (result.MessageType != WebSocketMessageType.Text) throw new InvalidOperationException("Text protocol frame required");
                        total += result.Count;
                        if (total >= bytes.Length && !result.EndOfMessage) throw new InvalidOperationException("Snapshot too large");
                    } while (!result.EndOfMessage);
                    if (result.MessageType == WebSocketMessageType.Close) break;
                    var text = Encoding.UTF8.GetString(bytes, 0, total);
                    if (callbacks.Count >= 256) throw new InvalidOperationException("Client receive queue exceeded budget");
                    callbacks.Enqueue(() => { if (socket == current && !disposed) Message?.Invoke(text); });
                }
                string closeReason=current.CloseStatusDescription;
                if(string.IsNullOrEmpty(closeReason))closeReason="closed";
                if(closeReason.Length>160)closeReason=closeReason.Substring(0,160);
                callbacks.Enqueue(() => { if (socket == current && !disposed) Closed?.Invoke(closeReason); });
            }
            catch (Exception error)
            {
                callbacks.Enqueue(() => { if (socket == current && !disposed) Closed?.Invoke(error.GetType().Name); });
            }
            finally { current.Dispose(); }
        }
#endif

        public void Send(string text)
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            RB_Send(text);
#else
            SendNative(text);
#endif
        }

#if !UNITY_WEBGL || UNITY_EDITOR
        private async void SendNative(string text)
        {
            var current = socket; var token = cancellation;
            if (current == null || current.State != WebSocketState.Open || token == null) return;
            try
            {
                await sendGate.WaitAsync(token.Token).ConfigureAwait(false);
                try
                {
                    var bytes = Encoding.UTF8.GetBytes(text);
                    await current.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, token.Token).ConfigureAwait(false);
                }
                finally { sendGate.Release(); }
            }
            catch (Exception) { callbacks.Enqueue(() => { if (socket == current && !disposed) Closed?.Invoke("send failed"); }); }
        }
#endif
        public void Poll()
        {
#if !UNITY_WEBGL || UNITY_EDITOR
            int remaining = 128;
            while (remaining-- > 0 && callbacks.TryDequeue(out var callback)) callback();
#endif
        }
        public void Close()
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            RB_Close();
#else
            var previous = socket; socket = null;
            cancellation?.Cancel(); cancellation?.Dispose(); cancellation = null;
            previous?.Dispose();
#endif
        }
        public void Dispose() { if (disposed) return; disposed = true; Close(); }
        private void OnDestroy() { Dispose(); }
        public void OnSocketOpened(string unused) { if (!disposed) Opened?.Invoke(); }
        public void OnSocketMessage(string text) { if (!disposed) Message?.Invoke(text); }
        public void OnSocketClosed(string reason) { if (!disposed) Closed?.Invoke(reason); }
        public static void Report(string text)
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            RB_Report(text);
#endif
        }
    }
}
