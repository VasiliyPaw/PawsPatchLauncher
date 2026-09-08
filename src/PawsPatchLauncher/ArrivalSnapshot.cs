namespace PawsPatchLauncher;

/// <summary>Presentation delta only. First load/context changes are quiet; ACKs keep the same key.</summary>
public sealed class ArrivalSnapshot<T> where T : notnull
{
    private string? _scope;
    private HashSet<T> _previous = [];
    private bool _ready;

    public HashSet<T> Observe(string scope, IEnumerable<T> keys, bool ready)
    {
        var current = keys.ToHashSet();
        var added = ready && _ready && _scope == scope ? current.Except(_previous).ToHashSet() : [];
        _scope = scope; _previous = current; _ready = ready;
        return added;
    }
}
