using System.IO.Compression;
using System.Net.Http;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

public static class RebornInstall
{
    public static string ChannelPath(string root, string channel)
    {
        if (!RebornBuild.IsChannel(channel)) throw new InvalidDataException("Invalid Reborn channel.");
        var path = Path.Combine(Path.GetFullPath(root),channel == "stable" ? "Release" : "Beta"); RemovalSafety.CheckNoLinks(path); return path;
    }
    public static RebornBuild? Installed(string? root, string channel)
    {
        if (string.IsNullOrWhiteSpace(root)) return null;
        try
        {
            var build = ReadMarker(root,channel);
            if (build is null || !File.Exists(Executable(root,build))) return null;
            return build;
        }
        catch (Exception e) when (e is IOException or InvalidDataException or UnauthorizedAccessException or JsonException or ArgumentException) { return null; }
    }
    public static string Executable(string root, RebornBuild build)
    {
        RebornBuild.Validate(build);
        var path = Path.Combine(ChannelPath(root,build.Channel),"builds",build.Id.ToString("N"),build.Executable);
        RemovalSafety.CheckNoLinks(path); return path;
    }
    public static async Task DownloadAsync(RebornTicket ticket, string archive, IProgress<(long Received,long Total)>? progress, CancellationToken ct)
    {
        if (ticket.ExpiresAt <= DateTimeOffset.UtcNow) throw new IOException("Reborn download permission expired.");
        RemovalSafety.CheckNoLinks(archive); Directory.CreateDirectory(Path.GetDirectoryName(archive)!);
        using var http = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = Timeout.InfiniteTimeSpan };
        using var response = await http.GetAsync(ticket.Url,HttpCompletionOption.ResponseHeadersRead,ct).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();
        if (response.Content.Headers.ContentLength is { } length && length != ticket.Build.Size) throw new InvalidDataException("Reborn download size mismatch.");
        await using var input = await response.Content.ReadAsStreamAsync(ct).ConfigureAwait(false);
        await using var output = new FileStream(archive,FileMode.CreateNew,FileAccess.Write,FileShare.None,131072,true);
        var buffer = new byte[131072]; long received = 0;
        for (var count = await input.ReadAsync(buffer,ct); count > 0; count = await input.ReadAsync(buffer,ct))
        {
            received += count; if (received > ticket.Build.Size) throw new InvalidDataException("Reborn download exceeds expected size.");
            await output.WriteAsync(buffer.AsMemory(0,count),ct); progress?.Report((received,ticket.Build.Size));
        }
        if (received != ticket.Build.Size) throw new InvalidDataException("Incomplete Reborn download.");
    }
    public static async Task InstallAsync(string root, RebornBuild build, string archive, Func<Task> authorize, CancellationToken ct)
    {
        RebornBuild.Validate(build);
        if (new FileInfo(archive).Length != build.Size || !(await CryptoAndIO.Sha256Async(archive,ct)).Equals(build.Sha256,StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Reborn archive verification failed.");
        var channel = ChannelPath(root,build.Channel);
        // A malformed/unrelated marker is not ours to overwrite.
        _ = ReadMarker(root,build.Channel); Directory.CreateDirectory(channel);
        var stage = Path.Combine(channel,".staging-"+Guid.NewGuid().ToString("N")); Directory.CreateDirectory(stage);
        try
        {
            await Task.Run(async () =>
            {
                using var zip = ZipFile.OpenRead(archive);
                if (zip.Entries.Count is < 1 or > 100000) throw new InvalidDataException("Invalid Reborn archive file count.");
                long expanded = 0; var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (var entry in zip.Entries)
                {
                    ct.ThrowIfCancellationRequested();
                    var name = entry.FullName.Replace('\\','/'); var parts = name.TrimEnd('/').Split('/');
                    if (name.StartsWith('/') || parts.Any(p => p is "" or "." or ".." || p.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 || p.EndsWith('.') || p.EndsWith(' ')
                        || Regex.IsMatch(p,@"\A(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\z",RegexOptions.IgnoreCase))
                        || !seen.Add(name.TrimEnd('/')) || ((entry.ExternalAttributes >> 16) & 0xF000) == 0xA000 || (entry.ExternalAttributes & (int)FileAttributes.ReparsePoint) != 0)
                        throw new InvalidDataException("Unsafe Reborn archive path.");
                    expanded = checked(expanded+entry.Length);
                    if (expanded > 34359738368) throw new InvalidDataException("Reborn archive expands beyond the limit.");
                    var target = CryptoAndIO.SafeChildPath(stage,name); RemovalSafety.CheckNoLinks(target);
                    if (name.EndsWith('/')) { Directory.CreateDirectory(target); continue; }
                    Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                    await using var source = entry.Open(); await using var destination = new FileStream(target,FileMode.CreateNew,FileAccess.Write,FileShare.None,131072,true);
                    var buffer = new byte[131072]; long copied = 0;
                    for (var count = await source.ReadAsync(buffer,ct); count > 0; count = await source.ReadAsync(buffer,ct))
                    { copied += count; if (copied > entry.Length) throw new InvalidDataException("Reborn entry exceeds declared size."); await destination.WriteAsync(buffer.AsMemory(0,count),ct); }
                    if (copied != entry.Length) throw new InvalidDataException("Incomplete Reborn archive entry.");
                }
            },ct);
            if (!File.Exists(Path.Combine(stage,build.Executable))) throw new InvalidDataException("Reborn executable is missing from the archive.");
            await authorize(); ct.ThrowIfCancellationRequested();
            var final = Path.GetDirectoryName(Executable(root,build))!; Directory.CreateDirectory(Path.GetDirectoryName(final)!);
            // Never overwrite an existing installation, including unknown user files.
            RemovalSafety.CheckNoLinks(final);
            if (Directory.Exists(final))
            {
                // Recover a completed move whose active-marker write was interrupted.
                // Existing user files are reused only when every path and byte matches.
                var expected = SafeFiles(stage).ToArray(); var existing = SafeFiles(final).ToArray();
                if (!expected.ToHashSet(StringComparer.OrdinalIgnoreCase).SetEquals(existing)) throw new IOException("Reborn build directory contains different files.");
                foreach (var name in expected)
                    if (!(await CryptoAndIO.Sha256Async(CryptoAndIO.SafeChildPath(stage,name),ct)).Equals(await CryptoAndIO.Sha256Async(CryptoAndIO.SafeChildPath(final,name),ct),StringComparison.OrdinalIgnoreCase))
                        throw new IOException("Reborn build directory contains different files.");
            }
            else Directory.Move(stage,final);
            _ = ReadMarker(root,build.Channel);
            await CryptoAndIO.AtomicWriteTextAsync(Path.Combine(channel,"active.json"),JsonSerializer.Serialize(build),ct);
        }
        finally
        {
            var fullStage = Path.GetFullPath(stage); var fullChannel = Path.GetFullPath(channel).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
            if (Directory.Exists(fullStage) && fullStage.StartsWith(fullChannel,StringComparison.OrdinalIgnoreCase)
                && Path.GetFileName(fullStage).StartsWith(".staging-",StringComparison.Ordinal))
            { RemovalSafety.CheckNoLinks(fullStage); Directory.Delete(fullStage,true); }
        }
    }
    private static RebornBuild? ReadMarker(string root,string channel)
    {
        var marker = Path.Combine(ChannelPath(root,channel),"active.json"); RemovalSafety.CheckNoLinks(marker);
        if (!File.Exists(marker)) return null;
        if (new FileInfo(marker).Length > 524288) throw new InvalidDataException("Invalid Reborn installation marker.");
        RebornBuild build;
        try { build = JsonSerializer.Deserialize<RebornBuild>(File.ReadAllText(marker)) ?? throw new InvalidDataException("Invalid Reborn installation marker."); }
        catch (JsonException error) { throw new InvalidDataException("Invalid Reborn installation marker.",error); }
        RebornBuild.Validate(build); if (build.Channel != channel) throw new InvalidDataException("Wrong Reborn installation channel."); return build;
    }
    private static IEnumerable<string> SafeFiles(string root)
    {
        var pending = new Stack<string>(); pending.Push(root);
        while (pending.Count > 0)
            foreach (var entry in Directory.EnumerateFileSystemEntries(pending.Pop()))
            { RemovalSafety.CheckNoLinks(entry); if (Directory.Exists(entry)) pending.Push(entry); else yield return Path.GetRelativePath(root,entry); }
    }
}
