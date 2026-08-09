using Xunit;
using ZWorkforceClient.Core.Models;

namespace ZWorkforceClient.Core.Tests;

public sealed class ConnectionSettingsTests
{
    [Theory]
    [InlineData("localhost:9569", "http://localhost:9569/")]
    [InlineData("http://localhost:9569/", "http://localhost:9569/")]
    [InlineData("https://workforce.example", "https://workforce.example/")]
    public void Base_url_accepts_common_operator_input(string input, string expected)
    {
        var settings = new ConnectionSettings(input, "key", "tenant");

        Assert.Equal(expected, settings.BaseUrl);
    }

    [Fact]
    public void Blank_base_url_is_rejected()
    {
        Assert.Throws<ArgumentException>(() => new ConnectionSettings(" ", "key"));
    }

    [Fact]
    public void Non_http_schemes_are_rejected()
    {
        Assert.Throws<ArgumentException>(() => new ConnectionSettings("ftp://workforce.example", "key"));
    }
}
