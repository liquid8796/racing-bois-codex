using System.Text.Json;
using Microsoft.AspNetCore.Http.Features;
using RacingBois.Protocol;
using RacingBois.Server.Application.Career;

namespace RacingBois.Server.Host;

internal static class CareerEndpoint
{
    private const int MaximumBodyBytes = 131072;
    private static readonly SemaphoreSlim RequestSlots = new(8, 8);
    private static readonly JsonSerializerOptions Json = new() { IncludeFields = true };
    private static readonly HashSet<string> Fields = new(StringComparer.Ordinal)
    { "operation", "transactionId", "bikeId", "characterId", "username", "password", "recoveryCode", "saveJson" };

    public static void Map(WebApplication app, IConfiguration configuration)
    {
        app.MapPost("/api/career", async (HttpContext context, CareerService career) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            context.Response.Headers.Pragma = "no-cache";
            string origin = context.Request.Headers.Origin.ToString();
            if (origin.Length > 0 && !string.Equals(origin, $"{context.Request.Scheme}://{context.Request.Host}", StringComparison.OrdinalIgnoreCase))
                return Reply("origin_rejected", 403);
            if (configuration["RealmKind"] == "online" && !context.Request.IsHttps) return Reply("https_required", 403);
            if (!(context.Request.ContentType ?? "").StartsWith("application/json", StringComparison.OrdinalIgnoreCase)) return Reply("bad_request", 415);
            var sizeFeature = context.Features.Get<IHttpMaxRequestBodySizeFeature>();
            if (sizeFeature is { IsReadOnly: false }) sizeFeature.MaxRequestBodySize = MaximumBodyBytes;
            if (context.Request.ContentLength > MaximumBodyBytes) return Reply("bad_request", 413);
            if (!RequestSlots.Wait(0)) return Reply("rate_limited", 429);
            try
            {
                using var payload = new MemoryStream();
                var buffer = new byte[8192]; int count;
                while ((count = await context.Request.Body.ReadAsync(buffer, context.RequestAborted)) > 0)
                {
                    if (payload.Length + count > MaximumBodyBytes) return Reply("bad_request", 413);
                    payload.Write(buffer, 0, count);
                }
                byte[] bytes = payload.ToArray();
                using var parsed = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 4 });
                if (parsed.RootElement.ValueKind != JsonValueKind.Object) return Reply("bad_request", 400);
                var seen = new HashSet<string>(StringComparer.Ordinal);
                foreach (var property in parsed.RootElement.EnumerateObject())
                    if (!Fields.Contains(property.Name) || !seen.Add(property.Name) || property.Value.ValueKind != JsonValueKind.String)
                        return Reply("bad_request", 400);
                var request = JsonSerializer.Deserialize<CareerRequest>(bytes, Json);
                if (request == null || request.operation.Length > 24 || request.transactionId.Length > 64 || request.bikeId.Length > 64 || request.characterId.Length > 64 ||
                    request.username.Length > 64 || request.password.Length > 128 || request.recoveryCode.Length > 128 || request.saveJson.Length > 100000)
                    return Reply("bad_request", 400);
                if ((request.operation is "register" or "login" or "recover" or "rotateRecovery") && !context.Request.IsHttps) return Reply("https_required", 403);
                string header = context.Request.Headers.Authorization.ToString();
                if (header.Length > 128 || header.Length > 0 && !header.StartsWith("Bearer ", StringComparison.Ordinal)) return Reply("auth_required", 401);
                string bearer = header.Length > 0 ? header[7..] : "";
                // The store serializes durable transactions; password hashing and disk I/O never execute on the simulation owner.
                var response = await Task.Run(() => career.Execute(bearer, request), context.RequestAborted);
                return JsonReply(response, response.code == "storage_unavailable" ? 503 : 200);
            }
            catch (JsonException) { return Reply("bad_request", 400); }
            catch (Exception error) when (error is IOException or InvalidDataException)
            {
                app.Logger.LogWarning("Career storage request failed: {Type}", error.GetType().Name);
                return Reply("storage_unavailable", 503);
            }
            finally { RequestSlots.Release(); }
        }).RequireRateLimiting("career");
    }
    // Unity's Web request reader needs an explicit byte length even for small API responses.
    private static IResult JsonReply(CareerResponse value, int status) =>
        Results.Text(JsonSerializer.Serialize(value, Json), "application/json", System.Text.Encoding.UTF8, status);
    private static IResult Reply(string code, int status) => JsonReply(new CareerResponse { code = code }, status);
}
