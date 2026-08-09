using System.Collections.ObjectModel;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using ZWorkforceClient.Core.Models;
using ZWorkforceClient.ViewModels;

namespace ZWorkforceClient.Pages;

public sealed partial class KnowledgePage : PageBase
{
    private readonly ObservableCollection<ResourceRow> _memories = new();
    private readonly ObservableCollection<ResourceRow> _skills = new();

    public KnowledgePage()
    {
        InitializeComponent();
        MemoriesList.ItemsSource = _memories;
        SkillsList.ItemsSource = _skills;
        Loaded += async (_, _) => await RefreshAsync();
    }

    private async void OnSearchClick(object sender, RoutedEventArgs args) => await RefreshAsync();

    private async Task RefreshAsync()
    {
        if (!RequireConnection(KnowledgeInfo))
        {
            return;
        }

        try
        {
            var memoriesTask = Api!.ListMemoriesAsync(QueryBox.Text, 100);
            var skillsTask = Api.GetItemsAsync("/api/v1/skills");
            await Task.WhenAll(memoriesTask, skillsTask);
            Fill(_memories, JsonModels.Items(await memoriesTask), "title", "content");
            Fill(_skills, await skillsTask, "name", "description");
        }
        catch (Exception exception)
        {
            KnowledgeInfo.Severity = InfoBarSeverity.Error;
            KnowledgeInfo.Title = "Knowledge unavailable";
            KnowledgeInfo.Message = ErrorMessage(exception);
            KnowledgeInfo.IsOpen = true;
        }
    }

    private static void Fill(
        ObservableCollection<ResourceRow> target,
        IReadOnlyList<System.Text.Json.Nodes.JsonObject> items,
        string titleKey,
        string detailKey)
    {
        target.Clear();
        foreach (var item in items)
        {
            target.Add(new ResourceRow(
                JsonModels.String(item, titleKey, JsonModels.String(item, "id", "Unnamed")),
                JsonModels.String(item, detailKey, ""),
                JsonModels.String(item, "status", "available")));
        }
    }
}
