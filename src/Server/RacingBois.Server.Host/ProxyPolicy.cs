using System.Net;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.HttpOverrides;

namespace RacingBois.Server.Host;

/// <summary>One explicitly enabled local reverse proxy; direct LAN hosts never trust forwarded headers.</summary>
internal static class ProxyPolicy
{
    public static ForwardedHeadersOptions? Create(bool enabled, bool allowLan)
    {
        if (!enabled) return null;
        if (allowLan) throw new InvalidOperationException("Trusted local proxy requires a loopback-only listener.");
        var options = new ForwardedHeadersOptions
        {
            ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto,
            ForwardLimit = 1,
            RequireHeaderSymmetry = true
        };
        options.KnownIPNetworks.Clear();
        options.KnownProxies.Clear();
        options.KnownProxies.Add(IPAddress.Loopback);
        options.KnownProxies.Add(IPAddress.IPv6Loopback);
        return options;
    }
}
