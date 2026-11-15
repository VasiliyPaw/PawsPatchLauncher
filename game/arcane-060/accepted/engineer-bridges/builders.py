"""Add bridge menus and bridge-only work to existing settler unit variants."""
import re

PIONEER = re.compile(r'^(?:[a-z]+_)?(?:pioneer|pilgrim|founder|settler|nightbringer|boneweaver|engineer|caretaker|forge|crafter)$', re.I)

def end_block(text, start):
    brace=text.index('{',start);end=brace+1;depth=1
    while depth:
        if text[end]=='{':depth+=1
        elif text[end]=='}':depth-=1
        end+=1
    return end

def bridge_ability(kind, second):
    # Native target flags cannot reference arbitrary property IDs. The
    # cannot_build predicate uses this unit's explicit BuilderComponent list.
    targets=('+constructable -cannot_build +under_construction +own +friend -enemy -upgrading -settlement_center'
             if kind=='Construct' else '+constructable -cannot_build -under_construction +own -enemy -upgrading -settlement_center')
    return f'''\n [Ability Template=K2{kind}Local]
 {{
  animation1 = build1
  animation2 = {'build2' if second else 'build1'}
  [AbilityDefinition Template=K2{kind}Action]
  {{
   targets = {targets}
   [Effect Template=HealEffect]
   amount = 20
   [WhenDo Template=FXC_PlaySFX]
   audio_ids = worker_build
  }}
 }}
'''

def patch_pioneers(text):
    changes=[];edits=[]
    for unit in re.finditer(r'(?im)^\s*\[(?:Unit|Thing)\b[^\]]*\]\s*\{',text):
        end=end_block(text,unit.start());block=text[unit.start():end]
        ident=re.search(r'(?im)^\s*IDS\s*=\s*(\w+)',block)
        if not ident or not PIONEER.fullmatch(ident[1]):continue
        if '[BuilderComponent' not in block:continue
        # Only the native settler/engineer replacement that can build an
        # outpost receives bridges. City-only settlers keep their old role.
        if not re.search(r'actor_ids\s*=\s*\w*_outpost\b',block,re.I):continue
        at=block.index('[BuildActor]')
        block=block[:at]+'[BuildActor]\n actor_ids = paws_bridge_wood_site\n [BuildActor]\n actor_ids = paws_bridge_stone_site\n '+block[at:]
        perf=block.index('[PerformerComponent');tail=end_block(block,perf)
        second=bool(re.search(r'IDS\s*=\s*build2\b',block,re.I));abilities=''
        # Settlers already have an own-building construction action that also
        # accepts a bridge once the blueprint is in their build list.
        if not re.search(r'\[Ability\s+Template\s*=\s*K2ConstructLocal(?:Settlement)?\s*\]',block,re.I):abilities+=bridge_ability('Construct',second)
        if not re.search(r'\[Ability\s+Template\s*=\s*K2RepairLocal\s*\]',block,re.I):abilities+=bridge_ability('Repair',second)
        block=block[:tail-1]+abilities+block[tail-1:]
        edits.append((unit.start(),end,block));changes.append(ident[1])
    for start,end,block in reversed(edits):text=text[:start]+block+text[end:]
    return text,changes

