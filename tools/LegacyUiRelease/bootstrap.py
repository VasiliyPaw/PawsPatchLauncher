from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[1]
s=(W/'work/ui-compact-release-20261117/context.py').read_text()
s=s.replace('ui-compact-release-20261117','ui-revert-release-20261118')
s=s.replace("ARC='0.6.0-beta.5';PURE='0.5.0-beta.9';RT='1.3.72-pure.21-beta.9';PR=WS/'outputs/ui-fullres-release-20261117'","ARC='0.6.0-beta.6';PURE='0.5.0-beta.10';RT='1.3.72-pure.21-beta.10';PR=WS/'outputs/ui-compact-release-20261117'")
s=s.replace("=='0.6.0-beta.4'","=='0.6.0-beta.5'").replace("=='0.5.0-beta.8'","=='0.5.0-beta.9'")
(P/'context.py').write_text(s)
s=(W/'work/ui-compact-release-20261117/build_helpers.py').read_text().replace("'0.6.0-beta.4'","'0.6.0-beta.5'").replace("'0.5.0-beta.8'","'0.5.0-beta.9'").replace("b'1.3.72-pure.21-beta.8'","b'1.3.72-pure.21-beta.9'")
(P/'build_helpers.py').write_text(s)
print('REVERT_BOOTSTRAP_READY')
