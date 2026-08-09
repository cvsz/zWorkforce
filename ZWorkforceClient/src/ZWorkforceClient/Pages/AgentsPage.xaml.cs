using System.Collections.ObjectModel;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using ZWorkforceClient.Core.Models;
using ZWorkforceClient.ViewModels;

namespace ZWorkforceClient.Pages;

public sealed partial class AgentsPage : PageBase
{
    private readonly ObservableCollection<AgentRow> _agents = new();

    public AgentsPage()
    {
        InitializeComponent();
        AgentsList.ItemsSource = _agents;
        Loaded += async (_, _) => await RefreshAsync();
    }

    private async void OnRefreshClick(object sender, RoutedEventArgs args) => await RefreshAsync();

    private async Task RefreshAsync()
    {
        if (!RequireConnection(AgentsInfo))
        {
            return;
        }

        try
        {
            var agents = await Api!.GetAgentsAsync();
            _agents.Clear();
            foreach (var agent in agents)
            {
                _agents.Add(new AgentRow(
                    JsonModels.String(agent, "id"),
                    JsonModels.String(agent, "name", JsonModels.String(agent, "id", "Agent")),
                    JsonModels.String(agent, "description", "No description"),
                    JsonModels.String(agent, "status", "available")));
            }
        }
        catch (Exception exception)
        {
            AgentsInfo.Severity = InfoBarSeverity.Error;
            AgentsInfo.Title = "Agents unavailable";
            AgentsInfo.Message = ErrorMessage(exception);
            AgentsInfo.IsOpen = true;
        }
    }
}
