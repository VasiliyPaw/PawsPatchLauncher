import unittest,json
from pathlib import Path
from GameTextValidation import validate_engine_text

ROOT=Path(__file__).resolve().parents[1]

class GameTextValidationTests(unittest.TestCase):
    def test_reported_startup_failure(self):
        for source in ('Delete','Add','Remove','DELETE','RENAME','KICK','BAN'):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):validate_engine_text(source,'& Вилучити')

    def test_inline_entities_are_not_menu_mnemonics(self):
        validate_engine_text('A &amp; B','А &amp; Б')
        for value in ('А & Б','А &amp Б','А &lt; Б','А\x00Б'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):validate_engine_text('A &amp; B',value)

    def test_all_current_game_and_mod_translations(self):
        checks=0
        for name in ('text-cs-uk.json','mod-cs-uk.json','mod-de-fr.json'):
            entries=json.loads((ROOT/'game/localization'/name).read_text('utf-8-sig'))['entries']
            for key,row in entries.items():
                source=row.get('en',key)
                for code in ('cs','uk','de','fr'):
                    if code in row:
                        validate_engine_text(source,row[code]);checks+=1
        print('GAME_TRANSLATION_ESCAPE_PASS',checks)

if __name__=='__main__':unittest.main()
