using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;

namespace PawsPatchLauncher;

public static class ResumableDownload
{
    public static async Task DownloadAsync(HttpClient http, string url, string destination, long size,
        IProgress<(long Received, long? Total)>? progress, CancellationToken ct, DownloadControl? control = null)
    {
        for (var attempt = 0; attempt < 3; attempt++)
        {
            try
            {
                if (control is not null) await control.WaitAsync(ct);
                var offset = File.Exists(destination) ? new FileInfo(destination).Length : 0;
                if (size > 0 && offset == size) return; // Caller verifies the signed hash.
                if (size > 0 && offset > size) { File.Delete(destination); offset = 0; }
                using var request = new HttpRequestMessage(HttpMethod.Get, url);
                if (offset > 0) request.Headers.Range = new RangeHeaderValue(offset, null);
                using var response = await http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, ct);
                if (response.StatusCode == HttpStatusCode.RequestedRangeNotSatisfiable && offset > 0)
                {
                    File.Delete(destination);
                    continue;
                }
                if (!response.IsSuccessStatusCode)
                    throw new HttpRequestException($"HTTP {(int)response.StatusCode}: {url}", null, response.StatusCode);
                var append = offset > 0 && response.StatusCode == HttpStatusCode.PartialContent;
                if (response.StatusCode == HttpStatusCode.PartialContent && response.Content.Headers.ContentRange?.From != (append ? offset : 0))
                    throw new InvalidDataException("Download server returned an incorrect byte range: " + url);
                if (!append) offset = 0; // Servers ignoring Range send a complete replacement.
                var total = size > 0 ? size : response.Content.Headers.ContentLength + offset;
                await using var input = await response.Content.ReadAsStreamAsync(ct);
                await using var output = new FileStream(destination, append ? FileMode.Append : FileMode.Create, FileAccess.Write, FileShare.None, 65536, true);
                var buffer = new byte[65536];
                var received = offset;
                progress?.Report((received, total));
                while (true)
                {
                    if (control is not null) await control.WaitAsync(ct);
                    using var idle = CancellationTokenSource.CreateLinkedTokenSource(ct);
                    idle.CancelAfter(TimeSpan.FromSeconds(30));
                    var count = await input.ReadAsync(buffer, idle.Token);
                    if (count == 0) break;
                    if (size > 0 && received + count > size) throw new InvalidDataException("Downloaded file exceeds signed size: " + url);
                    if (control is not null) await control.PaceAsync(count, ct);
                    await output.WriteAsync(buffer.AsMemory(0, count), ct);
                    received += count;
                    progress?.Report((received, total));
                }
                if (total is > 0 && received != total) throw new IOException("Download ended before the file was complete: " + url);
                return;
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested) { throw; }
            catch (Exception ex) when (attempt < 2 && (ex is IOException || ex is OperationCanceledException || ex is HttpRequestException h && (h.StatusCode is null || (int)h.StatusCode >= 500 || h.StatusCode == HttpStatusCode.TooManyRequests)))
            {
                await Task.Delay(500 * (attempt + 1), ct);
            }
            catch (OperationCanceledException error) when (!ct.IsCancellationRequested)
            { throw new TimeoutException("The download server stopped responding. Partial bytes are retained.", error); }
        }
        throw new IOException("The server could not resume this download: " + url);
    }
}
