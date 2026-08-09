namespace ZWorkforceClient.Core.Models;

public sealed record ConnectionSettings
{
    public ConnectionSettings(string baseUrl, string apiKey, string? tenantId = null)
    {
        if (string.IsNullOrWhiteSpace(baseUrl))
        {
            throw new ArgumentException("A server URL is required.", nameof(baseUrl));
        }

        var input = baseUrl.Trim();
        if (!input.Contains("://", StringComparison.Ordinal))
        {
            input = $"http://{input}";
        }

        if (!Uri.TryCreate(input, UriKind.Absolute, out var uri) ||
            (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps) ||
            string.IsNullOrWhiteSpace(uri.Host))
        {
            throw new ArgumentException("The server URL must be an HTTP or HTTPS URL.", nameof(baseUrl));
        }

        if (!string.IsNullOrEmpty(uri.Query) || !string.IsNullOrEmpty(uri.Fragment))
        {
            throw new ArgumentException("The server URL must not contain a query or fragment.", nameof(baseUrl));
        }

        var normalized = uri.AbsoluteUri;
        if (!normalized.EndsWith("/", StringComparison.Ordinal))
        {
            normalized += "/";
        }

        BaseUrl = normalized;
        BaseUri = new Uri(normalized, UriKind.Absolute);
        ApiKey = apiKey?.Trim() ?? string.Empty;
        TenantId = string.IsNullOrWhiteSpace(tenantId) ? "default" : tenantId.Trim();
    }

    public string BaseUrl { get; }

    public Uri BaseUri { get; }

    public string ApiKey { get; }

    public string TenantId { get; }

    public bool IsLocalHttp =>
        BaseUri.Scheme == Uri.UriSchemeHttp &&
        (BaseUri.Host.Equals("localhost", StringComparison.OrdinalIgnoreCase) ||
         BaseUri.Host.Equals("127.0.0.1", StringComparison.OrdinalIgnoreCase) ||
         BaseUri.Host.Equals("::1", StringComparison.OrdinalIgnoreCase));

    public void EnsureSecureTransport()
    {
        if (BaseUri.Scheme == Uri.UriSchemeHttp && !IsLocalHttp)
        {
            throw new InvalidOperationException(
                "HTTPS is required for non-local zWorkforce servers. Plain HTTP is allowed only for localhost development.");
        }
    }
}
