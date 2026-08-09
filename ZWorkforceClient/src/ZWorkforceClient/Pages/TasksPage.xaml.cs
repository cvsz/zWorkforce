using System.Collections.ObjectModel;
using System.Text.Json.Nodes;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using ZWorkforceClient.Core.Models;
using ZWorkforceClient.ViewModels;

namespace ZWorkforceClient.Pages;

public sealed partial class TasksPage : PageBase
{
    private readonly ObservableCollection<TaskRow> _tasks = new();
    private IReadOnlyList<JsonObject> _source = Array.Empty<JsonObject>();
    private string? _selectedTaskId;

    public TasksPage()
    {
        InitializeComponent();
        TasksList.ItemsSource = _tasks;
        Loaded += async (_, _) => await RefreshAsync();
    }

    private async void OnRefreshClick(object sender, RoutedEventArgs args) => await RefreshAsync();

    private async void OnFilterClick(object sender, RoutedEventArgs args) => await RefreshAsync();

    private async Task RefreshAsync()
    {
        if (!RequireConnection(TaskInfo))
        {
            return;
        }

        TaskInfo.IsOpen = false;
        try
        {
            var status = (StatusBox.SelectedItem as ComboBoxItem)?.Tag?.ToString();
            _source = await Api!.GetTasksAsync(100, 0, status);
            RenderTasks();
        }
        catch (Exception exception)
        {
            ShowError(ErrorMessage(exception));
        }
    }

    private void RenderTasks()
    {
        var query = SearchBox.Text.Trim();
        _tasks.Clear();
        foreach (var task in _source.Where(task =>
                     string.IsNullOrWhiteSpace(query) ||
                     JsonModels.String(task, "id").Contains(query, StringComparison.OrdinalIgnoreCase) ||
                     JsonModels.String(task, "agent_id").Contains(query, StringComparison.OrdinalIgnoreCase)))
        {
            _tasks.Add(ToRow(task));
        }
    }

    private void OnTaskSelected(object sender, SelectionChangedEventArgs args)
    {
        if (TasksList.SelectedItem is not TaskRow row)
        {
            return;
        }

        _selectedTaskId = row.Id;
        var task = _source.FirstOrDefault(candidate => JsonModels.String(candidate, "id") == row.Id);
        TaskDetailText.Text = task?.ToJsonString(new System.Text.Json.JsonSerializerOptions { WriteIndented = true }) ?? row.Id;
        TaskActions.Visibility = Visibility.Visible;
    }

    private async void OnApproveClick(object sender, RoutedEventArgs args) => await RunActionAsync(TaskAction.Approve);

    private async void OnRejectClick(object sender, RoutedEventArgs args) => await RunActionAsync(TaskAction.Reject);

    private async void OnCancelClick(object sender, RoutedEventArgs args) => await RunActionAsync(TaskAction.Cancel);

    private async void OnRetryClick(object sender, RoutedEventArgs args) => await RunActionAsync(TaskAction.Retry);

    private async Task RunActionAsync(TaskAction action)
    {
        if (Api is null || string.IsNullOrWhiteSpace(_selectedTaskId))
        {
            return;
        }

        try
        {
            await Api.TaskActionAsync(_selectedTaskId, action, $"Windows client {action}");
            await RefreshAsync();
        }
        catch (Exception exception)
        {
            ShowError(ErrorMessage(exception));
        }
    }

    private void ShowError(string message)
    {
        TaskInfo.Severity = InfoBarSeverity.Error;
        TaskInfo.Title = "Task operation failed";
        TaskInfo.Message = message;
        TaskInfo.IsOpen = true;
    }

    private static TaskRow ToRow(JsonObject task) => new(
        JsonModels.String(task, "id"),
        JsonModels.String(task, "status", "unknown"),
        JsonModels.String(task, "agent_id", "—"),
        JsonModels.String(task, "tier", "—"),
        JsonModels.String(task, "outcome_status", "—"),
        JsonModels.Display(task["cost_credits"]),
        JsonModels.String(task, "created_at", "—"));
}
