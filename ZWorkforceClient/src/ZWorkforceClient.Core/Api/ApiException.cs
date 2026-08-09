using System.Net;

namespace ZWorkforceClient.Core.Api;

public sealed class ApiException : Exception
{
    public ApiException(HttpStatusCode statusCode, string code, string message, string? requestId = null)
        : base(message)
    {
        StatusCode = statusCode;
        Code = string.IsNullOrWhiteSpace(code) ? "http_error" : code;
        RequestId = requestId;
    }

    public HttpStatusCode StatusCode { get; }

    public string Code { get; }

    public string? RequestId { get; }

    public bool IsUnauthorized => StatusCode is HttpStatusCode.Unauthorized or HttpStatusCode.Forbidden;

    public bool IsTransient =>
        StatusCode is HttpStatusCode.RequestTimeout or HttpStatusCode.TooManyRequests ||
        (int)StatusCode >= 500;
}
