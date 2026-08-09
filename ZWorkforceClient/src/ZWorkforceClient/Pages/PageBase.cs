using Microsoft.UI.Xaml.Controls;
using ZWorkforceClient.Core.Api;

namespace ZWorkforceClient.Pages;

public abstract class PageBase : Page
{
    protected ApiClient? Api => App.Current.Session.Api;

    protected bool RequireConnection(InfoBar infoBar)
    {
        if (Api is not null)
        {
            return true;
        }

        infoBar.IsOpen = true;
        infoBar.Severity = InfoBarSeverity.Warning;
        infoBar.Title = "Connect to zWorkforce";
        infoBar.Message = "Open Connection and enter a server URL and API key before loading this page.";
        return false;
    }

    protected static string ErrorMessage(Exception exception)
    {
        if (exception is ApiException apiException && !string.IsNullOrWhiteSpace(apiException.RequestId))
        {
            return $"{apiException.Message} (request {apiException.RequestId})";
        }

        return exception.Message;
    }
}
