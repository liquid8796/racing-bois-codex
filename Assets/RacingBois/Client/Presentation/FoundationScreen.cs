using System;
using UnityEngine;
using UnityEngine.UIElements;
using RacingBois.Client.Application;

namespace RacingBois.Client.Presentation
{
    public sealed class FoundationScreen : MonoBehaviour
    {
        public event Action<string> ConnectRequested;
        public event Action LeaveRequested;
        public bool IsTyping { get { return endpoint != null && endpoint.panel != null &&
            endpoint.Contains(endpoint.panel.focusController.focusedElement as VisualElement); } }
        private VisualElement root, menu, hud;
        private TextField endpoint;
        private Button connect;
        private Label status, message, speed, rider, distance, peers;
        public void Initialize(UIDocument document, string initialEndpoint)
        {
            root = document.rootVisualElement;
            menu = root.Q("menu"); hud = root.Q("hud");
            endpoint = root.Q<TextField>("endpoint"); endpoint.value = initialEndpoint;
            connect = root.Q<Button>("connect");
            status = root.Q<Label>("connection"); message = root.Q<Label>("message");
            speed = root.Q<Label>("speed"); rider = root.Q<Label>("rider");
            distance = root.Q<Label>("distance"); peers = root.Q<Label>("peers");
            root.Q<Label>(className: "title").text = "RACING\nBOIS.";
            connect.clicked += () => ConnectRequested?.Invoke(endpoint.value.Trim());
            root.Q<Button>("leave").clicked += () => LeaveRequested?.Invoke();
            root.Q<Toggle>("reduced-motion").RegisterValueChangedCallback(e => root.EnableInClassList("reduced-motion", e.newValue));
        }
        public void ShowState(SessionStatus state, string playerId, string error)
        {
            bool active = state == SessionStatus.Connected;
            menu.style.display = active ? DisplayStyle.None : DisplayStyle.Flex;
            hud.style.display = active ? DisplayStyle.Flex : DisplayStyle.None;
            connect.SetEnabled(state != SessionStatus.Connecting);
            connect.text = state == SessionStatus.Connecting ? "ĐANG KẾT NỐI..." : "VÀO ĐƯỜNG THỬ  >";
            status.text = active ? "ĐÃ KẾT NỐI" : state == SessionStatus.Connecting ? "ĐANG KẾT NỐI" : "CHƯA KẾT NỐI";
            rider.text = "RIDER / " + playerId.ToUpperInvariant();
            message.text = string.IsNullOrEmpty(error) ? "Tối đa 8 người · PC / Laptop" : error;
            if (active) root.Focus();
        }
        public void SetTelemetry(float metersPerSecond, double meters, int riderCount)
        {
            speed.text = (metersPerSecond * 3.6f).ToString("000");
            distance.text = (meters / 1000).ToString("0.00") + " KM";
            peers.text = riderCount + " / 8 TAY ĐUA";
        }
    }
}
