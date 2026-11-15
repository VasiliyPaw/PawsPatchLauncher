"""Bake local stock EE2 candidates to game-sized, saved bridge actor variants."""
from pathlib import Path
import io,sys,time,math,json,hashlib
import numpy as np

def prepare(source:Path,target:Path):
 sys.path.insert(0,str(source/'deps'));time.clock=time.perf_counter
 from pyffi.formats.nif import NifFormat as N
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge-selection-boxes'))
 from selection_box import add_selection_box
 stock_box=Path(__file__).with_name('fixtures').joinpath('selection-box.nif').read_bytes()
 folder=target/'Paws/Bridges';folder.mkdir(parents=True,exist_ok=True)
 manifest={}
 for material,model,width,zscale in [('wood','bld_bridge1_span',102.47924,.06),('stone','bld_bridge5_span',75.,.08)]:
  source_bytes=(source/'candidate'/model/'bridge.nif').read_bytes()
  raw=N.Data();raw.read(io.BytesIO(source_bytes))
  sources=[b for b in raw.blocks if isinstance(b,N.NiTriBasedGeom)]
  texture=f'PawsBridge{material.title()}.tga'
  old_texture=next((source/'candidate'/model).glob('*.tga'))
  (folder/texture).write_bytes(old_texture.read_bytes())
  for count in range(5,33):
   length=(count-1)*2;segments=math.ceil(length/8)
   for axis in ('x','y'):
    root=N.NiNode();root.name=b'Scene Root';root.flags=16
    base=N.NiNode();base.name=b'BASE';base.flags=16;root.add_child(base)
    finished=N.NiNode();finished.name=b'Final';finished.flags=16;base.add_child(finished)
    for index in range(segments):
     # PyFFI's dynamic classes are not compatible with Python deepcopy. A fresh
     # read provides independent linked data and preserves each mesh's metadata.
     module=N.Data();module.read(io.BytesIO(source_bytes))
     for mesh in [b for b in module.blocks if isinstance(b,N.NiTriBasedGeom)]:
      b=mesh;matrix=np.array(mesh.get_transform().as_list())
      vertices=np.array([[v.x,v.y,v.z,1.] for v in mesh.data.vertices])@matrix
      linear=np.diag([6/width,length/(segments*100),zscale])
      vertices=vertices[:,:3]@linear
      vertices[:,1]+=(index-(segments-1)/2)*length/segments
      rotation=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]]) if axis=='x' else np.eye(3)
      vertices=vertices@rotation
      for v,p in zip(b.data.vertices,vertices):v.x,v.y,v.z=map(float,p)
      if b.data.has_normals:
       transform=np.linalg.inv(matrix[:3,:3]@linear@rotation).T
       normals=np.array([[v.x,v.y,v.z] for v in mesh.data.normals])@transform
       normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
       for v,p in zip(b.data.normals,normals):v.x,v.y,v.z=map(float,p)
      b.set_transform(N.Matrix44())
      b.data.update_center_radius()
      for p in b.properties:
       if isinstance(p,N.NiTexturingProperty):p.base_texture.source.file_name=texture.encode()
       # EE2 exported binary-cutout textures with alpha blending enabled.
       # Put solid bridge geometry in the opaque pass: otherwise it is drawn
       # after Kohan's transparent water and underwater supports show through.
       if isinstance(p,N.NiAlphaProperty):p.flags=int(p.flags)&~1
      finished.add_child(b)
    output=N.Data(version=0x0A010000,user_version=0);output.roots=[root]
    selection=add_selection_box(N,output,length,axis,.1 if material=='wood' else 0.,stock_box)
    name=f'{material}_{axis}_{count:02}.nif';path=folder/name
    with path.open('wb') as f:output.write(f)
    checked=N.Data()
    with path.open('rb') as f:checked.read(f)
    assert len([b for b in checked.blocks if isinstance(b,N.NiTriBasedGeom) and bytes(b.name)!=b'SelectionBox'])==len(sources)*segments
    manifest[name]=dict(length=length,width=6,segments=segments,selectionBox=selection,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 (target/'bridge-model-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 return manifest

BRIDGE_BALANCE = {
 'human': ((2000,100,'wood',3),(5000,200,'stone',10)),
 'haroun': ((1600,80,'wood',3),(4000,160,'wood',7)),
 'shadow': ((2400,100,'stone',5),(6000,200,'stone',10)),
 'undead': ((1800,80,'wood',3),(4500,160,'stone',10)),
 'gauri': ((3000,125,'stone',5),(7500,250,'stone',10)),
 'drauga': ((2000,80,'wood',3),(5000,160,'stone',10)),
}

def bridge_balance(style, material):
 return BRIDGE_BALANCE.get(style.lower(),((1000,75,'wood',10),(2000,125,'stone',10)))[material=='stone']

def definitions(language='en', styles=None):
 labels={
  'en':('Wooden bridge','Stone bridge','A crossing between solid banks.','A durable crossing between solid banks.'),
  'ru':('Деревянный мост','Каменный мост','Переправа между твёрдыми берегами.','Прочная переправа между твёрдыми берегами.'),
  'de':('Holzbrücke','Steinbrücke','Brücke zwischen festen Ufern.','Stabile Brücke zwischen festen Ufern.'),
  'fr':('Pont en bois','Pont en pierre','Passage entre deux rives fermes.','Passage solide entre deux rives fermes.'),
  'cs':('Dřevěný most','Kamenný most','Přechod mezi pevnými břehy.','Odolný přechod mezi pevnými břehy.'),
  'uk':('Дерев’яний міст','Кам’яний міст','Переправа між твердими берегами.','Міцна переправа між твердими берегами.')
 }.get(language)
 if labels is None:raise ValueError(language)
 nodes=['''[Template PawsBridge Template=K2Structure]
{
 [Flags]
 {
  blocking = false
  ethereal = true
  flying = false
  corpse_blocking = false
  flatten_terrain = false
  invulnerable = false
  targetable = true
  ownable = true
  radar = false
  axis_locked = false
  tile_locked = false
  random_orientation = false
 }
 [Placement]
 placement_category = building
 placement_group_IDS = group_special
 [Size]
 blocking_shape = RECT
 soft_shape = RECT
 target_shape = RECT
 [View]
 {
  icon = /UI/Game/StructureButtons/OutpostIcon.png
  shadow_type = NONE
  selected_vfx = selected_square_vfx
  focused_vfx = focused_square_vfx
  [AspectNormal]
  skin = null
  disable_animations = true
 }
 [BodyComponent]
 health = 1000
 defense = 0
 [PropertiesComponent]
 [DetectionComponent]
 detection_range = 0
 remote_detection_range = 0
 [ConstructionComponent]
 can_sell = false
 can_raze = true
 [EconomyComponent]
 supply_required = false
 [WhenEnter Template=FXC_CreateVFX]
 actor_state = construction
 VFX_IDS = paws_bridge_construction_raise_vfx
 location = BASE
}''']
 # Stock Haroun outposts use the normal swaying/raising modifier together
 # with the living-wood construction effect and its completion counterpart.
 # Give bridges a separate base so those effects replace, rather than stack
 # with, the ordinary smoke and rigid bridge modifier.
 nodes.append(nodes[0].replace('Template PawsBridge ', 'Template PawsBridgeHaroun ')
  .replace('paws_bridge_construction_raise_vfx','normal_construction_raise_vfx')
  .replace(' [PropertiesComponent]\n',' [PropertiesComponent]\n {\n  [Property]\n  property_IDS = haroun_autoheal\n }\n')
  .replace(' [WhenEnter Template=FXC_CreateVFX]\n actor_state = active_construction\n VFX_IDS = construction_smoke_vfx\n location = BASE\n',''))
 nodes.append(nodes[0].replace('Template PawsBridge ', 'Template PawsBridgeUndead ').replace('paws_bridge_construction_raise_vfx','undead_construction_raise_vfx'))
 shadow=nodes[0].replace('Template PawsBridge ', 'Template PawsBridgeShadow ')
 shadow=shadow.replace(' [WhenEnter Template=FXC_CreateVFX]\n actor_state = construction\n VFX_IDS = paws_bridge_construction_raise_vfx\n location = BASE\n','')
 shadow=shadow[:-1]+''' [WhenEnter Template=FXC_CreateVFX]
 actor_state = construction
 VFX_IDS = paws_bridge_shadow_fade
 [WhenLeave Template=FXC_StopVFX]
 actor_state = construction
 VFX_IDS = paws_bridge_shadow_fade
 [WhenEnter Template=FXC_CreateVFX]
 actor_state = construction
 VFX_IDS = paws_bridge_shadow_pulse
 [WhenLeave Template=FXC_StopVFX]
 actor_state = construction
 VFX_IDS = paws_bridge_shadow_pulse
}'''
 nodes.append(shadow)
 nodes.append('''[Thing Template=PawsBridge]
{
 IDS = paws_bridge_site
 name = "'''+('Мост' if language=='ru' else labels[1])+'''"
 editor_name = "Paws bridge menu entry"
 description = "'''+('Автоматическая переправа между твёрдыми берегами.' if language=='ru' else 'Automatic crossing between solid banks.')+'''"
 [View]
 resource_prefix = /Paws/Bridges/stone_x_13
}''')
 for style,manifest in [('',{}),*((styles or {}).items())]:
  bridge_template={'haroun':'PawsBridgeHaroun','undead':'PawsBridgeUndead','shadow':'PawsBridgeShadow'}.get(style.lower(),'PawsBridge')
  style_prefix=(style.lower()+'_') if style else ''
  model_prefix='/Paws/Bridges'+('/'+style.title() if style else '')
  for material,resource,label,description in [('wood','wood',labels[0],labels[2]),('stone','stone',labels[1],labels[3])]:
   hp,gold,resource,upkeep=bridge_balance(style,material)
   nodes.append(f'''[Thing Template={bridge_template}]
 {{
  IDS = paws_bridge_{style_prefix}{material}_site
  name = "{label}"
  editor_name = "Paws bridge {material} menu entry"
  description = "{description}"
  [View]
  {{
   icon = /UI/Game/StructureButtons/PawsBridge{material.title()}Icon.png
   resource_prefix = {model_prefix}/{material}_x_13
   [AspectNormal]
   visual_radius_estimate = {max(24, manifest.get(material+'_x_13.nif',{}).get('visualRadiusEstimate',24))}
  }}
  [BodyComponent]
  health = {hp}
  [EconomyComponent]
  {{
   [Cost]
   gold = {gold}
   [Upkeep]
   {resource} = {upkeep}
  }}
 }}''')
   for count in range(5,33):
    length=(count-1)*2
    for axis in ('x','y'):
     growth=(f'''\n  [WhenEnter Template=FXC_CreateVFX]
  actor_state = construction
  VFX_IDS = paws_bridge_haroun_growth_{axis}_{count:02}
  location = BASE
  [WhenLeave Template=FXC_StopVFX]
  actor_state = construction
  VFX_IDS = paws_bridge_haroun_growth_{axis}_{count:02}
  [WhenLeave Template=FXC_CreateVFX]
  actor_state = construction
  VFX_IDS = paws_bridge_haroun_finish_{axis}_{count:02}
  location = BASE
''' if style.lower()=='haroun' else racial_construction_events(style.lower() or 'human',axis,count))
     nodes.append(f'''[Thing Template={bridge_template}]
 {{
  IDS = paws_bridge_{style_prefix}{material}_{axis}_{count:02}
  name = "{label}"
  editor_name = "Paws bridge {material} {axis} {count:02}"
  description = "{description}"
  [BodyComponent]
  health = {hp}
  [Size]
  rect_width = {length if axis=='x' else 6}
  rect_height = {6 if axis=='x' else length}
  target_rect_width = {length if axis=='x' else 6}
  target_rect_height = {6 if axis=='x' else length}
  [View]
  {{
   icon = /UI/Game/StructureButtons/PawsBridge{material.title()}Icon.png
   resource_prefix = {model_prefix}/{material}_{axis}_{count:02}
   selected_vfx = selected_square_vfx
   focused_vfx = focused_square_vfx
   {''.join(f'''[WhenConstructed Template=FXC_CreateVFX]
   VFX_IDS = paws_bridge_ground_{style.lower() if style else 'human'}
   translation = {end if axis=='x' else 0}, {end if axis=='y' else 0}, 0
   ''' for end in (-length/2, length/2))}
   [AspectNormal]
   visual_radius_estimate = {max(length, manifest.get(f'{material}_{axis}_{count:02}.nif',{}).get('visualRadiusEstimate',length))}
  }}
  {growth}
  [EconomyComponent]
  {{
   [Cost]
   gold = {gold}
   [Upkeep]
   {resource} = {upkeep}
  }}
 }}''')
 return '\n\n'.join(nodes)+'\n'

def racial_construction_events(race,axis,count):
 def create(event,state,fx):
  anchor="  at = SELF\n  attached = true\n" if race in ["human","gauri","drauga"] and ("_scaffold_" in fx or "_finish_" in fx) else "  location = BASE\n"
  return f'''\n  [{event} Template=FXC_CreateVFX]
  actor_state = {state}
  VFX_IDS = {fx}
{anchor}'''
 def stop(state,fx):return f'''\n  [WhenLeave Template=FXC_StopVFX]
  actor_state = {state}
  VFX_IDS = {fx}
'''
 suffix=f'{axis}_{count:02}'
 if race=='shadow':
  fx='paws_bridge_build_shadow_work_'+suffix
  return create('WhenEnter','active_construction',fx)+stop('active_construction',fx)
 if race=='undead':
  growth='paws_bridge_build_undead_growth_'+suffix;work='paws_bridge_build_undead_work_'+suffix;finish='paws_bridge_build_undead_finish_'+suffix
 else:
  growth=f'paws_bridge_build_{race}_scaffold_'+suffix;finish=f'paws_bridge_build_{race}_finish_'+suffix;work='paws_bridge_build_smoke_'+suffix
 return create('WhenEnter','construction',growth)+stop('construction',growth)+create('WhenLeave','construction',finish)+create('WhenEnter','active_construction',work)+stop('active_construction',work)

def racial_construction_effects():
 out=[]
 for race in ['human','gauri','drauga','undead','shadow']:
  kinds=['scaffold','finish'] if race in ['human','gauri','drauga'] else ['growth','work','finish'] if race=='undead' else ['work']
  for kind in kinds:
   for count in range(5,33):
    for axis in ['x','y']:
     out.append(f'''\n[VFX Template={'K2VFXModelTemporary' if kind=='finish' else 'K2VFXModelPermanent'}]
{{
 IDS = paws_bridge_build_{race}_{kind}_{axis}_{count:02}
 name = "Bridge {race} {kind}"
 model = /Paws/Bridges/RacialBuild/{race}/{kind}_{axis}_{count:02}.nif
 attached_scale = 0
 gyroscope = false
 {'duration = 7' if race=='undead' and kind=='finish' else ''}
}}
''')
 out.append('''
[VFX Template=VFXAlphaModifier]
{
 IDS = paws_bridge_shadow_fade
 name = "Shadow bridge construction opacity"
 alpha = .55
}
[VFX Template=VFXTintModifier]
{
 IDS = paws_bridge_shadow_pulse
 name = "Shadow bridge construction pulse"
 color = 0.3, 0.4, 0.6
 enhance_duration = 3
 fade_duration = 1.5
 tint_max = .75
 repeating = true
}
''')
 return ''.join(out)

def construction_effect():
 return '''\n[VFX Template=VFXConstructionRaiseModifier]
{
 IDS = paws_bridge_construction_raise_vfx
 name = "Bridge construction"
 apply_shaking = true
 shaking_frequency = 3
 shaking_strength = 0.05
 shaking_falloff = 2
 apply_swaying = true
 swaying_frequency = 2
 swaying_maxangle = 15
 swaying_falloff = 2
 attached_scale = 0
}
'''+''.join(f'''\n[VFX Template={'K2VFXModelPermanent' if kind=='growth' else 'K2VFXModelTemporary'}]
{{
 IDS = paws_bridge_haroun_{kind}_{axis}_{count:02}
 name = "Haroun bridge {kind}"
 model = /Paws/Bridges/HarounEffects/{kind}_{axis}_{count:02}.nif
 attached_scale = 0
 gyroscope = false
}}
''' for kind in ('growth','finish') for count in range(5,33) for axis in ('x','y'))+''.join(f'''
[VFX Template=K2VFXModelPermanent]
{{
 IDS = paws_bridge_build_smoke_{axis}_{count:02}
 name = "Bridge construction smoke"
 model = /Paws/Bridges/BuildEffects/smoke_{axis}_{count:02}.nif
 attached_scale = 0
 gyroscope = false
}}
''' for count in range(5,33) for axis in ('x','y'))+racial_construction_effects()+''.join(f'''
[VFX Template=VFXProjectedTexture]
{{
 IDS = paws_bridge_ground_{race}
 name = "Bridge ground covering"
 texture = /Paws/Bridges/Aprons/{race}-apron.tga
 attached_scale = 0
 attached_shape = false
 texture_size = 10
 respect_lighting = true
 random_orientation = false
 decal_fade_time = 3, 1
}}
''' for race in ('human','haroun','gauri','drauga','undead','shadow'))
def selection_effects():
 # Contours live in each bridge model; no separately attached VFX is needed.
 return ''
