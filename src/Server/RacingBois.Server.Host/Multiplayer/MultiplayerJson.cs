using System.Net.WebSockets;
using System.Text.Json;
using RacingBois.Protocol;

namespace RacingBois.Server.Host.Multiplayer;

internal static class MultiplayerJson
{
    public static object Parse(byte[] bytes)
    {
        using var document = WireJson.ReadDocument(bytes);
        var root = document.RootElement; RejectDuplicates(root);
        if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("kind", out var kind) || kind.ValueKind != JsonValueKind.String)
            throw new JsonException("Message kind required.");
        return kind.GetString() switch
        {
            "mpHello" => WireJson.Parse<MpHello>(bytes, "kind", "protocolVersion", "simulationRulesVersion", "contentHash", "requestNonce", "displayName", "profileToken", "resumeToken", "freshGuest", "lastReliableSequence"),
            "mpCreate" => WireJson.Parse<MpCreateRoom>(bytes, "kind", "protocolVersion", "sessionEpoch", "requestId", "name", "botCount", "courseIndex", "levelIndex", "publicRoom"),
            "mpJoin" => WireJson.Parse<MpJoinRoom>(bytes, "kind", "protocolVersion", "sessionEpoch", "requestId", "code"),
            "mpReady" => WireJson.Parse<MpSetReady>(bytes, "kind", "protocolVersion", "sessionEpoch", "requestId", "roomId", "ready"),
            "mpStart" => WireJson.Parse<MpStartRace>(bytes, "kind", "protocolVersion", "sessionEpoch", "requestId", "roomId"),
            "mpLeave" => WireJson.Parse<MpLeaveRoom>(bytes, "kind", "protocolVersion", "sessionEpoch", "requestId", "roomId"),
            "mpBack" => WireJson.Parse<MpReturnToLobby>(bytes, "kind", "protocolVersion", "sessionEpoch", "requestId", "roomId"),
            "mpList" => WireJson.Parse<MpListRooms>(bytes, "kind", "protocolVersion", "sessionEpoch", "requestId"),
            "mpGoodbye" => WireJson.Parse<MpGoodbye>(bytes, "kind", "protocolVersion", "sessionEpoch", "requestId"),
            "mpInput" => WireJson.Parse<MpInput>(bytes, "kind", "protocolVersion", "sessionEpoch", "roomId", "raceEpoch", "sequence", "targetTick", "reliableAck", "throttlePermille", "brakePermille", "steerPermille", "attackSide", "kick"),
            "mpPing" => WireJson.Parse<MpPing>(bytes, "kind", "protocolVersion", "sessionEpoch", "nonce", "clientMicroseconds", "reliableAck"),
            "mpAck" => WireJson.Parse<MpAck>(bytes, "kind", "protocolVersion", "sessionEpoch", "reliableSequence"),
            _ => throw new JsonException("Unsupported message kind.")
        };
    }
    private static void RejectDuplicates(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var keys = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in element.EnumerateObject())
            { if (!keys.Add(property.Name)) throw new JsonException("Duplicate field."); RejectDuplicates(property.Value); }
        }
        else if (element.ValueKind == JsonValueKind.Array) foreach (var item in element.EnumerateArray()) RejectDuplicates(item);
    }
    public static async Task<byte[]?> Receive(WebSocket socket, byte[] buffer, CancellationToken cancellation)
    {
        int used = 0;
        while (true)
        {
            var result = await socket.ReceiveAsync(buffer.AsMemory(used), cancellation);
            if (result.MessageType == WebSocketMessageType.Close) return null;
            if (result.MessageType != WebSocketMessageType.Text) throw new InvalidDataException("Text required.");
            used += result.Count;
            if (result.EndOfMessage) return buffer.AsSpan(0, used).ToArray();
            if (used >= buffer.Length) throw new InvalidDataException("Message budget exceeded.");
        }
    }
}
