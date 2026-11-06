from pathlib import Path
import json,subprocess
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3];OUT=WS/'outputs/mixed-biomes-r2-20261106'
row=json.loads((OUT/'build.json').read_text());args=[a for a in row['args'] if not a.startswith(('/out:','/target:','/main:'))]
args[1:1]=['/target:exe','/main:MixedTransactionTests','/out:'+str(OUT/'TransactionTests.exe')];args.append(str(HERE/'TransactionTests.cs'))
subprocess.run(args,check=True)
r=subprocess.run([str(OUT/'TransactionTests.exe')],capture_output=True,text=True);(OUT/'transaction-tests.log').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr);r.check_returncode()
