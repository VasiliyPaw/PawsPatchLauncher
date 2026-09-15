import unittest,json
from pathlib import Path
from GameTextValidation import validate_engine_text
from GameTextValidation import validate_format_tokens
from CollectSlavicCatalog import ROW,unquote
from PrepareEuropeanModLanguages import table
from SlavicEditorial import corrections,spacing,keyed

ROOT=Path(__file__).resolve().parents[1]

class GameTextValidationTests(unittest.TestCase):
    def test_same_english_word_uses_its_game_context(self):
        path='Localization/strings_data_K2.tgi'
        self.assertEqual(keyed(path,'swarm_2_name','Host','uk','Ведучий'),'Рій')
        self.assertEqual(keyed('Localization/strings_rtse.tgi','ui_tooltip_item_title_host','Host','uk','Ведучий'),'Ведучий')
        self.assertEqual(keyed(path,'haste_3_name','Fury','cs','Gargoyla'),'Zuřivost')
        self.assertEqual(keyed(path,'fury_name','Fury','cs','Gargoyla'),'Gargoyla')
    def test_reported_czech_quote_failure_and_backslash(self):
        for text in ('Použijte "Příkazy skupině".', 'Použijte \\Příkazy.', 'Lomítko (\\)'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):validate_engine_text('Use team commands.',text)
        validate_engine_text('Use team commands.','Použijte týmové příkazy.')

    def test_typed_engine_keys_are_included(self):
        raw='[Text language = Default]\n{\nname = "Example"\ntechnology_gained|s = "%s technology gained"\ngame_event|* = "%s discovered"\nplayers|dd = "%d/%d Players"\n}\n'
        keys={r[1] for r in ROW.findall(raw)}
        self.assertEqual(keys,{'name','technology_gained|s','game_event|*','players|dd'})
        self.assertEqual(set(table(raw.encode('utf-16'))),keys-{'name'})

    def test_formats_preserve_printf_type_and_order(self):
        validate_format_tokens('%s: %lc%.0f / %d%%','%s: %lc%.0f / %d%%')
        for value in ('%d: %lc%.0f / %s%%','%s: %lc%0.f / %d%%','%s: %.0f / %d%%'):
            with self.assertRaises(ValueError):validate_format_tokens('%s: %lc%.0f / %d%%',value)
        data=json.loads((ROOT/'game/localization/slavic-format-strings.json').read_text('utf-8'))
        self.assertEqual(len(data),362)
        for en,row in data.items():
            for value in row.values():validate_format_tokens(en,value);validate_engine_text(en,value)

    def test_reported_game_terms_and_geographic_annotations(self):
        data=json.loads((ROOT/'game/localization/text-cs-uk.json').read_text('utf-8'))['entries']
        expected={'Factions':'Фракції','Nations':'Раси','Proving Grounds':'Полігон','Metal Works':'Залізна майстерня','Impaler':'Списниця','Blacksmith':'Кузня','Score':'Рахунок','Warlock':'Чорнокнижник','Fiend':'Демон'}
        for en,uk in expected.items():self.assertEqual(data[en]['uk'],uk)
        self.assertEqual(data['%s technology gained']['uk'],'Здобуто технологію: %s')
        self.assertEqual(data['%d/%d Players']['cs'],'%d/%d hráčů')
        for value in ('Феласgreece_ prefectures. kgm','ДжарротCity in Ontario Canada','Орелstar name'):
            with self.assertRaises(ValueError):validate_engine_text('Name',value)
        for en,values in corrections().items():
            if en in data:
                self.assertEqual(data[en],{c:spacing(v,c) for c,v in values.items()},en)

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
