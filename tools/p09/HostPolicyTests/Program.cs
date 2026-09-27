using System.Net;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using RacingBois.Server.Host;
using RacingBois.Server.Host.Multiplayer;

var checks = new List<object>();
void Check(bool passed, string name) { if (!passed) throw new InvalidOperationException(name); checks.Add(new { name, passed }); }
Check(ProxyPolicy.Create(false, true) == null, "direct_lan_does_not_trust_forwarded_headers");
bool rejected = false;
try { ProxyPolicy.Create(true, true); } catch (InvalidOperationException) { rejected = true; }
Check(rejected, "proxy_mode_rejects_public_listener");
async Task<DefaultHttpContext> Apply(string remote, string ip, string proto, string forwardedHost = "attacker.invalid")
{
    var context = new DefaultHttpContext();
    context.Connection.RemoteIpAddress = IPAddress.Parse(remote);
    context.Request.Scheme = "http"; context.Request.Host = new HostString("racing.test");
    context.Request.Headers["X-Forwarded-For"] = ip;
    context.Request.Headers["X-Forwarded-Proto"] = proto;
    context.Request.Headers["X-Forwarded-Host"] = forwardedHost;
    var middleware = new ForwardedHeadersMiddleware(_ => Task.CompletedTask, NullLoggerFactory.Instance, Options.Create(ProxyPolicy.Create(true, false)!));
    await middleware.Invoke(context); return context;
}
var valid = await Apply("127.0.0.1", "192.0.2.2", "https");
Check(valid.Request.IsHttps && valid.Connection.RemoteIpAddress!.Equals(IPAddress.Parse("192.0.2.2")), "trusted_loopback_preserves_https_and_client_ip");
Check(valid.Request.Host.Value == "racing.test", "forwarded_host_cannot_override_actual_host");
var unknown = await Apply("192.0.2.3", "192.0.2.2", "https");
Check(!unknown.Request.IsHttps && unknown.Connection.RemoteIpAddress!.Equals(IPAddress.Parse("192.0.2.3")), "unknown_proxy_cannot_spoof_https_or_ip");
var chain = await Apply("127.0.0.1", "198.51.100.1,192.0.2.2", "http,https");
Check(chain.Request.IsHttps && chain.Connection.RemoteIpAddress!.Equals(IPAddress.Parse("192.0.2.2")), "only_nearest_trusted_proxy_hop_applied");
var asymmetric = await Apply("127.0.0.1", "192.0.2.2,198.51.100.1", "https");
Check(!asymmetric.Request.IsHttps, "asymmetric_headers_rejected");
var histogram = new TickDurationHistogram();
for (int i = 0; i < 99; i++) histogram.Record(0.2);
histogram.Record(1000);
using var sample = JsonDocument.Parse(JsonSerializer.Serialize(histogram.Snapshot()));
Check(sample.RootElement.GetProperty("samples").GetInt64() == 100 && sample.RootElement.GetProperty("p99UpperBoundMilliseconds").GetDouble() == 0.25 && sample.RootElement.GetProperty("overflowSamples").GetInt64() == 1, "bounded_histogram_counts_and_percentile_upper_bound");
string report = JsonSerializer.Serialize(new { generatedUtc = DateTimeOffset.UtcNow, passed = checks.Count, failed = 0, checks }, new JsonSerializerOptions { WriteIndented = true });
if (args.Length == 1) { Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[0]))!); File.WriteAllText(args[0], report); }
Console.WriteLine(report);
