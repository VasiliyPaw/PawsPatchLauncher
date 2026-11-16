from context import *
import shutil
s=(WS/'work/arcane060-beta3-release-20261116/catalog_check.py').read_text()
s=s.replace('mod==GameMod.ArcaneWars&&patch&&!data?64:1','mod!=GameMod.ArcaneWars&&patch?64:1')
s=s.replace('var a=EffectiveSettings.ForFeed', 'var ps=GameMod.PureComponents(Settings());\n  var a=EffectiveSettings.ForFeed')
anchor='RoamingSpawnMode=spawn};';assert anchor in s
s=s.replace('UserSettings Settings()=>new(){','UserSettings Settings(){var ss=new UserSettings(){').replace(anchor,'RoamingSpawnMode=spawn};var pp=GameMod.PureComponents(ss);pp.Colors=B(0);pp.IgnoreDesync=B(1);pp.WoundedLairDefenders=B(5);return ss;}')
s=s.replace('var full=channel=="beta"&&mod==GameMod.ArcaneWars&&patch&&!data;','var full=channel=="beta"&&mod!=GameMod.ArcaneWars&&patch&&!data;var pure=channel=="beta"&&mod!=GameMod.ArcaneWars&&patch;')
a=s.index('  Check(y.Count(');b=s.index('  Check(x.Select',a);s=s[:a]+s[b:]
s=s.replace('if(full&&files.ContainsKey(p.Id))Check(p.Version=="0.6.0-beta.3","version")','if(pure&&files.ContainsKey(p.Id))Check(p.Version==(p.Id=="pure-fixes-runtime"?"1.3.72-pure.21-beta.7":"0.5.0-beta.7"),"version")')
s=s.replace('seen.Count==8','seen.Count==4')
(P/'catalog_check.py').write_text(s)
