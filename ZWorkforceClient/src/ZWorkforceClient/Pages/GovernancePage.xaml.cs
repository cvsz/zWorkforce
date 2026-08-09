using System.Collections.ObjectModel;
using System.Text.Json.Nodes;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using ZWorkforceClient.Core.Models;
using ZWorkforceClient.ViewModels;

namespace ZWorkforceClient.Pages;

public sealed partial class GovernancePage : PageBase
{
    private readonly ObservableCollection<ResourceRow> _policies = new();
    private readonly ObservableCollection<ResourceRow> _budgets = new();
    private readonly ObservableCollection<ResourceRow> _slo = new();
    private readonly ObservableCollection<ResourceRow> _audit = new();

    public GovernancePage()
    {
        InitializeComponent();
        PoliciesList.ItemsSource = _policies;
        BudgetsList.ItemsSource = _budgets;
        SloList.ItemsSource = _slo;
        AuditList.ItemsSource = _audit;
        Loaded += async (_, _) => await RefreshAsync();
    }

    private async void OnRefreshClick(object sender, RoutedEventArgs args) => await RefreshAsync();

    private async Task RefreshAsync()
    {
        if (!RequireConnection(GovernanceInfo))
        {
            return;
        }

        try
        {
            var policies = Api!.GetItemsAsync("/api/v1/policies");
            var budgets = Api.GetItemsAsync("/api/v1/budgets");
            var slo = Api.GetItemsAsync("/api/v1/slo");
            var audit = Api.GetItemsAsync("/api/v1/audit?limit=100");
            await Task.WhenAll(policies, budgets, slo, audit);
            Fill(_policies, await policies, "name", "id");
            Fill(_budgets, await budgets, "name", "limit_credits");
            Fill(_slo, await slo, "name", "target");
            Fill(_audit, await audit, "action", "actor");
        }
        catch (Exception exception)
        {
            GovernanceInfo.Severity = InfoBarSeverity.Error;
            GovernanceInfo.Title = "Governance unavailable";
            GovernanceInfo.Message = ErrorMessage(exception);
            GovernanceInfo.IsOpen = true;
        }
    }

    private static void Fill(
        ObservableCollection<ResourceRow> target,
        IReadOnlyList<JsonObject> items,
        string titleKey,
        string detailKey)
    {
        target.Clear();
        foreach (var item in items)
        {
            target.Add(new ResourceRow(
                JsonModels.String(item, titleKey, JsonModels.String(item, "id", "Record")),
                JsonModels.String(item, detailKey, ""),
                JsonModels.String(item, "status", JsonModels.String(item, "effect", "available"))));
        }
    }
}
