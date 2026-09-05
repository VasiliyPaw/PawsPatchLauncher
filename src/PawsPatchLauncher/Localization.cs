namespace PawsPatchLauncher;

public sealed class Localization
{
    private string _language;

    public Localization(string language) => _language = Normalize(language);

    public string Language => _language;
    public void SetLanguage(string language) => _language = Normalize(language);

    public string this[string key]
        => Strings.TryGetValue(key, out var value) ? (_language == "en" ? value.En : value.Ru) : key;

    private static string Normalize(string language) => language.Equals("en", StringComparison.OrdinalIgnoreCase) ? "en" : "ru";

    private static readonly Dictionary<string, (string Ru, string En)> Strings = new()
    {
        ["app.title"] = ("Paw's Patch для Kohan II", "Paw's Patch for Kohan II"),
        ["app.subtitle"] = ("Arcane Wars · центр обновлений", "Arcane Wars · update center"),
        ["nav.home"] = ("Главная", "Home"),
        ["nav.modules"] = ("Компоненты", "Components"),
        ["nav.settings"] = ("Настройки", "Settings"),
        ["status.ready"] = ("Готово к игре", "Ready to play"),
        ["status.notfound"] = ("Kohan II не найден", "Kohan II not found"),
        ["status.feedmissing"] = ("Сервер обновлений ещё не подключён", "Update server is not configured yet"),
        ["game.path"] = ("Папка игры", "Game folder"),
        ["game.version"] = ("Версия игры", "Game version"),
        ["patch.version"] = ("Версия патча", "Patch version"),
        ["modules.title"] = ("Компоненты патча", "Patch components"),
        ["modules.core"] = ("Arcane Wars + Paw's Patch", "Arcane Wars + Paw's Patch"),
        ["modules.core.desc"] = ("Основные данные, баланс, новые логова и семейства", "Core data, balance, new lairs and families"),
        ["modules.ru"] = ("Русская локализация", "Russian localization"),
        ["modules.ru.desc"] = ("Перевод оригинальной игры, Arcane Wars и новых настроек", "Translation for the base game, Arcane Wars and new settings"),
        ["modules.colors"] = ("Расширенные цвета игроков", "Extended player colors"),
        ["modules.colors.desc"] = ("51 цвет в лобби · экспериментально", "51 lobby colors · experimental"),
        ["channel.beta"] = ("Бета", "Beta"),
        ["channel.beta.tip"] = ("Тестовые функции и ранние обновления", "Test features and early updates"),
        ["modules.oos"] = ("Обработка рассинхрона", "Out-of-sync handling"),
        ["modules.oos.official"] = ("Официальная — остановить игру", "Official — stop the game"),
        ["modules.oos.continue"] = ("Продолжать игру · экспериментально", "Continue the game · experimental"),
        ["news.title"] = ("Последние изменения", "Latest changes"),
        ["news.empty"] = ("После подключения сервера здесь появится история обновлений.", "Release notes will appear here after the update server is connected."),
        ["button.update"] = ("Установить / обновить", "Install / update"),
        ["button.repair"] = ("Проверить файлы", "Verify files"),
        ["button.launch"] = ("Запустить игру", "Launch game"),
        ["button.browse"] = ("Выбрать", "Browse"),
        ["progress.checking"] = ("Проверяю обновления…", "Checking for updates…"),
        ["progress.downloading"] = ("Загрузка", "Downloading"),
        ["progress.installing"] = ("Установка и проверка файлов…", "Installing and verifying files…"),
        ["error.title"] = ("Ошибка", "Error"),
        ["dialog.selectgame"] = ("Выберите папку Kohan II", "Select the Kohan II folder"),
    };
}
