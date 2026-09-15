using System.Globalization;
using System.Text.Json;

namespace PawsPatchLauncher;

public static class UiLanguages
{
    public sealed record Choice(string Code, string Label);
    public static IReadOnlyList<Choice> Choices { get; } =
    [new("en", "English"), new("ru", "Русский"), new("cs", "Čeština"), new("de", "Deutsch"), new("fr", "Français")];
    public static string Normalize(string? language) => Choices.FirstOrDefault(c => c.Code.Equals(language, StringComparison.OrdinalIgnoreCase))?.Code ?? "en";
    public static string DatePattern(string language) => language switch { "ru" or "cs" or "de" => "dd.MM.yyyy", "fr" => "dd/MM/yyyy", _ => "yyyy-MM-dd" };
    private static readonly Dictionary<string, Dictionary<string,string>> Catalogs = Load();
    private static Dictionary<string, Dictionary<string,string>> Load()
    {
        var result = new Dictionary<string, Dictionary<string,string>>(StringComparer.Ordinal);
        foreach (var code in new[] { "cs", "de", "fr" })
        {
            using var stream = typeof(UiLanguages).Assembly.GetManifestResourceStream("PawsPatchLauncher.Assets.Languages." + code + ".json");
            result[code] = stream is null ? new() : JsonSerializer.Deserialize<Dictionary<string,string>>(stream)!;
            foreach(var (key,value) in result[code].ToArray())
            {
                // Two legacy labels are composed from this authored compile-time constant.
                string Expand(string text) => text.Replace("{PatchGuide.PlayerColorCount}",PatchGuide.PlayerColorCount.ToString(CultureInfo.InvariantCulture))
                    .Replace("{PlayerColorCount}",PatchGuide.PlayerColorCount.ToString(CultureInfo.InvariantCulture));
                var expanded=Expand(key);if(expanded!=key)result[code][expanded]=Expand(value);
            }
        }
        return result;
    }
    // Only authored UI strings pass here. Never translate player names, chat,
    // signed catalogs, identifiers, paths or content supplied by other players.
    public static string Text(string language, string ru, string en) => language == "ru" ? ru : English(language, en);
    public static string Format(string language, FormattableString ru, FormattableString en)
    {
        var value=language=="ru"?ru:en;
        var format=language=="ru"?ru.Format:English(language,en.Format);
        return string.Format(CultureInfo.GetCultureInfo(Normalize(language)),format,value.GetArguments());
    }
    public static string English(string language, string en) => Catalogs.TryGetValue(language, out var catalog) && catalog.TryGetValue(en, out var value) ? value : en;
    public static string GameLanguageName(string code, string language) => code switch
    {
        "en" => Text(language, "Английский (оригинал)", "English (Original)"),
        "ru" => Text(language, "Русский", "Russian"),
        "de" => Text(language, "Немецкий", "German"),
        "fr" => Text(language, "Французский", "French"),
        "cs" => Text(language, "Чешский", "Czech"),
        "uk" => Text(language, "Украинский", "Ukrainian"),
        _ => throw new ArgumentOutOfRangeException(nameof(code))
    };
}
