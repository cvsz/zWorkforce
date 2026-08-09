using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json.Nodes;
using Xunit;
using ZWorkforceClient.Core.Api;
using ZWorkforceClient.Core.Models;

namespace ZWorkforceClient.Core.Tests;

public sealed class ApiClientTests
{
    [Fact]
    public void Connection_settings_normalize_base_url_and_default_tenant()
    {
        var settings = new ConnectionSettings(" https://workforce.example/api/ ", "secret");

        Assert.Equal("https://workforce.example/api/", settings.BaseUrl);
        Assert.Equal("default", settings.TenantId);
        Assert.Equal(new Uri("https://workforce.example/api/"), settings.BaseUri);
    }

    [Fact]
    public async Task Authenticated_requests_send_bearer_and_tenant_headers()
    {
        var handler = new RecordingHandler(_ => JsonResponse("{\"items\":[]}"));
        var client = CreateClient(handler);

        await client.GetCollectionAsync("/api/v1/agents");

        Assert.Equal(HttpMethod.Get, handler.LastRequest!.Method);
        Assert.Equal("Bearer secret", handler.LastRequest.Headers.Authorization!.ToString());
        Assert.Equal("acme", handler.LastRequest.Headers.GetValues("X-Tenant-ID").Single());
        Assert.Equal("/api/v1/agents", handler.LastRequest.RequestUri!.AbsolutePath);
    }

    [Fact]
    public async Task Public_health_does_not_require_credentials()
    {
        var handler = new RecordingHandler(_ => JsonResponse("{\"status\":\"ok\",\"version\":\"3.0.1\"}"));
        var client = new ApiClient(new HttpClient(handler), new ConnectionSettings("http://localhost:9569", ""));

        var health = await client.GetHealthAsync();

        Assert.Equal("ok", health.Status);
        Assert.Equal("3.0.1", health.Version);
        Assert.Null(handler.LastRequest!.Headers.Authorization);
        Assert.DoesNotContain("X-Tenant-ID", handler.LastRequest.Headers.Select(x => x.Key));
    }

    [Fact]
    public async Task Server_errors_preserve_code_message_and_request_id()
    {
        var handler = new RecordingHandler(_ => JsonResponse(
            "{\"error\":{\"code\":\"task_forbidden\",\"message\":\"not allowed\"},\"request_id\":\"req-42\"}",
            HttpStatusCode.Forbidden));
        var client = CreateClient(handler);

        var exception = await Assert.ThrowsAsync<ApiException>(() => client.GetCollectionAsync("/api/v1/tasks"));

        Assert.Equal(HttpStatusCode.Forbidden, exception.StatusCode);
        Assert.Equal("task_forbidden", exception.Code);
        Assert.Equal("not allowed", exception.Message);
        Assert.Equal("req-42", exception.RequestId);
    }

    [Fact]
    public async Task Mutating_requests_get_an_idempotency_key_and_json_body()
    {
        var handler = new RecordingHandler(_ => JsonResponse("{\"id\":\"task-1\"}", HttpStatusCode.Created));
        var client = CreateClient(handler);

        await client.PostJsonAsync(
            "/api/v1/tasks",
            new JsonObject { ["agent_id"] = "researcher", ["prompt"] = "hello" },
            idempotencyKey: "fixed-key");

        Assert.Equal(HttpMethod.Post, handler.LastRequest!.Method);
        Assert.Equal("fixed-key", handler.LastRequest.Headers.GetValues("Idempotency-Key").Single());
        Assert.Equal("application/json", handler.LastRequest.Content!.Headers.ContentType!.MediaType);
        Assert.Contains("researcher", await handler.LastRequest.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task Task_actions_use_the_expected_route_and_return_json()
    {
        var handler = new RecordingHandler(_ => JsonResponse("{\"id\":\"task-1\",\"status\":\"canceled\"}"));
        var client = CreateClient(handler);

        var result = await client.TaskActionAsync("task-1", TaskAction.Cancel, "operator request", "action-key");

        Assert.Equal("canceled", result["status"]!.GetValue<string>());
        Assert.Equal("/api/v1/tasks/task-1/cancel", handler.LastRequest!.RequestUri!.AbsolutePath);
        Assert.Equal("action-key", handler.LastRequest.Headers.GetValues("Idempotency-Key").Single());
    }

    [Fact]
    public async Task Readiness_parses_database_and_provider_state()
    {
        var handler = new RecordingHandler(_ => JsonResponse(
            "{\"status\":\"ready\",\"database\":true,\"database_backend\":\"postgresql\",\"providers\":[{\"name\":\"primary\",\"available\":true}]}"));
        var client = CreateClient(handler);

        var ready = await client.GetReadinessAsync();

        Assert.True(ready.IsReady);
        Assert.True(ready.Database);
        Assert.Equal("postgresql", ready.DatabaseBackend);
        Assert.Single(ready.Providers);
        Assert.Equal("primary", ready.Providers[0].Name);
    }

    private static ApiClient CreateClient(RecordingHandler handler)
    {
        return new ApiClient(
            new HttpClient(handler),
            new ConnectionSettings("https://workforce.example/", "secret", "acme"));
    }

    private static HttpResponseMessage JsonResponse(string body, HttpStatusCode status = HttpStatusCode.OK)
    {
        return new HttpResponseMessage(status)
        {
            Content = new StringContent(body, Encoding.UTF8, "application/json")
        };
    }

    private sealed class RecordingHandler(Func<HttpRequestMessage, HttpResponseMessage> responder) : HttpMessageHandler
    {
        public HttpRequestMessage? LastRequest { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            LastRequest = request;
            return Task.FromResult(responder(request));
        }
    }
}
