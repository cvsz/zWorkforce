using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using ZWorkforceClient.Core.Models;

namespace ZWorkforceClient.Core.Api;

public sealed partial class ApiClient
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = true
    };

    private readonly HttpClient _httpClient;
    private readonly ConnectionSettings _settings;

    public ApiClient(HttpClient httpClient, ConnectionSettings settings)
    {
        _httpClient = httpClient ?? throw new ArgumentNullException(nameof(httpClient));
        _settings = settings ?? throw new ArgumentNullException(nameof(settings));
        _httpClient.BaseAddress = settings.BaseUri;
        _httpClient.Timeout = TimeSpan.FromSeconds(30);
    }

    public ConnectionSettings Settings => _settings;

    public async Task<HealthStatus> GetHealthAsync(CancellationToken cancellationToken = default)
    {
        return await GetTypedAsync<HealthStatus>(ApiRoutes.Health, authenticated: false, cancellationToken)
            .ConfigureAwait(false);
    }

    public async Task<ReadinessStatus> GetReadinessAsync(CancellationToken cancellationToken = default)
    {
        return await GetTypedAsync<ReadinessStatus>(ApiRoutes.Ready, authenticated: false, cancellationToken)
            .ConfigureAwait(false);
    }

    public Task<JsonObject> GetOverviewAsync(CancellationToken cancellationToken = default) =>
        GetJsonAsync(ApiRoutes.Overview, cancellationToken: cancellationToken);

    public Task<JsonObject> GetModelsAsync(CancellationToken cancellationToken = default) =>
        GetJsonAsync(ApiRoutes.Models, cancellationToken: cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetAgentsAsync(CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.Agents, cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetTasksAsync(
        int limit = 100,
        int offset = 0,
        string? status = null,
        string? agentId = null,
        CancellationToken cancellationToken = default)
    {
        var query = new List<string>
        {
            $"limit={Math.Clamp(limit, 1, 500)}",
            $"offset={Math.Max(0, offset)}"
        };
        AddQuery(query, "status", status);
        AddQuery(query, "agent_id", agentId);
        return GetItemsAsync($"{ApiRoutes.Tasks}?{string.Join('&', query)}", cancellationToken);
    }

    public Task<JsonObject> GetTaskAsync(string taskId, CancellationToken cancellationToken = default) =>
        GetJsonAsync(ApiRoutes.Task(taskId), cancellationToken: cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetTaskEventsAsync(
        string taskId, CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.TaskEvents(taskId), cancellationToken);

    public Task<IReadOnlyList<JsonObject>> GetTaskApprovalsAsync(
        string taskId, CancellationToken cancellationToken = default) =>
        GetItemsAsync(ApiRoutes.TaskApprovals(taskId), cancellationToken);

    public Task<JsonObject> TaskActionAsync(
        string taskId,
        TaskAction action,
        string? comment = null,
        string? idempotencyKey = null,
        CancellationToken cancellationToken = default)
    {
        var body = new JsonObject();
        if (!string.IsNullOrWhiteSpace(comment))
        {
            body["comment"] = comment.Trim();
        }

        return PostJsonAsync(
            ApiRoutes.TaskAction(taskId, action.ToString().ToLowerInvariant()),
            body,
            idempotencyKey,
            cancellationToken);
    }

    public Task<JsonObject> GetCollectionAsync(string route, CancellationToken cancellationToken = default) =>
        GetJsonAsync(route, cancellationToken: cancellationToken);

    public async Task<IReadOnlyList<JsonObject>> GetItemsAsync(
        string route, CancellationToken cancellationToken = default)
    {
        var payload = await GetJsonAsync(route, cancellationToken: cancellationToken).ConfigureAwait(false);
        return JsonModels.Items(payload);
    }

    public Task<JsonObject> GetJsonAsync(
        string route,
        bool authenticated = true,
        CancellationToken cancellationToken = default) =>
        SendJsonAsync(HttpMethod.Get, route, body: null, authenticated, idempotencyKey: null, cancellationToken);

    public Task<JsonObject> PostJsonAsync(
        string route,
        JsonObject? body = null,
        string? idempotencyKey = null,
        CancellationToken cancellationToken = default) =>
        SendJsonAsync(HttpMethod.Post, route, body, authenticated: true, idempotencyKey, cancellationToken);

    public Task<JsonObject> ListProvidersAsync(CancellationToken cancellationToken = default) =>
        GetJsonAsync(ApiRoutes.Providers, cancellationToken: cancellationToken);

    public Task<JsonObject> ListRecommendationsAsync(
        int days = 7, CancellationToken cancellationToken = default) =>
        GetJsonAsync($"{ApiRoutes.Recommendations}?days={Math.Clamp(days, 1, 365)}", cancellationToken: cancellationToken);

    public Task<JsonObject> ListToolsAsync(CancellationToken cancellationToken = default) =>
        GetJsonAsync(ApiRoutes.Tools, cancellationToken: cancellationToken);

    public Task<JsonObject> ListMemoriesAsync(
        string? query = null, int limit = 100, CancellationToken cancellationToken = default)
    {
        var route = $"{ApiRoutes.Memories}?limit={Math.Clamp(limit, 1, 500)}";
        if (!string.IsNullOrWhiteSpace(query))
        {
            route += $"&q={Uri.EscapeDataString(query.Trim())}";
        }

        return GetJsonAsync(route, cancellationToken: cancellationToken);
    }

    public Task<JsonObject> SearchRagAsync(
        string query, int limit = 10, string? agentId = null, CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(query))
        {
            throw new ArgumentException("A search query is required.", nameof(query));
        }

        var route = $"{ApiRoutes.Rag}?q={Uri.EscapeDataString(query.Trim())}&limit={Math.Clamp(limit, 1, 100)}";
        if (!string.IsNullOrWhiteSpace(agentId))
        {
            route += $"&agent_id={Uri.EscapeDataString(agentId.Trim())}";
        }

        return GetJsonAsync(route, cancellationToken: cancellationToken);
    }

    public Task<JsonObject> GetWorkflowRunAsync(string runId, CancellationToken cancellationToken = default) =>
        GetJsonAsync(ApiRoutes.WorkflowRun(runId), cancellationToken: cancellationToken);

    public Task<JsonObject> GetEvaluationRunAsync(string runId, CancellationToken cancellationToken = default) =>
        GetJsonAsync(ApiRoutes.EvaluationRun(runId), cancellationToken: cancellationToken);

    public Task<JsonObject> GetSloStatusAsync(CancellationToken cancellationToken = default) =>
        GetJsonAsync(ApiRoutes.SloStatus, cancellationToken: cancellationToken);

    public Task<JsonObject> GetChargebackAsync(
        int hours = 720, CancellationToken cancellationToken = default) =>
        GetJsonAsync($"{ApiRoutes.Chargeback}?hours={Math.Clamp(hours, 1, 8760)}", cancellationToken: cancellationToken);

    public Task<JsonObject> GetCapacityAsync(
        int hours = 24, CancellationToken cancellationToken = default) =>
        GetJsonAsync($"{ApiRoutes.Capacity}?hours={Math.Clamp(hours, 1, 8760)}", cancellationToken: cancellationToken);

    private async Task<T> GetTypedAsync<T>(
        string route, bool authenticated, CancellationToken cancellationToken)
    {
        var payload = await SendStringAsync(
            HttpMethod.Get, route, body: null, authenticated, idempotencyKey: null, cancellationToken)
            .ConfigureAwait(false);
        return JsonSerializer.Deserialize<T>(payload, SerializerOptions)
               ?? throw new InvalidOperationException($"The server returned an empty {typeof(T).Name} response.");
    }

    private async Task<JsonObject> SendJsonAsync(
        HttpMethod method,
        string route,
        JsonObject? body,
        bool authenticated,
        string? idempotencyKey,
        CancellationToken cancellationToken)
    {
        var text = await SendStringAsync(method, route, body, authenticated, idempotencyKey, cancellationToken)
            .ConfigureAwait(false);
        var node = JsonNode.Parse(text) as JsonObject;
        return node ?? throw new InvalidOperationException("The server returned a JSON value that is not an object.");
    }

    private async Task<string> SendStringAsync(
        HttpMethod method,
        string route,
        JsonObject? body,
        bool authenticated,
        string? idempotencyKey,
        CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(method, NormalizeRoute(route));
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

        if (authenticated)
        {
            if (string.IsNullOrWhiteSpace(_settings.ApiKey))
            {
                throw new InvalidOperationException("An API key is required for authenticated requests.");
            }

            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _settings.ApiKey);
            request.Headers.TryAddWithoutValidation("X-Tenant-ID", _settings.TenantId);
        }

        if (method == HttpMethod.Post)
        {
            request.Headers.TryAddWithoutValidation(
                "Idempotency-Key", string.IsNullOrWhiteSpace(idempotencyKey) ? Guid.NewGuid().ToString() : idempotencyKey);
            request.Content = new StringContent(
                (body ?? new JsonObject()).ToJsonString(SerializerOptions), Encoding.UTF8, "application/json");
        }

        HttpResponseMessage response;
        try
        {
            response = await _httpClient.SendAsync(
                request, HttpCompletionOption.ResponseHeadersRead, cancellationToken).ConfigureAwait(false);
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new TimeoutException("The zWorkforce server did not respond before the request timeout.");
        }
        catch (HttpRequestException exception)
        {
            throw new InvalidOperationException("The zWorkforce server could not be reached.", exception);
        }

        await using var responseContent = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
        using var document = await JsonDocument.ParseAsync(responseContent, cancellationToken: cancellationToken)
            .ConfigureAwait(false);
        var raw = document.RootElement.GetRawText();

        if (!response.IsSuccessStatusCode)
        {
            throw CreateApiException(response.StatusCode, document.RootElement);
        }

        return raw;
    }

    private static ApiException CreateApiException(HttpStatusCode statusCode, JsonElement root)
    {
        var error = root.TryGetProperty("error", out var errorElement) && errorElement.ValueKind == JsonValueKind.Object
            ? errorElement
            : default;
        var code = error.ValueKind == JsonValueKind.Object && error.TryGetProperty("code", out var codeElement)
            ? codeElement.GetString() ?? "http_error"
            : "http_error";
        var message = error.ValueKind == JsonValueKind.Object && error.TryGetProperty("message", out var messageElement)
            ? messageElement.GetString() ?? "The server rejected the request."
            : "The server rejected the request.";
        var requestId = root.TryGetProperty("request_id", out var requestElement)
            ? requestElement.GetString()
            : null;
        return new ApiException(statusCode, code, message, requestId);
    }

    private static string NormalizeRoute(string route)
    {
        if (string.IsNullOrWhiteSpace(route))
        {
            throw new ArgumentException("An API route is required.", nameof(route));
        }

        return route.StartsWith("/", StringComparison.Ordinal) ? route : $"/{route}";
    }

    private static void AddQuery(ICollection<string> query, string name, string? value)
    {
        if (!string.IsNullOrWhiteSpace(value))
        {
            query.Add($"{name}={Uri.EscapeDataString(value.Trim())}");
        }
    }
}
