using System.Text.Json.Serialization;

namespace ZWorkforceClient.Core.Models;

public sealed record HealthStatus(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("version")] string Version)
{
    public bool IsHealthy => string.Equals(Status, "ok", StringComparison.OrdinalIgnoreCase);
}

public sealed record ProviderStatus(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("available")] bool Available);

public sealed record ReadinessStatus(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("database")] bool Database,
    [property: JsonPropertyName("database_backend")] string DatabaseBackend,
    [property: JsonPropertyName("providers")] IReadOnlyList<ProviderStatus> Providers)
{
    public bool IsReady => string.Equals(Status, "ready", StringComparison.OrdinalIgnoreCase);
}

public enum TaskAction
{
    Approve,
    Reject,
    Cancel,
    Retry
}
