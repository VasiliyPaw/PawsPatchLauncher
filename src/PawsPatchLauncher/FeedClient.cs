using System.Net.Http;
using System.Text;
using System.Text.Json;

namespace PawsPatchLauncher;

public sealed class FeedClient
{
    private readonly HttpClient _http;
    private readonly LauncherConfiguration _configuration;
    private readonly string _cacheRoot;

    public FeedClient(LauncherConfiguration configuration, HttpClient? http = null)
    {
        _configuration = configuration;
        _cacheRoot = string.IsNullOrWhiteSpace(configuration.CacheRoot)
            ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "PawsPatchLauncher")
            : Path.GetFullPath(configuration.CacheRoot);
        _http = http ?? new HttpClient { Timeout = TimeSpan.FromMinutes(10) };
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
                await ArchiveAsync(bytes, manifest, cancellationToken);
                return manifest;
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw; }
            catch (Exception ex) { errors.Add(ex); }
        }
        throw new AggregateException("Every update feed failed.", errors);
    }

    public async Task<string> DownloadVerifiedAsync(PackageRelease package, IProgress<(long Received, long? Total)>? progress,
        CancellationToken cancellationToken = default)
    {
        var cacheRoot = Path.Combine(_cacheRoot, "downloads", package.Id, package.Version);
        Directory.CreateDirectory(cacheRoot);
        var destination = CachedPackagePath(package);
        if (File.Exists(destination) && string.Equals(await CryptoAndIO.Sha256Async(destination, cancellationToken), package.Sha256, StringComparison.OrdinalIgnoreCase))
            return destination;

        var errors = new List<Exception>();
        foreach (var url in package.Urls.Concat(package.Urls))
        {
            var temporary = destination + ".download";
            try
            {
                await DownloadAsync(url, temporary, progress, cancellationToken, package.Size);
                var actual = await CryptoAndIO.Sha256Async(temporary, cancellationToken);
                if (!string.Equals(actual, package.Sha256, StringComparison.OrdinalIgnoreCase))
                {
                    File.Delete(temporary);
                    throw new InvalidDataException($"SHA-256 mismatch for {package.Id}: expected {package.Sha256}, got {actual}.");
                }
                File.Move(temporary, destination, true);
                return destination;
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw; }
            catch (Exception ex)
            {
                errors.Add(ex);
            }
        }
        throw new AggregateException($"Every download mirror failed for {package.Id}.", errors);
    }

    public bool IsPackageCached(PackageRelease package)
    {
        var path = CachedPackagePath(package);
        if (!File.Exists(path)) return false;
        return package.Size <= 0 || new FileInfo(path).Length == package.Size;
    }

    private string CachedPackagePath(PackageRelease package)
        => Path.Combine(_cacheRoot, "downloads", package.Id, package.Version, package.Sha256.ToUpperInvariant() + ".zip");

    public async Task<string> DownloadLauncherAsync(LauncherRelease release, IProgress<(long Received, long? Total)>? progress,
        CancellationToken cancellationToken = default)
    {
        var directory = Path.Combine(_cacheRoot, "launcher");
        Directory.CreateDirectory(directory);
        var destination = CryptoAndIO.SafeChildPath(directory, $"PawsPatchLauncher-{release.Version}-{release.Sha256}.exe");
        if (File.Exists(destination) && string.Equals(await CryptoAndIO.Sha256Async(destination, cancellationToken), release.Sha256, StringComparison.OrdinalIgnoreCase))
            return destination;

        var errors = new List<Exception>();
        foreach (var url in release.Urls.Concat(release.Urls))
        {
            var temporary = destination + ".download";
            try
            {
                await DownloadAsync(url, temporary, progress, cancellationToken, release.Size);
                var actual = await CryptoAndIO.Sha256Async(temporary, cancellationToken);
                if (!actual.Equals(release.Sha256, StringComparison.OrdinalIgnoreCase))
                {
                    File.Delete(temporary);
                    throw new InvalidDataException($"Launcher SHA-256 mismatch: expected {release.Sha256}, got {actual}.");
                }
                File.Move(temporary, destination, true);
                return destination;
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw; }
            catch (Exception ex)
            {
                errors.Add(ex);
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
        CancellationToken cancellationToken, long expectedSize = 0)
    {
        if (!IsRemote(source))
        {
            var local = source.StartsWith("file:", StringComparison.OrdinalIgnoreCase) ? new Uri(source).LocalPath : source;
            await using var input = new FileStream(local, FileMode.Open, FileAccess.Read, FileShare.Read, 1024 * 1024, true);
            await using var output = new FileStream(destination, FileMode.Create, FileAccess.Write, FileShare.None, 1024 * 1024, true);
            await CopyWithProgressAsync(input, output, input.Length, progress, cancellationToken);
            return;
        }

        await ResumableDownload.DownloadAsync(_http, source, destination, expectedSize, progress, cancellationToken);
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

    private string ArchivedPath(string id)
    {
        if (id.Length != 64 || !id.All(Uri.IsHexDigit)) throw new InvalidDataException("Invalid release fingerprint.");
        return Path.Combine(_cacheRoot, "releases", id.ToUpperInvariant() + ".json");
    }

    private async Task ArchiveAsync(byte[] bytes, ChannelManifest manifest, CancellationToken ct)
        => await CryptoAndIO.AtomicWriteTextAsync(ArchivedPath(ChannelFingerprint.Create(manifest)), Encoding.UTF8.GetString(bytes), ct);

    public ChannelManifest LoadArchived(string id, string channel)
    {
        var manifest = ParseFeed(File.ReadAllBytes(ArchivedPath(id)), _configuration.RequireSignedRemoteFeed);
        if (!manifest.Channel.Equals(channel, StringComparison.OrdinalIgnoreCase) || ChannelFingerprint.Create(manifest) != id.ToUpperInvariant())
            throw new InvalidDataException("Archived release identity mismatch.");
        return manifest;
    }

    public async Task<ChannelManifest> GetPreviousAsync(ReleaseReference reference, string channel)
    {
        var bytes = await ReadBytesAsync(reference.Url, CancellationToken.None);
        var manifest = ParseFeed(bytes, true);
        if (!manifest.Channel.Equals(channel, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Previous release channel mismatch.");
        await ArchiveAsync(bytes, manifest, CancellationToken.None);
        return manifest;
    }

    public List<ChannelManifest> Archived(string channel)
    {
        var root = Path.Combine(_cacheRoot, "releases");
        var result = new List<ChannelManifest>();
        if (!Directory.Exists(root)) return result;
        foreach (var file in Directory.EnumerateFiles(root, "*.json"))
            try { result.Add(LoadArchived(Path.GetFileNameWithoutExtension(file), channel)); } catch { }
        return result.OrderByDescending(x => x.PublishedAt, StringComparer.Ordinal).ToList();
    }
}
