using System.Net.Security;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;

/// <summary>Trust only this public development certificate for this probe. Never changes OS trust.</summary>
internal sealed class ScopedCertificateTrust : IDisposable
{
    private readonly X509Certificate2 anchor;
    private readonly byte[] expectedSha256;
    private readonly bool emptyTrustAnchor;
    public string PublicSha256 => Convert.ToHexString(expectedSha256);
    public ScopedCertificateTrust(string publicCertificatePath, bool wrongFingerprint = false, bool emptyTrustAnchor = false)
    {
        this.emptyTrustAnchor = emptyTrustAnchor;
        anchor = X509CertificateLoader.LoadCertificateFromFile(publicCertificatePath);
        if (anchor.HasPrivateKey) throw new InvalidOperationException("Only public certificate input is permitted.");
        expectedSha256 = anchor.GetCertHash(HashAlgorithmName.SHA256);
        if (wrongFingerprint) expectedSha256[0] ^= 0xff;
    }
    public bool Validate(object sender, X509Certificate certificate, X509Chain suppliedChain, SslPolicyErrors errors)
    {
        if (certificate == null || (errors & (SslPolicyErrors.RemoteCertificateNotAvailable | SslPolicyErrors.RemoteCertificateNameMismatch)) != 0) return false;
        using var presented = X509CertificateLoader.LoadCertificate(certificate.GetRawCertData());
        if (!CryptographicOperations.FixedTimeEquals(presented.GetCertHash(HashAlgorithmName.SHA256), expectedSha256)) return false;
        using var chain = new X509Chain();
        chain.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
        if (!emptyTrustAnchor) chain.ChainPolicy.CustomTrustStore.Add(anchor);
        chain.ChainPolicy.VerificationFlags = X509VerificationFlags.NoFlag;
        // The explicit self-signed local anchor has no revocation service. No public-CA policy is weakened.
        chain.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
        chain.ChainPolicy.ApplicationPolicy.Add(new Oid("1.3.6.1.5.5.7.3.1")); // TLS server authentication
        return chain.Build(presented);
    }
    public void Dispose() => anchor.Dispose();
}
