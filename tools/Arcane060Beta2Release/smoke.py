from context import *
import shutil
for name in ['review.py','native_review.py']:shutil.copy2(PREV/name,P/name)
(P/'target.txt').write_text(str(R));shutil.copy2(PREV/'PawsNetworkQA.dll',P/'PawsNetworkQA.dll')
s=(PREV/'product_smoke.py').read_text().replace('from release_context import *','from context import *').replace("E=FIX/'evidence'","E=O/'native-evidence'")
(P/'product_smoke.py').write_text(s)
exec(compile(s,str(P/'product_smoke.py'),'exec'),dict(__name__='__main__',__file__=str(P/'product_smoke.py')))
