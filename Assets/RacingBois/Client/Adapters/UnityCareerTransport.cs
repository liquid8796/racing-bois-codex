using System;
using System.Collections;
using System.Text;
using RacingBois.Client.Application;
using RacingBois.Protocol;
using UnityEngine;
using UnityEngine.Networking;

namespace RacingBois.Client.Adapters
{
    /// <summary>Uses the platform TLS trust store; never bypasses certificate verification or logs credentials.</summary>
    public sealed class UnityCareerTransport : MonoBehaviour, ICareerTransport
    {
        public void Send(string endpoint, string bearer, CareerRequest request, Action<CareerResponse, bool> completed)
        { StartCoroutine(SendRequest(endpoint, bearer, request, completed)); }
        private IEnumerator SendRequest(string endpoint, string bearer, CareerRequest command, Action<CareerResponse, bool> completed)
        {
            byte[] payload = Encoding.UTF8.GetBytes(JsonUtility.ToJson(command));
            using (var request = new UnityWebRequest(endpoint, "POST"))
            {
                request.uploadHandler = new UploadHandlerRaw(payload);
                Array.Clear(payload, 0, payload.Length);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");
                if (!string.IsNullOrEmpty(bearer)) request.SetRequestHeader("Authorization", "Bearer " + bearer);
                request.timeout = 20; request.redirectLimit = 0;
                yield return request.SendWebRequest();
                CareerResponse response = null;
                string text = request.downloadHandler.text;
                if (text != null && text.Length <= 262144)
                    try { response = JsonUtility.FromJson<CareerResponse>(text); } catch (ArgumentException) { }
                bool transient = request.result == UnityWebRequest.Result.ConnectionError || request.responseCode >= 500;
                completed(response, transient);
            }
        }
    }
}
