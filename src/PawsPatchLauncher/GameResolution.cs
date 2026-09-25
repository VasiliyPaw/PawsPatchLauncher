namespace PawsPatchLauncher;

public sealed record GameResolution(int Width, int Height)
{
    public static IReadOnlyList<GameResolution> WidescreenChoices { get; } = Array.AsReadOnly<GameResolution>(
    [
        new(1280, 720), new(1366, 768), new(1600, 900), new(1920, 1080),
        new(2048, 1152), new(2560, 1440), new(2880, 1620), new(3200, 1800), new(3840, 2160)
    ]);

    public string Label => $"{Width} × {Height}" + ((Width, Height) switch
    {
        (1280, 720) => " · HD",
        (1920, 1080) => " · Full HD",
        (2560, 1440) => " · QHD",
        (3840, 2160) => " · 4K",
        _ => ""
    });
    public override string ToString() => Label;
}
