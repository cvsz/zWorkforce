using System;
using System.Threading.Tasks;

namespace ZWorkforceClient.Core.Services
{
    public enum VoiceSessionState
    {
        Idle,
        Listening,
        Streaming,
        Processing,
        Error
    }

    public class VoiceService
    {
        public VoiceSessionState State { get; private set; } = VoiceSessionState.Idle;
        public string ServerEndpoint { get; }
        public string HotkeySequence { get; }

        public VoiceService(string serverEndpoint = "http://127.0.0.1:9569", string hotkeySequence = "Win+Alt+Z")
        {
            ServerEndpoint = serverEndpoint;
            HotkeySequence = hotkeySequence;
        }

        public void StartListening()
        {
            State = VoiceSessionState.Listening;
        }

        public void StopListening()
        {
            State = VoiceSessionState.Idle;
        }

        public async Task<bool> SendAudioChunkAsync(byte[] pcm16Data)
        {
            if (State != VoiceSessionState.Listening && State != VoiceSessionState.Streaming)
            {
                return false;
            }

            if (pcm16Data == null || pcm16Data.Length == 0)
            {
                return false;
            }

            State = VoiceSessionState.Streaming;
            await Task.Delay(1); // Simulation of async HTTP/WebSocket dispatch
            return true;
        }
    }
}
