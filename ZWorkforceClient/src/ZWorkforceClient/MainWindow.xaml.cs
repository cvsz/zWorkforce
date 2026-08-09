using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using ZWorkforceClient.Pages;

namespace ZWorkforceClient;

public sealed partial class MainWindow : Window
{
    private bool _isNavigating;

    public MainWindow()
    {
        InitializeComponent();
        NavigateTo("connection");
    }

    public void NavigateTo(string tag)
    {
        if (_isNavigating)
        {
            return;
        }

        _isNavigating = true;
        try
        {
            var item = RootNavigationView.MenuItems
                .OfType<NavigationViewItem>()
                .Concat(RootNavigationView.FooterMenuItems.OfType<NavigationViewItem>())
                .FirstOrDefault(candidate => string.Equals(candidate.Tag?.ToString(), tag, StringComparison.Ordinal));

            if (item is not null && !ReferenceEquals(RootNavigationView.SelectedItem, item))
            {
                RootNavigationView.SelectedItem = item;
            }

            ContentFrame.Navigate(tag switch
            {
                "overview" => typeof(OverviewPage),
                "tasks" => typeof(TasksPage),
                "agents" => typeof(AgentsPage),
                "automation" => typeof(AutomationPage),
                "knowledge" => typeof(KnowledgePage),
                "governance" => typeof(GovernancePage),
                "settings" => typeof(SettingsPage),
                _ => typeof(ConnectionPage)
            });
        }
        finally
        {
            _isNavigating = false;
        }
    }

    private void OnNavigationSelectionChanged(
        NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.SelectedItem is NavigationViewItem item && item.Tag is string tag)
        {
            NavigateTo(tag);
        }
    }
}
