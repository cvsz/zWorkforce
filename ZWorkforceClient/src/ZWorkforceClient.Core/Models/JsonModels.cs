using System.Globalization;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ZWorkforceClient.Core.Models;

public static class JsonModels
{
    public static IReadOnlyList<JsonObject> Items(JsonObject? envelope)
    {
        if (envelope?["items"] is not JsonArray array)
        {
            return Array.Empty<JsonObject>();
        }

        return array.OfType<JsonObject>().ToArray();
    }

    public static string String(JsonObject? objectNode, string name, string fallback = "")
    {
        return objectNode?[name]?.GetValue<string>() ?? fallback;
    }

    public static bool Bool(JsonObject? objectNode, string name, bool fallback = false)
    {
        return objectNode?[name]?.GetValue<bool>() ?? fallback;
    }

    public static double Double(JsonObject? objectNode, string name, double fallback = 0)
    {
        if (objectNode?[name] is JsonValue value && value.TryGetValue<double>(out var number))
        {
            return number;
        }

        return fallback;
    }

    public static int Int(JsonObject? objectNode, string name, int fallback = 0)
    {
        if (objectNode?[name] is JsonValue value && value.TryGetValue<int>(out var number))
        {
            return number;
        }

        return fallback;
    }

    public static string Display(JsonNode? value)
    {
        if (value is null)
        {
            return "—";
        }

        if (value is JsonValue jsonValue && jsonValue.TryGetValue<string>(out var text))
        {
            return string.IsNullOrWhiteSpace(text) ? "—" : text;
        }

        if (value is JsonValue numberValue && numberValue.TryGetValue<double>(out var number))
        {
            return number.ToString("0.####", CultureInfo.InvariantCulture);
        }

        return value.ToJsonString(new JsonSerializerOptions { WriteIndented = false });
    }
}
