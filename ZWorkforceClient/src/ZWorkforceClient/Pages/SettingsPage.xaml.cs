using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Windows.ApplicationModel;

namespace ZWorkforceClient.Pages;

public sealed partial class SettingsPage : PageBase
{
    private bool _loading;

    public SettingsPage()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private void OnLoaded(object sender, RoutedEventArgs args)
    {
        var session = App.Current.Session;
        ConnectionText.Text = session.Connection is null
            ? "Not connected"
            : $"{session.Connection.BaseUrl} · tenant {session.Connection.TenantId}";
        ClientVersionText.Text = $"zWorkforce Client {PackageVersion()} · API keys remain server-side and are stored locally only in Windows Credential Manager when you opt in.";
        _loading = true;
        ThemeBox.SelectedValue = session.Settings.Theme;
        _loading = false;
    }

    private void OnThemeChanged(object sender, SelectionChangedEventArgs args)
    {
        if (_loading || ThemeBox.SelectedValue is not string theme)
        {
            return;
        }

        App.Current.Session.Settings.SaveTheme(theme);
        App.Current.MainWindow?.ApplyTheme(theme);
    }

    private static string PackageVersion()
    {
        try
        {
            var version = Package.Current.Id.Version;
            return $"{version.Major}.{version.Minor}.{version.Build}.{version.Revision}";
        }
        catch (InvalidOperationException)
        {
            return typeof(SettingsPage).Assembly.GetName().Version?.ToString(3) ?? "development";
        }
    }

    private void OnDisconnectClick(object sender, RoutedEventArgs args)
    {
        App.Current.Session.Disconnect(false);
        ConnectionText.Text = "Not connected";
        ShowMessage("Disconnected. The saved API key was retained.", InfoBarSeverity.Informational);
    }

    private void OnForgetClick(object sender, RoutedEventArgs args)
    {
        var connection = App.Current.Session.Connection;
        if (connection is not null)
        {
            App.Current.Session.Credentials.Delete(connection.BaseUrl, connection.TenantId);
        }

        App.Current.Session.Disconnect(true);
        ConnectionText.Text = "Not connected";
        ShowMessage("The saved API key was removed.", InfoBarSeverity.Success);
    }

    private void ShowMessage(string message, InfoBarSeverity severity)
    {
        SettingsInfo.Severity = severity;
        SettingsInfo.Title = "Settings updated";
        SettingsInfo.Message = message;
        SettingsInfo.IsOpen = true;
    }
}
