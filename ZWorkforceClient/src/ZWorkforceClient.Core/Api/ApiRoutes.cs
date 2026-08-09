namespace ZWorkforceClient.Core.Api;

public static class ApiRoutes
{
    public const string Health = "/health";
    public const string Ready = "/ready";
    public const string Metrics = "/metrics";
    public const string Overview = "/api/v1/overview";
    public const string Providers = "/api/v1/providers";
    public const string Models = "/api/v1/models";
    public const string Recommendations = "/api/v1/recommendations";
    public const string Tools = "/api/v1/tools";
    public const string Agents = "/api/v1/agents";
    public const string AgentTemplates = "/api/v1/agent-templates";
    public const string Policies = "/api/v1/policies";
    public const string Tasks = "/api/v1/tasks";
    public const string Budgets = "/api/v1/budgets";
    public const string Memories = "/api/v1/memories";
    public const string Skills = "/api/v1/skills";
    public const string Workflows = "/api/v1/workflows";
    public const string WorkflowRuns = "/api/v1/workflow-runs";
    public const string WorkflowTick = "/api/v1/workflow-tick";
    public const string Schedules = "/api/v1/schedules";
    public const string EventRules = "/api/v1/event-rules";
    public const string Events = "/api/v1/events";
    public const string SchedulerTick = "/api/v1/scheduler-tick";
    public const string EvaluationSuites = "/api/v1/evaluation-suites";
    public const string EvaluationRuns = "/api/v1/evaluation-runs";
    public const string EvaluationTick = "/api/v1/evaluation-tick";
    public const string Rag = "/api/v1/rag";
    public const string RagReindex = "/api/v1/rag/reindex";
    public const string Artifacts = "/api/v1/artifacts";
    public const string Slo = "/api/v1/slo";
    public const string SloStatus = "/api/v1/slo/status";
    public const string Chargeback = "/api/v1/chargeback";
    public const string Capacity = "/api/v1/capacity";
    public const string Economics = "/api/v1/economics";
    public const string Tenants = "/api/v1/tenants";
    public const string ApiKeys = "/api/v1/api-keys";
    public const string Audit = "/api/v1/audit";
    public const string AuditVerify = "/api/v1/audit/verify";
    public const string ToolEvents = "/api/v1/tool-events";

    public static string AgentVersions(string agentId) => $"{Agents}/{Escape(agentId)}/versions";

    public static string AgentTemplateInstantiate(string templateId) =>
        $"{AgentTemplates}/{Escape(templateId)}/instantiate";

    public static string Task(string taskId) => $"{Tasks}/{Escape(taskId)}";

    public static string TaskEvents(string taskId) => $"{Task(taskId)}/events";

    public static string TaskApprovals(string taskId) => $"{Task(taskId)}/approvals";

    public static string TaskAction(string taskId, string action) => $"{Task(taskId)}/{Escape(action)}";

    public static string WorkflowRun(string runId) => $"{WorkflowRuns}/{Escape(runId)}";

    public static string EvaluationRun(string runId) => $"{EvaluationRuns}/{Escape(runId)}";

    public static string ApiKeyRevoke(string keyId) => $"{ApiKeys}/{Escape(keyId)}/revoke";

    private static string Escape(string value) => Uri.EscapeDataString(value.Trim());
}
