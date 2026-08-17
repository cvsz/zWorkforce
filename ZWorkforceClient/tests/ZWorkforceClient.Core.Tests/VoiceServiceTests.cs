using System;
using System.Threading.Tasks;
using Xunit;
using ZWorkforceClient.Core.Services;

namespace ZWorkforceClient.Core.Tests
{
    public class VoiceServiceTests
    {
        [Fact]
        public void VoiceService_Initializes_With_Defaults()
        {
            var service = new VoiceService();
            Assert.Equal(VoiceSessionState.Idle, service.State);
            Assert.Equal("http://127.0.0.1:9569", service.ServerEndpoint);
            Assert.Equal("Win+Alt+Z", service.HotkeySequence);
        }

        [Fact]
        public async Task VoiceService_State_Transitions_Correctly()
        {
            var service = new VoiceService();
            service.StartListening();
            Assert.Equal(VoiceSessionState.Listening, service.State);

            var chunk = new byte[] { 0x00, 0x10, 0x20, 0x30 };
            var success = await service.SendAudioChunkAsync(chunk);
            Assert.True(success);
            Assert.Equal(VoiceSessionState.Streaming, service.State);

            service.StopListening();
            Assert.Equal(VoiceSessionState.Idle, service.State);
        }
    }
}
