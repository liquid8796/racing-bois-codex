using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using RacingBois.Protocol;

namespace RacingBois.Server.Host;

internal static class WireJson
{
    private static readonly UTF8Encoding StrictUtf8 = new(false, true);
    public static readonly JsonSerializerOptions Options = new()
    {
        IncludeFields = true,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        MaxDepth = 8
    };

    public static byte[] Serialize(object message) => JsonSerializer.SerializeToUtf8Bytes(message, message.GetType(), Options);

    public static T Parse<T>(byte[] bytes, params string[] requiredFields)
    {
        using var doc = ReadDocument(bytes);
        if (doc.RootElement.ValueKind != JsonValueKind.Object) throw new JsonException("Object required.");
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (var field in doc.RootElement.EnumerateObject())
            if (!names.Add(field.Name)) throw new JsonException("Duplicate field.");
        foreach (var required in requiredFields)
            if (!names.Contains(required)) throw new JsonException("Required field missing.");
        return JsonSerializer.Deserialize<T>(bytes, Options) ?? throw new JsonException("Null message.");
    }

    public static JsonDocument ReadDocument(byte[] bytes)
    {
        // JsonDocument can defer decoding a string until GetString/Name. Invalid UTF-8
        // then throws InvalidOperationException, outside the protocol rejection path.
        // Validate encoded text before a document escapes this boundary.
        try
        {
            StrictUtf8.GetCharCount(bytes);
            var document = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 8 });
            try { ValidateText(document.RootElement); return document; }
            catch { document.Dispose(); throw; }
        }
        catch (DecoderFallbackException error) { throw new JsonException("Invalid UTF-8 protocol text.", error); }
        catch (InvalidOperationException error) { throw new JsonException("Invalid encoded JSON string.", error); }
    }

    private static void ValidateText(JsonElement value)
    {
        if (value.ValueKind == JsonValueKind.String) { ValidateUnicode(value.GetString()!); return; }
        if (value.ValueKind == JsonValueKind.Object)
            foreach (var property in value.EnumerateObject()) { ValidateUnicode(property.Name); ValidateText(property.Value); }
        else if (value.ValueKind == JsonValueKind.Array)
            foreach (var item in value.EnumerateArray()) ValidateText(item);
    }

    private static void ValidateUnicode(string text)
    {
        for (int index = 0; index < text.Length; index++)
        {
            if (!char.IsSurrogate(text[index])) continue;
            if (!char.IsHighSurrogate(text[index]) || index + 1 == text.Length || !char.IsLowSurrogate(text[index + 1]))
                throw new JsonException("Unpaired Unicode surrogate.");
            index++;
        }
    }

    public static async Task<byte[]?> Receive(WebSocket socket, CancellationToken cancellation)
    {
        var buffer = new byte[WireProtocol.MaximumMessageBytes];
        int used = 0;
        while (true)
        {
            var result = await socket.ReceiveAsync(buffer.AsMemory(used), cancellation);
            if (result.MessageType == WebSocketMessageType.Close) return null;
            if (result.MessageType != WebSocketMessageType.Text) throw new InvalidDataException("Only text messages are accepted.");
            used += result.Count;
            if (result.EndOfMessage) return buffer.AsSpan(0, used).ToArray();
            if (used == buffer.Length) throw new InvalidDataException("Message exceeds byte limit.");
        }
    }
}
