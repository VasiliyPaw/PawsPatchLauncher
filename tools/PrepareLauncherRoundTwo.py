"""Compose the second local review feed; this script never publishes or edits a game."""
import argparse
import base64
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text(ru, en):
    return {"ru": ru, "en": en}


def scope(package):
    if package.get("mods"):
        return package["mods"]
    name = package["id"]
    if name.startswith("pure-fixes-"):
        return ["vanilla", "immortals"]
    if name.startswith("immortals"):
        return ["immortals"]
    if name == "game-localization-en":
        return ["vanilla", "immortals", "arcane-wars"]
    if name == "vanilla-localization-ru":
        return ["vanilla", "arcane-wars"]
    if name == "startup-base":
        return ["immortals", "arcane-wars"]
    return ["arcane-wars"]


def patch_guide(mod, missing_labels):
    name = "ваниллы" if mod == "vanilla" else "Immortals"
    english = "Vanilla" if mod == "vanilla" else "Immortals"
    def entry(id, ru, en, body_ru, body_en):
        return dict(id=id, category="always", titleRu=ru, titleEn=en, bodyRu=body_ru, bodyEn=body_en)
    entries = [entry("base", f"Paw's Patch для {name}", f"Paw's Patch for {english}",
        "Набор исправлений для выбранного режима. Включается и выключается компонентом Paw's Patch. Выбор сохраняется отдельно от других модов. Баланс, войска, способности, размеры карт и правила режима сохраняются. Русский язык выбирается независимо от патча.",
        "A set of fixes for the selected mode, controlled by its Paw's Patch component. The choice is remembered separately for each mod. Balance, units, abilities, map sizes and rules are preserved. Game language is independent of the patch."),
        entry("badge-colors", "Цвета на значках рот", "Company badge colors",
        "Исправлено отображение цвета игрока на значках рот. Сохраняются существующие цвета и мягкое затенение. Изменение работает через игровые ресурсы и не зависит от версии EXE.",
        "Corrects player colors on company badges while retaining the existing colors and soft shading. This resource fix does not depend on the game executable version."),
        entry("negative-zero", "Отображение чисел", "Number display",
        "При выводе чисел «−0» отображается как «0». Меняется только форматирование, без записи в игровые расчёты. Требуется поддерживаемая версия Kohan II 1.3.72.",
        "Displays negative zero as zero. Only number formatting changes; simulation values are not written. Requires the supported Kohan II 1.3.72 executable."),
        entry("terrain", "Инициализация рельефа", "Terrain initialization",
        "При создании карты инициализируется параметр рельефа, который мог содержать случайные данные памяти. Новые размеры или типы карт не добавляются. Стандартная остановка при рассинхроне сохраняется. Исправление не означает устранения всех возможных причин рассинхрона. Требуется поддерживаемая версия 1.3.72.",
        "Initializes a terrain parameter that could otherwise contain uninitialized memory during map generation. No map sizes or types are added. Standard desync checks remain active. This does not claim to fix every possible desync cause. Requires the supported 1.3.72 executable.")]
    if mod == "immortals" and missing_labels:
        entries.append(entry("missing-labels", "Недостающие подписи", "Missing labels",
            "Добавлены отсутствующие названия способности, ячеек осадных рот и песчаной бури. Исправлены только строки интерфейса; характеристики и действие способности сохраняются.",
            "Adds missing labels for an ability, siege-company slots and the sandstorm sound. Only interface strings are changed; statistics and ability behavior are preserved."))
    return dict(schemaVersion=1, version="0.1.0", entries=entries)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--package-list", type=Path, action="append", required=True)
    parser.add_argument("--mod-games", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    replacements = {}
    for file in args.package_list:
        for package in read(file):
            replacements[package["id"]] = package
    for package in replacements.values():
        path = Path(package["urls"][0])
        assert path.is_file() and path.stat().st_size == package["size"], path
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == package["sha256"].upper(), path
    for channel in ("stable", "beta"):
        envelope = read(args.base / (channel + ".json"))
        feed = json.loads(base64.b64decode(envelope["payload"]))
        existing = {p["id"] for p in feed["packages"]}
        feed["packages"] = [copy.deepcopy(replacements.get(p["id"], p)) for p in feed["packages"]]
        feed["packages"].extend(copy.deepcopy(p) for id, p in replacements.items() if id not in existing)
        for package in feed["packages"]:
            package["mods"] = scope(package)
        feed["modGames"] = read(args.mod_games)
        for guide in feed["modGuides"]:
            if guide["id"] not in ("vanilla", "immortals"):
                continue
            guide["patchGuide"] = patch_guide(guide["id"], "immortals-text-fixes" in replacements)
            if guide["id"] == "vanilla":
                guide["sections"][0]["body"] = text(
                    "При применении настроек восстанавливаются оригинальные правила игры и удаляются изменения других модов. Сохранения и выбранный язык остаются. Компонент Paw's Patch добавляет отдельный набор исправлений; его можно выключить для полностью оригинального режима.",
                    "Applying settings restores the original game rules and removes changes from other mods. Saves and the chosen language are retained. The optional Paw's Patch component adds a separate set of fixes; disable it for the original mode.")
        stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        feed["publishedAt"] = stamp
        notes = [dict(category="launcher", version="0.6.4-local.3", publishedAt="2026-09-10",
            title=text("Исправления русификации и интерфейса · тестовая сборка", "Localization and interface fixes · test build"),
            body=text("• Исправлены русские строки в ванилле и Immortals.\n• Добавлен выключаемый Paw's Patch с чистыми исправлениями для обоих режимов.\n• Обновления и непрочитанная история относятся к своему моду.\n• Надпись администратора находится рядом с @юзернеймом.\n• Повторное открытие админ-панели возвращает на предыдущую вкладку.\n• Панель установки сохраняет высоту при смене этапов.\n\nЛокальная тестовая сборка. Не опубликована.",
                "• Fixed Russian text in Vanilla and Immortals.\n• Optional Paw's Patch fixes are available for both modes.\n• Updates and unread patch history belong to their own mod.\n• Administrator badge is next to @username.\n• Pressing Admin again returns to the previous page.\n• Installation progress retains its height between stages.\n\nLocal test build. Not published."))]
        for mod in ("vanilla", "immortals"):
            notes.append(dict(category="patch", mods=[mod], version="0.1.0", publishedAt="2026-09-10",
                title=text("Русский язык и чистые исправления", "Russian language and focused fixes"),
                body=text("Исправлено чтение русских строк. В компоненте Paw's Patch доступны исправления цветов значков рот, отображения «−0» и инициализации рельефа. Для исправлений движка требуется поддерживаемая 1.3.72; файловые исправления остаются доступны отдельно.",
                    "Fixed Russian string loading. Paw's Patch offers company-badge colors, negative-zero display and terrain initialization fixes. Engine fixes require the supported 1.3.72 executable; file fixes remain separately available.")))
        feed["changelog"] = notes + feed["changelog"]
        write(args.out / (channel + ".payload.json"), feed)
        if channel == "stable":
            write(Path(__file__).resolve().parents[1] / "src/PawsPatchLauncher/Assets/mod-guides.json", feed["modGuides"])
    write(args.out / "preparation.json", dict(published=False, replacements=list(replacements), modGames=read(args.mod_games)))
    print("Prepared scoped local feeds and guides; nothing published.")


if __name__ == "__main__":
    main()
