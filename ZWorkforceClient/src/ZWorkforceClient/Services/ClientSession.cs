using System.Net.Http;
using ZWorkforceClient.Core.Api;
using ZWorkforceClient.Core.Models;

namespace ZWorkforceClient.Services;

public sealed class ClientSession : IDisposable
{
    private HttpClient? _httpClient;

    public ClientSession()
    {
        Credentials = new WindowsCredentialStore();
        Settings = new WindowsSettingsStore();
    }

    public WindowsCredentialStore Credentials { get; }

    public WindowsSettingsStore Settings { get; }

    public ApiClient? Api { get; private set; }

    public ConnectionSettings? Connection { get; private set; }

    public bool IsConnected => Api is not null && Connection is not null;

    public async Task<ReadinessStatus> ConnectAsync(
        string baseUrl,
        string apiKey,
        string tenantId,
        bool rememberCredential,
        CancellationToken cancellationToken = default)
    {
        var connection = new ConnectionSettings(baseUrl, apiKey, tenantId);
        if (string.IsNullOrWhiteSpace(connection.ApiKey))
        {
            throw new InvalidOperationException("Enter an API key before connecting.");
        }
        connection.EnsureSecureTransport();

        var httpClient = new HttpClient();
        var client = new ApiClient(httpClient, connection);
        await client.GetHealthAsync(cancellationToken).ConfigureAwait(false);
        var readiness = await client.GetReadinessAsync(cancellationToken).ConfigureAwait(false);

        _httpClient?.Dispose();
        _httpClient = httpClient;
        Api = client;
        Connection = connection;
        Settings.SaveConnection(connection.BaseUrl, connection.TenantId);
        if (rememberCredential)
        {
            Credentials.Save(connection.BaseUrl, connection.TenantId, connection.ApiKey);
        }

        return readiness;
    }

    public string? LoadRememberedApiKey(string baseUrl, string tenantId)
    {
        try
        {
            var normalized = new ConnectionSettings(baseUrl, string.Empty, tenantId);
            return Credentials.Read(normalized.BaseUrl, normalized.TenantId);
        }
        catch (ArgumentException)
        {
            return null;
        }
    }

    public void Disconnect(bool forgetCredential)
    {
        if (forgetCredential && Connection is not null)
        {
            Credentials.Delete(Connection.BaseUrl, Connection.TenantId);
            Settings.ClearConnection();
        }

        Api = null;
        Connection = null;
        _httpClient?.Dispose();
        _httpClient = null;
    }

    public void Dispose() => Disconnect(false);
}
