using Windows.Storage;

namespace ZWorkforceClient.Services;

public sealed class WindowsSettingsStore
{
    private const string BaseUrlKey = "server.baseUrl";
    private const string TenantKey = "server.tenantId";
    private const string ThemeKey = "ui.theme";

    private ApplicationDataContainer Values => ApplicationData.Current.LocalSettings;

    public string? BaseUrl => Values.Values[BaseUrlKey] as string;

    public string? TenantId => Values.Values[TenantKey] as string;

    public string Theme => Values.Values[ThemeKey] as string ?? "system";

    public void SaveConnection(string baseUrl, string tenantId)
    {
        Values.Values[BaseUrlKey] = baseUrl;
        Values.Values[TenantKey] = tenantId;
    }

    public void SaveTheme(string theme) => Values.Values[ThemeKey] = theme;

    public void ClearConnection()
    {
        Values.Values.Remove(BaseUrlKey);
        Values.Values.Remove(TenantKey);
    }
}
