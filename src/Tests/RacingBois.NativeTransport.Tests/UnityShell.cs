using System;

// The actual native transport source is linked unchanged. This shell does not simulate Unity lifecycle, graphics or its Mono runtime.
namespace UnityEngine { public class MonoBehaviour { } }
namespace RacingBois.Client.Application
{
    public interface IRealtimeTransport : IDisposable
    {
        event Action Opened;
        event Action<string> Message;
        event Action<string> Closed;
        void Connect(string endpoint);
        void Send(string text);
        void Poll();
        void Close();
    }
}
