namespace PawsPatchLauncher;

public static class RecoveryCode
{
    public const int Length = 6;

    // Allow copying a code with surrounding whitespace or a visual separator.
    // Never truncate or extract digits from a link, prose, or a longer code.
    public static string Normalize(string value) => value.Length > 64
        ? "" : new string(value.Where(c => !char.IsWhiteSpace(c)).ToArray());
    public static bool IsPartial(string value) => value.Length <= Length && value.All(c => c is >= '0' and <= '9');
    public static bool IsComplete(string value) => value.Length == Length && IsPartial(value);
}
