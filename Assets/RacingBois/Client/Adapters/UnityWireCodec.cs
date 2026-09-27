using RacingBois.Client.Application;
using UnityEngine;
namespace RacingBois.Client.Adapters
{
    public sealed class UnityWireCodec : IWireCodec
    {
        public string Encode(object message) { return JsonUtility.ToJson(message); }
        public T Decode<T>(string text) where T : class { return JsonUtility.FromJson<T>(text); }
    }
}