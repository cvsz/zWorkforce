using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using ZWorkforceClient.Core.Models;

namespace ZWorkforceClient.Pages;

public sealed partial class ConnectionPage : PageBase
{
    public ConnectionPage()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private void OnLoaded(object sender, RoutedEventArgs args)
    {
        var settings = App.Current.Session.Settings;
        ServerUrlBox.Text = settings.BaseUrl ?? "http://localhost:9569";
        TenantBox.Text = settings.TenantId ?? "default";
        if (!string.IsNullOrWhiteSpace(ServerUrlBox.Text) && !string.IsNullOrWhiteSpace(TenantBox.Text))
        {
            var remembered = App.Current.Session.LoadRememberedApiKey(ServerUrlBox.Text, TenantBox.Text);
            if (!string.IsNullOrWhiteSpace(remembered))
            {
                ApiKeyBox.Password = remembered;
            }
        }
    }

    private async void OnConnectClick(object sender, RoutedEventArgs args)
    {
        SetBusy(true);
        ConnectionInfo.IsOpen = false;
        HealthText.Text = "Health: checking…";
        ReadyText.Text = "Readiness: checking…";
        try
        {
            var connection = new ConnectionSettings(ServerUrlBox.Text, ApiKeyBox.Password, TenantBox.Text);
            var health = await App.Current.Session.ConnectAsync(
                connection.BaseUrl,
                connection.ApiKey,
                connection.TenantId,
                RememberCheckBox.IsChecked == true);
            HealthText.Text = $"Health: healthy ({health.DatabaseBackendLabel()})";
            ReadyText.Text = $"Readiness: {(health.IsReady ? "ready" : "not ready")}";

            if (!health.IsReady)
            {
                ShowError("The server is reachable but is not ready. Check its database and provider status.");
                return;
            }

            App.Current.MainWindow?.NavigateTo("overview");
        }
        catch (Exception exception)
        {
            HealthText.Text = "Health: failed";
            ReadyText.Text = "Readiness: failed";
            ShowError(ErrorMessage(exception));
        }
        finally
        {
            SetBusy(false);
        }
    }

    private void SetBusy(bool busy)
    {
        ConnectButton.IsEnabled = !busy;
        ConnectButton.Content = busy ? "Connecting…" : "Connect";
    }

    private void ShowError(string message)
    {
        ConnectionInfo.Severity = InfoBarSeverity.Error;
        ConnectionInfo.Title = "Connection failed";
        ConnectionInfo.Message = message;
        ConnectionInfo.IsOpen = true;
    }
}

internal static class ReadinessStatusExtensions
{
    public static string DatabaseBackendLabel(this ReadinessStatus readiness) =>
        string.IsNullOrWhiteSpace(readiness.DatabaseBackend) ? "server" : readiness.DatabaseBackend;
}
