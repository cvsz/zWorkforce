using System.Collections.ObjectModel;
using System.Text.Json.Nodes;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using ZWorkforceClient.Core.Models;
using ZWorkforceClient.ViewModels;

namespace ZWorkforceClient.Pages;

public sealed partial class AutomationPage : PageBase
{
    private readonly ObservableCollection<ResourceRow> _workflows = new();
    private readonly ObservableCollection<ResourceRow> _runs = new();
    private readonly ObservableCollection<ResourceRow> _schedules = new();
    private readonly ObservableCollection<ResourceRow> _eventRules = new();

    public AutomationPage()
    {
        InitializeComponent();
        WorkflowsList.ItemsSource = _workflows;
        RunsList.ItemsSource = _runs;
        SchedulesList.ItemsSource = _schedules;
        EventRulesList.ItemsSource = _eventRules;
        Loaded += async (_, _) => await RefreshAsync();
    }

    private async void OnRefreshClick(object sender, RoutedEventArgs args) => await RefreshAsync();

    private async void OnTabChanged(object sender, SelectionChangedEventArgs args) => await RefreshAsync();

    private async Task RefreshAsync()
    {
        if (!RequireConnection(AutomationInfo))
        {
            return;
        }

        try
        {
            var workflows = Api!.GetItemsAsync("/api/v1/workflows");
            var runs = Api.GetItemsAsync("/api/v1/workflow-runs");
            var schedules = Api.GetItemsAsync("/api/v1/schedules");
            var rules = Api.GetItemsAsync("/api/v1/event-rules");
            await Task.WhenAll(workflows, runs, schedules, rules);
            Fill(_workflows, await workflows);
            Fill(_runs, await runs);
            Fill(_schedules, await schedules);
            Fill(_eventRules, await rules);
        }
        catch (Exception exception)
        {
            AutomationInfo.Severity = InfoBarSeverity.Error;
            AutomationInfo.Title = "Automation unavailable";
            AutomationInfo.Message = ErrorMessage(exception);
            AutomationInfo.IsOpen = true;
        }
    }

    private static void Fill(ObservableCollection<ResourceRow> target, IReadOnlyList<JsonObject> items)
    {
        target.Clear();
        foreach (var item in items)
        {
            target.Add(new ResourceRow(
                JsonModels.String(item, "name", JsonModels.String(item, "id", "Unnamed")),
                JsonModels.String(item, "description", JsonModels.String(item, "workflow_id", "")),
                JsonModels.String(item, "status", JsonModels.String(item, "state", "available"))));
        }
    }
}
