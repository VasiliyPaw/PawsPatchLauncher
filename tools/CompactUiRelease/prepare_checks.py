from context import *
def main():
 # Reuse the previously validated public-client selection matrix, changing
 # only the expected terrain grouping and compact UI payload assertions.
 s=(WS/'work/ui-fullres-release-20261117/catalog_check.py').read_text()
 s=s.replace('Check(x.Select(p=>p.Id).Order().SequenceEqual(y.Select(p=>p.Id).Order()),"package selection changed");','''var expectedIds=x.Select(p=>p.Id).ToList();if(full&&mod==GameMod.ArcaneWars){expectedIds.RemoveAll(p=>p.StartsWith("arcane-biome-textures-"));expectedIds.Add("arcane-biome-textures");}Check(expectedIds.Order().SequenceEqual(y.Select(p=>p.Id).Order()),"package selection changed");''')
 s=s.replace('var old=x.Single(q=>q.Id==p.Id);if(channel=="beta"&&files.ContainsKey(p.Id))Check(p.Version==versions[p.Id],"version");else Check(JsonSerializer.Serialize(p)==JsonSerializer.Serialize(old),"unrelated package changed "+p.Id);','''if(channel=="beta"&&files.ContainsKey(p.Id))Check(p.Version==versions[p.Id],"version");else Check(JsonSerializer.Serialize(p)==JsonSerializer.Serialize(x.Single(q=>q.Id==p.Id)),"unrelated package changed "+p.Id);''')
 s=s.replace('Check(files[common].Keys.Count(n=>n.StartsWith("paws-hd-ui/"))==645,"HD priority depot incomplete");','''Check(files[common].ContainsKey("paws-hd-ui.rwd"),"compact UI depot missing");Check(files[common].Keys.Count(n=>n.StartsWith("skins/")&&n.EndsWith(".rwd"))==6,"faction archives missing");if(mod==GameMod.ArcaneWars)Check(y.Count(p=>p.Id=="arcane-biome-textures")==1&&!y.Any(p=>p.Id.StartsWith("arcane-biome-textures-")),"terrain is not grouped");''')
 (P/'catalog_check.py').write_text(s);print('COMPACT_CHECKS_READY')
if __name__=='__main__':main()
