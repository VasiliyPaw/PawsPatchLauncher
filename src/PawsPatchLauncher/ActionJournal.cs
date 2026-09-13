using System.Text.Json;
using System.Threading.Channels;

namespace PawsPatchLauncher;

// Only static action/control identifiers and allowlisted configuration choices go here.
// Never pass input values, message bodies, URLs, account identifiers or exception messages.
public sealed class ActionJournalWriter
{
    public const long FileLimit = 2 * 1024 * 1024;
    public const int RetainedFiles = 3;
    private readonly string _root;
    private readonly long _limit;
    private readonly string _session = Guid.NewGuid().ToString("N");
    private readonly Channel<(string? Line, TaskCompletionSource? Flush)> _queue = Channel.CreateBounded<(string?, TaskCompletionSource?)>(
        new BoundedChannelOptions(1024) { SingleReader = true, FullMode = BoundedChannelFullMode.Wait });
    private long _sequence, _dropped;

    public ActionJournalWriter(string root, long limit = FileLimit)
    {
        _root = root; _limit = limit;
        _ = Task.Run(ConsumeAsync);
    }

    public static string Identifier(string value) => value.Length is > 0 and <= 160
        && value.All(c => char.IsAsciiLetterOrDigit(c) || c is '.' or '_' or '-' or ':' or '=' or ';') ? value : "redacted";

    public void Write(string action, string detail = "")
    {
        var record = JsonSerializer.Serialize(new Dictionary<string, object?> {
            ["utc"] = DateTimeOffset.UtcNow.ToString("O"), ["session"] = _session,
            ["sequence"] = Interlocked.Increment(ref _sequence), ["action"] = Identifier(action),
            ["detail"] = detail.Length == 0 ? null : Identifier(detail), ["droppedBefore"] = Interlocked.Exchange(ref _dropped, 0) });
        if (!_queue.Writer.TryWrite((record, null))) Interlocked.Increment(ref _dropped);
    }

    public async Task FlushAsync()
    {
        var completion = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await _queue.Writer.WriteAsync((null, completion)).ConfigureAwait(false);
        await completion.Task.ConfigureAwait(false);
    }

    private async Task ConsumeAsync()
    {
        await foreach (var item in _queue.Reader.ReadAllAsync())
        {
            if (item.Flush is not null) { item.Flush.TrySetResult(); continue; }
            try
            {
                Directory.CreateDirectory(_root);
                var path = Path.Combine(_root, "user-actions.jsonl");
                if (File.Exists(path) && new FileInfo(path).Length >= _limit)
                {
                    for (var i = RetainedFiles - 1; i >= 1; i--)
                    {
                        var source = i == 1 ? path : Path.Combine(_root, $"user-actions.{i - 1}.jsonl");
                        if (File.Exists(source)) File.Move(source, Path.Combine(_root, $"user-actions.{i}.jsonl"), true);
                    }
                }
                await File.AppendAllTextAsync(path, item.Line + "\n");
            }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException) { Interlocked.Increment(ref _dropped); }
        }
    }
}

public static class ActionJournal
{
    private static readonly Lazy<ActionJournalWriter> Writer = new(() => new(ActivityStore.Root));
    public static void Record(string action, string detail = "") => Writer.Value.Write(action, detail);
    public static Task FlushAsync() => Writer.Value.FlushAsync();
}
