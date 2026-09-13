using System.Net.Http;

namespace PawsPatchLauncher;

// The dedicated offline fixture blocks every launcher-owned HTTP transport.
// Ordinary installs and other local test profiles keep their normal networking.
internal static class LocalTestNetwork
{
    internal static HttpMessageHandler Handler(Func<HttpMessageHandler> online)
    {
        if (ActivityStore.LocalTestProfile is not null)
        {
            try
            {
                if (File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "launcher.test-mode")).Trim() == "01-offline")
                    return new OfflineHandler();
            }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
        return online();
    }

    private sealed class OfflineHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return Task.FromException<HttpResponseMessage>(new HttpRequestException("Local offline test: network unavailable."));
        }
    }
}
