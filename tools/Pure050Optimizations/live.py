"""Owned functional acceptance with actual menu readiness and optimization probes."""
from adapt_live import *
p=REPO/'tools/Pure050Release/live_beta.py';s=adapt_outer(p.read_text())
exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p),'OUT':OUT})
