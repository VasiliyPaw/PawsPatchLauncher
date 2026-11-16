from context import *
fog=WS/'work/capture-hud-fog-20261116'
s=(fog/'control.py').read_text();a=s.index("N=Path(");b=s.index('\nk=C.WinDLL',a);s=s[:a]+"MODE=json.loads((Path(__file__).with_name('active-mode.json')).read_text())['mode'];N=Path('G:/PawsWork/QA/Pure050Beta7-20261116')/('network-'+MODE);W=Path('G:/CodexData/projects/Codex/2026-09-09/paws-patch-kohan-ii-3/work');ROLES=('host','client','witness');PORT=6221"+s[b:]
a=s.index(' return Path(',s.index('def folder('));b=s.index('\n',a);s=s[:a]+" return Path('G:/PawsWork/QA/Pure050Beta7-20261116')/MODE if role=='host'else N/role"+s[b:];(P/'control.py').write_text(s)
(P/'checksums.py').write_text((fog/'checksums.py').read_text().replace('from common import O','from context import O'))
s=(fog/'match.py').read_text().replace('from common import O','from context import O').replace("native('host','!port 6115')","native('host','!port 6221')").replace('InternetGameCreate ArcaneBeta2Private','InternetGameCreate PureBeta7Private');(P/'match.py').write_text(s)
write(P/'active-mode.json',dict(mode='vanilla'))
