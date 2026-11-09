"""Load an actual beta1 save, then create another match under the optimized helper."""
from adapt_live import *
p=REPO/'tools/Pure050Release/live_resume.py';s=p.read_text();s=s.replace("source=HERE/'live_beta.py';outer=source.read_text()","source=REPO/'tools/Pure050Release/live_beta.py';outer=adapt_outer(source.read_text())")
# The replacement scenario checks the new native modules in both worlds.
s=s.replace("loadedview=details(h)","loadedview=details(h);check_optimizations(h,'loaded')")
s=s.replace("secondview=details(h)","secondview=details(h);check_optimizations(h,'second')")
exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p),'adapt_outer':adapt_outer})
