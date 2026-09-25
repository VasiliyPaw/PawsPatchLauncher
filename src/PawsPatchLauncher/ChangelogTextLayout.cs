namespace PawsPatchLauncher;

public enum ChangelogTextKind { Paragraph, Heading, Bullet }

public sealed record ChangelogTextLine(ChangelogTextKind Kind, string Text);

public static class ChangelogTextLayout
{
    public static IReadOnlyList<ChangelogTextLine> Parse(string? value)
    {
        var result = new List<ChangelogTextLine>();
        var paragraph = new List<string>();
        void FlushParagraph()
        {
            if (paragraph.Count == 0) return;
            result.Add(new(ChangelogTextKind.Paragraph, string.Join("\n", paragraph)));
            paragraph.Clear();
        }
        foreach (var raw in (value ?? "").Replace("\r\n", "\n").Replace('\r', '\n').Split('\n'))
        {
            var line = raw.Trim();
            if (line.Length == 0) { FlushParagraph(); continue; }
            var heading = line.TrimStart('#').TrimStart();
            if (line.StartsWith('#') && heading.Length > 0)
            {
                FlushParagraph(); result.Add(new(ChangelogTextKind.Heading, heading)); continue;
            }
            if (line.StartsWith("- ", StringComparison.Ordinal) || line.StartsWith("• ", StringComparison.Ordinal))
            {
                FlushParagraph(); result.Add(new(ChangelogTextKind.Bullet, line[2..].Trim())); continue;
            }
            paragraph.Add(line);
        }
        FlushParagraph();
        return result;
    }

    public static string Preview(string value, int maximumLength = 300)
    {
        var paragraphs = value.Replace("\r\n", "\n").Split("\n\n", StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        var preview = string.Join("\n\n", paragraphs.Take(2));
        if (preview.Length <= maximumLength) return preview;
        return preview[..maximumLength].TrimEnd() + "…";
    }
}
