from context import *
s=(PREV/'catalog_qa.py').read_text().replace('from release_context import *','from context import *').replace('full?10:0','full?4:0').replace('x.Select(p=>p.Id).Order().SequenceEqual','x.Where(p=>!p.Id.StartsWith("arcane-biome-textures-")).Select(p=>p.Id).Order().SequenceEqual').replace('p.Version=="0.6.0-beta.1"','p.Version=="0.6.0-beta.2"')
exec(compile(s,str(P/'catalog_check.py'),'exec'),globals())
