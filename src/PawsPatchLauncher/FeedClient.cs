using System.Net.Http;
using System.Text;
using System.Text.Json;

namespace PawsPatchLauncher;

public sealed class FeedClient
{
    private readonly HttpClient _http;
    private readonly LauncherConfiguration _configuration;
    private readonly string _cacheRoot;

    public FeedClient(LauncherConfiguration configuration)
    {
        _configuration = configuration;
        _cacheRoot = string.IsNullOrWhiteSpace(configuration.CacheRoot)
            ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "PawsPatchLauncher")
            : Path.GetFullPath(configuration.CacheRoot);
        _http = new HttpClient { Timeout = TimeSpan.FromMinutes(10) };
        _http.DefaultRequestHeaders.UserAgent.ParseAdd("PawsPatchLauncher/0.2");
    }

    public async Task<ChannelManifest?> GetChannelAsync(string channel = "stable", CancellationToken cancellationToken = default)
    {
        var sources = channel.Equals("beta", StringComparison.OrdinalIgnoreCase)
            ? _configuration.BetaFeedUrls
            : _configuration.FeedUrls;
        if (sources.Count == 0) return null;
        var errors = new List<Exception>();
        foreach (var source in sources)
        {
            try
            {
                var bytes = await ReadBytesAsync(source, cancellationToken);
                var manifest = ParseFeed(bytes, IsRemote(source));
                if (!manifest.Channel.Equals(channel, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException($"Requested update channel '{channel}', received '{manifest.Channel}'.");
                return manifest;
            }
            catch (Exception ex) { errors.Add(ex); }
        }
        throw new AggregateException("Every update feed failed.", errors);
    }

    public async Task<string> DownloadVerifiedAsync(PackageRelease package, IProgress<(long Received, long? Total)>? progress,
        CancellationToken cancellationToken = default)
    {
        var cacheRoot = Path.Combine(_cacheRoot, "downloads", package.Id, package.Version);
        Directory.CreateDirectory(cacheRoot);
        var destination = Path.Combine(cacheRoot, package.Sha256.ToUpperInvariant() + ".zip");
        if (File.Exists(destination) && string.Equals(await CryptoAndIO.Sha256Async(destination, cancellationToken), package.Sha256, StringComparison.OrdinalIgnoreCase))
            return destination;

        var errors = new List<Exception>();
        foreach (var url in package.Urls)
        {
            var temporary = destination + ".download";
            try
            {
                if (File.Exists(temporary)) File.Delete(temporary);
                await DownloadAsync(url, temporary, progress, cancellationToken);
                var actual = await CryptoAndIO.Sha256Async(temporary, cancellationToken);
                if (!string.Equals(actual, package.Sha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException($"SHA-256 mismatch for {package.Id}: expected {package.Sha256}, got {actual}.");
                File.Move(temporary, destination, true);
                return destination;
            }
            catch (Exception ex)
            {
                errors.Add(ex);
                try { if (File.Exists(temporary)) File.Delete(temporary); } catch { }
            }
        }
        throw new AggregateException($"Every download mirror failed for {package.Id}.", errors);
    }

    public async Task<string> DownloadLauncherAsync(LauncherRelease release, IProgress<(long Received, long? Total)>? progress,
        CancellationToken cancellationToken = default)
    {
        var directory = Path.Combine(_cacheRoot, "launcher");
        Directory.CreateDirectory(directory);
        var destination = Path.Combine(directory, $"PawsPatchLauncher-{release.Version}.exe");
        if (File.Exists(destination) && string.Equals(await CryptoAndIO.Sha256Async(destination, cancellationToken), release.Sha256, StringComparison.OrdinalIgnoreCase))
            return destination;

        var errors = new List<Exception>();
        foreach (var url in release.Urls)
        {
            var temporary = destination + ".download";
            try
            {
                if (File.Exists(temporary)) File.Delete(temporary);
                await DownloadAsync(url, temporary, progress, cancellationToken);
                var actual = await CryptoAndIO.Sha256Async(temporary, cancellationToken);
                if (!actual.Equals(release.Sha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException($"Launcher SHA-256 mismatch: expected {release.Sha256}, got {actual}.");
                File.Move(temporary, destination, true);
                return destination;
            }
            catch (Exception ex)
            {
                errors.Add(ex);
                try { if (File.Exists(temporary)) File.Delete(temporary); } catch { }
            }
        }
        throw new AggregateException("Every launcher download mirror failed.", errors);
    }

    private ChannelManifest ParseFeed(byte[] bytes, bool remote)
    {
        var text = Encoding.UTF8.GetString(bytes);
        SignedFeedEnvelope? envelope = null;
        try { envelope = JsonSerializer.Deserialize(text, LauncherJsonContext.Default.SignedFeedEnvelope); } catch { }

        byte[] payload;
        if (envelope is not null && !string.IsNullOrWhiteSpace(envelope.Payload))
        {
            payload = Convert.FromBase64String(envelope.Payload);
            if (!CryptoAndIO.VerifySignature(payload, envelope.Signature, _configuration.PublicKeyPem))
                throw new CryptographicException("The update manifest signature is invalid.");
        }
        else
        {
            if (remote && _configuration.RequireSignedRemoteFeed)
                throw new CryptographicException("An unsigned remote update manifest was rejected.");
            payload = bytes;
        }

        var manifest = JsonSerializer.Deserialize(payload, LauncherJsonContext.Default.ChannelManifest)
                       ?? throw new InvalidDataException("The update manifest is empty.");
        if (manifest.SchemaVersion != 1) throw new InvalidDataException($"Unsupported update manifest schema: {manifest.SchemaVersion}.");
        return manifest;
    }

    private async Task DownloadAsync(string source, string destination, IProgress<(long Received, long? Total)>? progress,
        CancellationToken cancellationToken)
    {
        if (!IsRemote(source))
        {
            var local = source.StartsWith("file:", StringComparison.OrdinalIgnoreCase) ? new Uri(source).LocalPath : source;
            await using var input = new FileStream(local, FileMode.Open, FileAccess.Read, FileShare.Read, 1024 * 1024, true);
            await using var output = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1024 * 1024, true);
            await CopyWithProgressAsync(input, output, input.Length, progress, cancellationToken);
            return;
        }

        using var response = await _http.GetAsync(source, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        response.EnsureSuccessStatusCode();
        await using var inputStream = await response.Content.ReadAsStreamAsync(cancellationToken);
        await using var outputStream = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1024 * 1024, true);
        await CopyWithProgressAsync(inputStream, outputStream, response.Content.Headers.ContentLength, progress, cancellationToken);
    }

    private static async Task CopyWithProgressAsync(Stream input, Stream output, long? total,
        IProgress<(long Received, long? Total)>? progress, CancellationToken cancellationToken)
    {
        var buffer = new byte[1024 * 1024];
        long received = 0;
        int read;
        while ((read = await input.ReadAsync(buffer, cancellationToken)) > 0)
        {
            await output.WriteAsync(buffer.AsMemory(0, read), cancellationToken);
            received += read;
            progress?.Report((received, total));
        }
    }

    private async Task<byte[]> ReadBytesAsync(string source, CancellationToken cancellationToken)
    {
        if (!IsRemote(source))
        {
            var local = source.StartsWith("file:", StringComparison.OrdinalIgnoreCase) ? new Uri(source).LocalPath : source;
            return await File.ReadAllBytesAsync(local, cancellationToken);
        }
        return await _http.GetByteArrayAsync(source, cancellationToken);
    }

    private static bool IsRemote(string value)
        => Uri.TryCreate(value, UriKind.Absolute, out var uri) && (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps);
}
