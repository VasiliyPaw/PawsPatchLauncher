"""Dependency, phase, capacity and preservation checks for generated city plans."""
from pathlib import Path
import re, unittest
from prepare_city_plans import transform, military_items, ROOT, RACES
from prepare_data import blocks, owners, prop

class CityPlansTests(unittest.TestCase):
    def test_all_races_have_seven_distinct_physical_slots(self):
        for race in RACES:
            items=military_items(race)
            self.assertEqual(len(items),7);self.assertEqual(len(set(items)),7)
            self.assertIn(race+'_quarry',items)
            self.assertFalse(race+'_library' in items and race+'_magecollege' in items)
    def test_evil_magic_and_human_advanced_unlocks(self):
        for race in ('undead','shadow'):
            self.assertIn(race+'_manafocus',military_items(race))
            self.assertIn(race+'_barracks',military_items(race))
            self.assertIn(race+'_library',military_items(race))
        self.assertIn('human_magecollege',military_items('human'))
    def test_all_twelve_profiles_resolve_shared_plans(self):
        files=sorted((ROOT/'data/data/SAI').glob('*hard*.tgi'));self.assertEqual(len(files),12)
        definitions={}
        for path in files:
            text=path.read_text('utf-8-sig')
            self.assertEqual(transform(text,path.stem),(text,[]))
            for _,_,plan in blocks(text,r'^\[SettlementTemplate template\s*=\s*SettlementTemplate\]'):
                key=prop(plan,'IDS');self.assertNotIn(key,definitions);definitions[key]=plan
        for path in files:
            race=path.stem.split('_')[0];text=path.read_text('utf-8-sig')
            for target in re.findall(r'\[SettlementTemplate\]\s*IDS\s*=\s*(\w+)',text):
                self.assertIn(target,definitions)
                items=re.findall(r'\[Build\]\s*IDS\s*=\s*(\w+)',definitions[target])
                self.assertEqual(items[0],race+'_quarry')
                self.assertEqual(items.count(race+'_quarry'),1)
    def test_new_plan_is_gated_and_cannot_demolish(self):
        for path in (ROOT/'data/data/SAI').glob('*hard*.tgi'):
            text=path.read_text('utf-8-sig');plan=next(blocks(text,r'^\[SettlementTemplate template\s*=\s*SettlementTemplate\]'))[2]
            self.assertEqual(prop(plan,'instances_max'),'1')
            self.assertRegex(plan,r'stat = SETTLEMENTS_OWNED\s+min = 2')
            self.assertRegex(plan,r'stat = gold_rate\s+min = 20')
            self.assertEqual(set(re.findall(r'destroy_mismatch_priority\s*=\s*(\S+)',plan)),{'0'})
    def test_emergency_avoids_development_plan(self):
        for path in (ROOT/'data/data/SAI').glob('*hard*.tgi'):
            for key,(_,_,ego) in owners(path.read_text('utf-8-sig')).items():
                if not ego.startswith('[Ego '):continue
                if 'Bleeding' in ego.splitlines()[0]:
                    self.assertNotIn('paw_aw_',ego)
                else:self.assertIn('paw_aw_'+path.stem+'_military_city',ego)
                self.assertRegex(ego,r'actor_IDS = '+path.stem.split('_')[0]+r'_quarry\s+value = 0\s+one_time_bonus = 1500')
    def test_transform_preserves_existing_recruitment_and_filters(self):
        sample='''[SettlementTemplate template = SettlementTemplate]
{
 IDS = opening
 [Build]
 IDS = shadow_woodmill
 build_next_item_priority = 400
}
[Ego template = DefaultK2EgoHard]
{
 IDS = opening_ego
 [Filters]
 {
  [Item]
  stat = gold_rate
  min = 20
  max = 999999
 }
 [GoalEngine]
 {
  [Recruiting]
  {
   [SpecificRecruitRequest]
   {
    property_ids = company_sovereign_shadow
    base_priority = 8000
   }
  }
 }
 [SettlementTemplate]
 IDS = opening
}
'''
        result,_=transform(sample,'shadow_hard')
        for header in ('Filters','Recruiting'):
            before=next(blocks(sample,r'^\s*\['+header+r'\]'))[2]
            ego=owners(result)['opening_ego'][2]
            self.assertIn(before,ego)
        self.assertEqual(transform(result,'shadow_hard'),(result,[]))

if __name__=='__main__':unittest.main(verbosity=2)
