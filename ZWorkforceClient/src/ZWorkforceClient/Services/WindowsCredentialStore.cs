using System.Runtime.InteropServices;
using Windows.Security.Credentials;

namespace ZWorkforceClient.Services;

public sealed class WindowsCredentialStore
{
    private const string Resource = "zWorkforceClient.api-key";

    public string? Read(string baseUrl, string tenantId)
    {
        try
        {
            var credential = new PasswordVault().Retrieve(Resource, UserName(baseUrl, tenantId));
            credential.RetrievePassword();
            return credential.Password;
        }
        catch (COMException)
        {
            return null;
        }
    }

    public void Save(string baseUrl, string tenantId, string apiKey)
    {
        Delete(baseUrl, tenantId);
        new PasswordVault().Add(new PasswordCredential(Resource, UserName(baseUrl, tenantId), apiKey));
    }

    public void Delete(string baseUrl, string tenantId)
    {
        try
        {
            var vault = new PasswordVault();
            var credential = vault.Retrieve(Resource, UserName(baseUrl, tenantId));
            vault.Remove(credential);
        }
        catch (COMException)
        {
            // Missing credentials are already in the desired state.
        }
    }

    private static string UserName(string baseUrl, string tenantId) =>
        $"{baseUrl.Trim()}|{tenantId.Trim()}";
}
