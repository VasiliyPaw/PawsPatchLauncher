"""Arcane city prerequisites for all 12 hard SAIs. Native TGI planning only.

Opening plans unlock the sovereign builder before filling their remaining slots.
One developed city gets the complete racial military dependency set. Native
affordability, construction, upgrade prerequisites and slot limits still apply.
"""
from pathlib import Path
import re, json, hashlib
from prepare_data import blocks, owners, prop

ROOT = Path(__file__).resolve().parent
MARK = 'PAW_AW_CITY_PLANS_R1'
RACES = ('human', 'gauri', 'drauga', 'haroun', 'undead', 'shadow')

def military_items(race):
    # Seven physical slots. Magecollege upgrades library, never an eighth slot.
    if race in ('shadow', 'undead'):
        kinds = ['quarry','woodmill','blacksmith','barracks','shrine','library','manafocus']
    else:
        kinds = ['quarry','woodmill','market','blacksmith','barracks','shrine','library']
    if race == 'human': kinds[-1] = 'magecollege'
    return [race+'_'+k for k in kinds]

def item(target, priority, later, upgrade=0):
    return (f'\n\t[Build]\n\tIDS = {target}\n'
            f'\tbuild_next_item_priority = {priority}\n\tbuild_later_item_priority = {later}\n'
            f'\tbuild_next_item_precursor_priority = {priority}\n\tbuild_later_item_precursor_priority = {later}\n'
            f'\tdestroy_mismatch_priority = 0\n\tupgrade_settlement_priority = {upgrade}\n')

def bonus(target, value):
    return (f'\n\t\t[ActorPriority]\n\t\t{{\n\t\t\tactor_IDS = {target}\n'
            f'\t\t\tvalue = 0\n\t\t\tone_time_bonus = {value}\n'
            '\t\t\tmax_recruited_per_think = 1\n\t\t}\n')

def transform(text, profile):
    if MARK in text: return text, []
    race = profile.split('_')[0]
    assert race in RACES
    changes = []; edits = []
    # Includes templates shared by the second profile. Only the quarry entry
    # changes; existing economic buildings, research and personality survive.
    for a,b,plan in blocks(text, r'^\[SettlementTemplate template\s*=\s*SettlementTemplate\]'):
        target = race+'_quarry'
        pattern = r'(?ms)^\s*\[Build\]\s*IDS\s*=\s*'+target+r'\s*\n.*?(?=^\s*\[Build\]|^\})'
        matches = list(re.finditer(pattern,plan)); assert len(matches)<=1
        if matches:
            match=matches[0]; plan=plan[:match.start()]+plan[match.end():]
        pos=plan.index('[Build]'); pos=plan.rfind('\n',0,pos)
        plan=plan[:pos]+item(target,800,800,120)+plan[pos:]
        edits.append((a,b,plan))
        changes.append(dict(field='city_plan_quarry_first',plan=prop(plan,'IDS'),target=target))
    for a,b,new in reversed(edits): text=text[:a]+new+text[b:]
    template_id='paw_aw_'+profile+'_military_city'
    edits=[]
    for key,(a,b,ego) in owners(text).items():
        if not ego.startswith('[Ego '): continue
        engines=list(blocks(ego,r'^\s*\[GoalEngine\]')); assert len(engines)==1
        ea,eb,engine=engines[0]
        # One-time means no blanket incentive to fill every city with quarries.
        # The native counter also retains admission and per-think queue checks.
        additions=bonus(race+'_quarry',1500)
        emergency='Bleeding' in ego.splitlines()[0]
        if not emergency:
            # Sovereign-city structures are separate AW actors, not upgrades of
            # the ordinary ones. Bonus-only admission lets native city capability
            # pick the appropriate variant instead of assigning an invalid plan.
            for kind in ('woodmill','blacksmith','barracks','shrine','library'):
                additions+=bonus(race+'_sovereign_'+kind,250)
            if race in ('shadow','undead'):
                additions+=bonus(race+'_sovereign_manafocus',300)
        engine=engine[:-1]+additions+engine[-1:]
        ego=ego[:ea]+engine+ego[eb:]
        if not emergency:
            ego=ego[:-1]+f'\n\t[SettlementTemplate]\n\tIDS = {template_id}\n'+ego[-1:]
        edits.append((a,b,ego))
        changes.append(dict(owner=key,field='aw_city_prerequisites',quarry_one_time_bonus=1500,
                            military_template=None if emergency else template_id))
    for a,b,new in reversed(edits): text=text[:a]+new+text[b:]
    plan=(f';; {MARK}: racial prerequisites, one military city, no demolition.\n'
          '[SettlementTemplate template = SettlementTemplate]\n{\n'
          f'\tIDS = {template_id}\n\tname = "Paw Arcane military city"\n'
          '\t[Filters]\n\t{\n\t\tinstances_max = 1\n'
          '\t\t[Item]\n\t\tstat = SETTLEMENTS_OWNED\n\t\tmin = 2\n\t\tmax = 10000\n'
          '\t\t[Item]\n\t\tstat = gold_rate\n\t\tmin = 20\n\t\tmax = 999999\n\t}\n'
          '\t[Priority]\n\tpriority = 1600\n\tinertia = 400\n')
    for target in military_items(race):
        plan += item(target,800 if target.endswith('_quarry') else 250,
                     800 if target.endswith('_quarry') else 100,120)
    text=plan+'}\n\n'+text
    return text,changes

def main():
    folder=ROOT/'data';manifest=json.loads((folder/'manifest.json').read_text())
    count=0
    for entry in manifest:
        if not entry['path'].startswith('data/SAI/'):continue
        path=folder/entry['path'];raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==entry['after'],path
        text,changes=transform(raw.decode('utf-8-sig'),path.stem)
        if changes:
            path.write_bytes(text.encode('utf-8'));entry['after']=hashlib.sha256(path.read_bytes()).hexdigest()
            entry['changes']+=changes;count+=1
        assert transform(text,path.stem)==(text,[])
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('AW_CITY_PLANS:',count,'profiles updated')

if __name__=='__main__':main()
