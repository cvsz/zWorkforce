using System.Collections.ObjectModel;
using System.Text.Json.Nodes;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using ZWorkforceClient.Core.Models;
using ZWorkforceClient.ViewModels;

namespace ZWorkforceClient.Pages;

public sealed partial class OverviewPage : PageBase
{
    private readonly ObservableCollection<ProviderRow> _providers = new();
    private readonly ObservableCollection<TaskRow> _tasks = new();

    public OverviewPage()
    {
        InitializeComponent();
        ProvidersList.ItemsSource = _providers;
        RecentTasksList.ItemsSource = _tasks;
        Loaded += async (_, _) => await RefreshAsync();
    }

    private async void OnRefreshClick(object sender, RoutedEventArgs args) => await RefreshAsync();

    private async Task RefreshAsync()
    {
        if (!RequireConnection(OverviewInfo))
        {
            return;
        }

        LoadingRing.IsActive = true;
        OverviewInfo.IsOpen = false;
        try
        {
            var api = Api!;
            var overviewTask = api.GetOverviewAsync();
            var providerTask = api.ListProvidersAsync();
            var tasksTask = api.GetTasksAsync(limit: 8);
            await Task.WhenAll(overviewTask, providerTask, tasksTask);

            RenderOverview(await overviewTask);
            RenderProviders(await providerTask);
            RenderTasks(await tasksTask);
        }
        catch (Exception exception)
        {
            OverviewInfo.Severity = InfoBarSeverity.Error;
            OverviewInfo.Title = "Overview unavailable";
            OverviewInfo.Message = ErrorMessage(exception);
            OverviewInfo.IsOpen = true;
        }
        finally
        {
            LoadingRing.IsActive = false;
        }
    }

    private void RenderOverview(JsonObject overview)
    {
        ActiveTasksText.Text = JsonModels.Display(overview["active_tasks"]);
        Tasks24hText.Text = JsonModels.Display(overview["tasks_24h"]);
        SuccessRateText.Text = $"{JsonModels.Display(overview["success_rate"])}%";
        DeadLettersText.Text = JsonModels.Display(overview["dead_letter_tasks"]);
    }

    private void RenderProviders(JsonObject payload)
    {
        _providers.Clear();
        foreach (var provider in JsonModels.Items(payload))
        {
            _providers.Add(new ProviderRow(
                JsonModels.String(provider, "name", "unknown"),
                JsonModels.String(provider, "kind", "provider"),
                JsonModels.Bool(provider, "available"),
                JsonModels.Display(provider["priority"])));
        }
    }

    private void RenderTasks(IReadOnlyList<JsonObject> tasks)
    {
        _tasks.Clear();
        foreach (var task in tasks)
        {
            _tasks.Add(new TaskRow(
                JsonModels.String(task, "id"),
                JsonModels.String(task, "status", "unknown"),
                JsonModels.String(task, "agent_id", "—"),
                JsonModels.String(task, "tier", "—"),
                JsonModels.String(task, "outcome_status", "—"),
                JsonModels.Display(task["cost_credits"]),
                JsonModels.String(task, "created_at", "—")));
        }
    }
}
