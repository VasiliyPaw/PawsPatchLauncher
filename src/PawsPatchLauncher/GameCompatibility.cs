namespace PawsPatchLauncher;

public enum GameCompatibilityState { Unchecked, Checking, Supported, Unsupported, Unavailable }

public readonly record struct GameFileStamp(long Length,long LastWriteTicks)
{
    public static GameFileStamp Read(string path)
    {
        var info=new FileInfo(path);
        return info.Exists?new(info.Length,info.LastWriteTimeUtc.Ticks):new(-1,0);
    }
}

public static class GameCompatibility
{
    public static async Task<GameCompatibilityState> CheckAsync(string path,IReadOnlyList<string> hashes,CancellationToken ct=default)
    {
        if(hashes.Count==0)return GameCompatibilityState.Unchecked;
        try
        {
            var before=GameFileStamp.Read(path);
            if(before.Length<0)return GameCompatibilityState.Unavailable;
            var hash=await CryptoAndIO.Sha256Async(path,ct).ConfigureAwait(false);
            if(before!=GameFileStamp.Read(path))return GameCompatibilityState.Unavailable;
            return hashes.Contains(hash,StringComparer.OrdinalIgnoreCase)?GameCompatibilityState.Supported:GameCompatibilityState.Unsupported;
        }
        catch(OperationCanceledException){throw;}
        catch(IOException){return GameCompatibilityState.Unavailable;}
        catch(UnauthorizedAccessException){return GameCompatibilityState.Unavailable;}
    }
}
