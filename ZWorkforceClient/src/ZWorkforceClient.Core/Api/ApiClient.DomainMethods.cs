using System.Text.Json.Nodes;

namespace ZWorkforceClient.Core.Api;

public sealed partial class ApiClient
{
    public Task<IReadOnlyList<JsonObject>> GetAgentTemplatesAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.AgentTemplates, cancellationToken);

    public Task<JsonObject> CreateOrUpdateAgentTemplateAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.AgentTemplates, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> InstantiateAgentTemplateAsync(
        string templateId,
        JsonObject? body = null,
        string? idempotencyKey = null,
        CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.AgentTemplateInstantiate(templateId), body, idempotencyKey, cancellationToken);

    public Task<JsonObject> GetAgentVersionsAsync(string agentId, CancellationToken cancellationToken = default) =>
        GetCollectionAsync(ApiRoutes.AgentVersions(agentId), cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetPoliciesAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.Policies, cancellationToken);

    public Task<JsonObject> CreateOrUpdatePolicyAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Policies, body, idempotencyKey, cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetBudgetsAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.Budgets, cancellationToken);

    public Task<JsonObject> SetBudgetAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Budgets, body, idempotencyKey, cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetWorkflowsAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.Workflows, cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetWorkflowRunsAsync(
        int limit = 100, CancellationToken cancellationToken = default) =>
        GetItemsAsync($"{ApiRoutes.WorkflowRuns}?limit={Math.Clamp(limit, 1, 500)}", cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetSchedulesAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.Schedules, cancellationToken);

    public Task<JsonObject> CreateScheduleAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Schedules, body, idempotencyKey, cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetEventRulesAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.EventRules, cancellationToken);

    public Task<JsonObject> CreateEventRuleAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.EventRules, body, idempotencyKey, cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetEvaluationSuitesAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.EvaluationSuites, cancellationToken);

    public Task<JsonObject> CreateEvaluationSuiteAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.EvaluationSuites, body, idempotencyKey, cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetEvaluationRunsAsync(
        CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.EvaluationRuns, cancellationToken);

    public Task<JsonObject> StartEvaluationRunAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.EvaluationRuns, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> RunEvaluationTickAsync(
        string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.EvaluationTick, idempotencyKey: idempotencyKey, cancellationToken: cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetArtifactsAsync(
        int limit = 100, CancellationToken cancellationToken = default) =>
        GetItemsAsync($"{ApiRoutes.Artifacts}?limit={Math.Clamp(limit, 1, 500)}", cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetSkillsAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.Skills, cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetSloPoliciesAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.Slo, cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetTenantsAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.Tenants, cancellationToken);

    public Task<JsonObject> CreateTenantAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Tenants, body, idempotencyKey, cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetApiKeysAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.ApiKeys, cancellationToken);

    public Task<JsonObject> CreateApiKeyAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.ApiKeys, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> RevokeApiKeyAsync(
        string keyId, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.ApiKeyRevoke(keyId), idempotencyKey: idempotencyKey, cancellationToken: cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetAuditAsync(
        int limit = 100, int offset = 0, CancellationToken cancellationToken = default) =>
        GetItemsAsync($"{ApiRoutes.Audit}?limit={Math.Clamp(limit, 1, 500)}&offset={Math.Max(0, offset)}", cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetToolEventsAsync(
        string? taskId = null, int limit = 100, CancellationToken cancellationToken = default)
    {
        var route = $"{ApiRoutes.ToolEvents}?limit={Math.Clamp(limit, 1, 500)}";
        if (!string.IsNullOrWhiteSpace(taskId))
        {
            route += $"&task_id={Uri.EscapeDataString(taskId.Trim())}";
        }

        return GetItemsAsync(route, cancellationToken);
    }

    public Task<JsonObject> CreateTaskAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Tasks, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> CreateOrUpdateAgentAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Agents, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> CreateOrUpdateWorkflowAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Workflows, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> StartWorkflowRunAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.WorkflowRuns, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> RunWorkflowTickAsync(CancellationToken cancellationToken = default) =>
        RunWorkflowTickAsync(idempotencyKey: null, cancellationToken: cancellationToken);

    public Task<JsonObject> RunWorkflowTickAsync(
        string? idempotencyKey, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.WorkflowTick, idempotencyKey: idempotencyKey, cancellationToken: cancellationToken);

    public Task<JsonObject> RunSchedulerTickAsync(CancellationToken cancellationToken = default) =>
        RunSchedulerTickAsync(idempotencyKey: null, cancellationToken: cancellationToken);

    public Task<JsonObject> RunSchedulerTickAsync(
        string? idempotencyKey, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.SchedulerTick, idempotencyKey: idempotencyKey, cancellationToken: cancellationToken);

    public Task<JsonObject> ReindexRagAsync(CancellationToken cancellationToken = default) =>
        ReindexRagAsync(idempotencyKey: null, cancellationToken: cancellationToken);

    public Task<JsonObject> ReindexRagAsync(
        string? idempotencyKey, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.RagReindex, idempotencyKey: idempotencyKey, cancellationToken: cancellationToken);

    public Task<JsonObject> EmitEventAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Events, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> SetSloPolicyAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Slo, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> SetEconomicsAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Economics, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> VerifyAuditAsync(CancellationToken cancellationToken = default) =>
        GetJsonAsync(ApiRoutes.AuditVerify, cancellationToken: cancellationToken);

    public Task<JsonObject> CreateMemoryAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Memories, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> CreateSkillAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Skills, body, idempotencyKey, cancellationToken);

    public Task<JsonObject> CreateArtifactAsync(
        JsonObject body, string? idempotencyKey = null, CancellationToken cancellationToken = default) =>
        PostJsonAsync(ApiRoutes.Artifacts, body, idempotencyKey, cancellationToken);
}
