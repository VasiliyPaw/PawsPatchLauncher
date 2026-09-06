using System.Net;
using System.Net.Http;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Text.Json;

namespace PawsPatchLauncher;

public enum ErrorAction { CheckUpdates, Storage, Settings, Diagnostics }
public sealed record FriendlyError(string Code, string TitleRu, string TitleEn, string BodyRu, string BodyEn, ErrorAction Action)
{
    public string Title(string language) => language == "ru" ? TitleRu : TitleEn;
    public string Body(string language) => language == "ru" ? BodyRu : BodyEn;
    public string ActionText(string language) => (Action, language == "ru") switch
    {
        (ErrorAction.CheckUpdates, true) => "Проверить обновления",
        (ErrorAction.Storage, true) => "Управление местом",
        (ErrorAction.Settings, true) => "Открыть настройки",
        (ErrorAction.Diagnostics, true) => "Создать диагностику",
        (ErrorAction.CheckUpdates, _) => "Check for updates",
        (ErrorAction.Storage, _) => "Manage storage",
        (ErrorAction.Settings, _) => "Open settings",
        _ => "Create diagnostics"
    };
}

public static class FriendlyErrors
{
    public static FriendlyError Describe(Exception exception)
    {
        var all = new List<Exception>();
        void Visit(Exception error)
        {
            all.Add(error);
            if (error is AggregateException aggregate) foreach (var inner in aggregate.InnerExceptions) Visit(inner);
            else if (error.InnerException is not null) Visit(error.InnerException);
        }
        Visit(exception);
        if (all.Any(x => x is CryptographicException or AuthenticationException))
            return new("security", "Проверка безопасности не пройдена", "Security verification failed",
                "Не удалось подтвердить подлинность обновления или защищённое соединение. Установка остановлена. Проверьте дату и время Windows; если ошибка повторится, отправьте диагностику. Проверки безопасности отключать не нужно.",
                "The update signature or secure connection could not be verified. Installation stopped. Check the Windows date and time; if this persists, send diagnostics. Do not disable security checks.", ErrorAction.Diagnostics);
        if (all.Any(x => x is IOException && (x.HResult & 0xffff) is 112 or 39))
            return new("disk-full", "Недостаточно места", "Not enough disk space",
                "На диске закончилось место. В настройках можно проверить размер кеша и безопасно очистить устаревшие данные. После освобождения места повторите установку.",
                "The disk is full. Settings shows cache sizes and can safely clean old data. Free some space, then retry installation.", ErrorAction.Storage);
        if (all.OfType<HttpRequestException>().Any(x => x.StatusCode == HttpStatusCode.NotFound))
            return new("http-404", "Файл обновления не найден", "Update file not found",
                "Сервер не нашёл запрошенный файл (404). Обновите список версий и попробуйте снова. Если ошибка повторится, автору нужно исправить публикацию; переустановка игры не требуется.",
                "The server could not find the requested file (404). Refresh the release list and try again. If this persists, the publisher must fix the release; reinstalling the game is not required.", ErrorAction.CheckUpdates);
        if (all.OfType<HttpRequestException>().Any(x => x.StatusCode is HttpStatusCode.Forbidden or HttpStatusCode.Unauthorized or HttpStatusCode.TooManyRequests))
            return new("http-access", "Сервер ограничил доступ", "Server access is limited",
                "Сервер отклонил запрос или временно ограничил частоту скачиваний. Подождите несколько минут и повторите проверку. Вводить пароль Steam или GitHub в лаунчер не нужно.",
                "The server rejected the request or temporarily limited downloads. Wait a few minutes and check again. Do not enter a Steam or GitHub password in the launcher.", ErrorAction.CheckUpdates);
        if (all.Any(x => x is OperationCanceledException or TimeoutException))
            return new("timeout", "Сервер не ответил вовремя", "The server timed out",
                "Проверьте подключение к интернету и повторите проверку. Уже установленные игровые файлы эта ошибка не меняет.",
                "Check your internet connection and try again. This error does not change installed game files.", ErrorAction.CheckUpdates);
        if (all.Any(x => x is UnauthorizedAccessException))
            return new("access", "Нет доступа к папке", "Folder access denied",
                "Windows не разрешила прочитать или изменить файл. Проверьте выбранную папку игры и права доступа. Не отключайте защиту Windows и не удаляйте файлы вручную.",
                "Windows did not allow a file to be read or changed. Check the selected game folder and its permissions. Do not disable Windows protection or delete files manually.", ErrorAction.Settings);
        if (all.Any(x => x is IOException && (x.HResult & 0xffff) is 32 or 33))
            return new("locked", "Файл используется другой программой", "File is in use",
                "Закройте Kohan II и дождитесь завершения других установок или проверок файлов. Затем повторите действие. Лаунчер не будет принудительно закрывать игру.",
                "Close Kohan II and wait for other installations or file checks to finish, then retry. The launcher will not force-close the game.", ErrorAction.Settings);
        if (all.Any(x => x is HttpRequestException))
            return new("network", "Не удалось связаться с сервером", "Could not reach the server",
                "Возможно, соединение пропало или сервер временно недоступен. Проверьте интернет и повторите проверку немного позже.",
                "The connection may have dropped or the server may be temporarily unavailable. Check your internet connection and try again later.", ErrorAction.CheckUpdates);
        if (all.Any(x => x is InvalidDataException && (x.Message.Contains("SHA-256", StringComparison.OrdinalIgnoreCase) || x.Message.Contains("hash mismatch", StringComparison.OrdinalIgnoreCase))))
            return new("hash", "Файл не прошёл проверку", "File verification failed",
                "Скачанные данные не совпали с опубликованной контрольной суммой и не будут установлены. Проверьте обновления и повторите установку. Если ошибка повторяется, отправьте диагностику автору.",
                "Downloaded data did not match its published checksum and will not be installed. Check for updates and retry installation. If this persists, send diagnostics to the author.", ErrorAction.CheckUpdates);
        if (all.Any(x => x is FormatException or JsonException || x is InvalidDataException && x.Message.Contains("report", StringComparison.OrdinalIgnoreCase)))
            return new("format", "Не удалось прочитать данные", "Could not read the data",
                "Код настроек, отчёт или файл настроек имеет неподдерживаемый либо повреждённый формат. Для сравнения попросите друга заново сохранить отчёт в актуальном лаунчере. Исходные данные не изменены.",
                "The configuration code, report or settings file is unsupported or damaged. For comparison, ask your friend to export a new report with the current launcher. The source data was not changed.", ErrorAction.Settings);
        return new("operation", "Действие не завершено", "The operation did not finish",
            "Лаунчер остановил действие из-за ошибки. Подробности можно скопировать или приложить архив диагностики. Не удаляйте файлы игры вручную.",
            "The launcher stopped this operation because of an error. Copy the details or attach a diagnostic archive. Do not delete game files manually.", ErrorAction.Diagnostics);
    }
}
