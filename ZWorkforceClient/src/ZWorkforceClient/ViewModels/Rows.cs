namespace ZWorkforceClient.ViewModels;

public sealed record ProviderRow(string Name, string Kind, bool Available, string Priority);

public sealed record TaskRow(
    string Id,
    string Status,
    string Agent,
    string Tier,
    string Outcome,
    string Cost,
    string CreatedAt);

public sealed record AgentRow(string Id, string Name, string Description, string Status);

public sealed record ResourceRow(string Name, string Detail, string Status);

public sealed record KeyValueRow(string Name, string Value);
