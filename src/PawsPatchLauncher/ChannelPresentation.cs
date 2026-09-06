using System.Text.RegularExpressions;

namespace PawsPatchLauncher;

/// <summary>Display names only. Stored channel IDs, signed feeds and sharing codes stay unchanged.</summary>
public static partial class ChannelPresentation
{
    public static string Name(string channel, string language) => channel.ToLowerInvariant() switch
    {
        "stable" => language == "en" ? "Release" : "Релиз",
        "beta" => language == "en" ? "Beta" : "Бета",
        _ => channel
    };

    // Old signed changelogs retain their original bytes. Translate channel terminology
    // only when rendering prose; preserve links, paths, code spans and PAW-STABLE codes.
    public static string ChangelogText(string text, string language)
        => PlainPunctuation(OldDisplayName().Replace(text, match => match.Groups["keep"].Success ? match.Value : Name("stable", language)));

    // Apply only to display prose, never signed models, identifiers or file contents.
    // Links, paths, filenames and code spans are literal data and must stay copyable.
    public static string PlainPunctuation(string text)
        => text.AsSpan().IndexOfAny('\u2013', '\u2014', '\u2015') < 0 ? text
            : ProseDashes().Replace(text, match => match.Groups["keep"].Success ? match.Value : "-");

    [GeneratedRegex("""(?<keep>https?://\S+|`[^`]*`|"[^"\r\n]*[\\/][^"\r\n]*"|«[^»\r\n]*[\\/][^»\r\n]*»|\S*[\\/]\S*|\b[^\s/\\:\"<>|]+\.[a-z0-9]{1,10}\b)|[\u2013-\u2015]""", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant | RegexOptions.NonBacktracking)]
    private static partial Regex ProseDashes();

    [GeneratedRegex(@"(?<keep>https?://\S+|`[^`]*`)|(?<![\w/\\.\-])(?:stable|стейбл)(?![\w\\\-]|\.\w)", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex OldDisplayName();
}
