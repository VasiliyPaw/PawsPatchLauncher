from context import *
dump=LEGACY/'k2_runtime_1372_20260904.bin';deps=['--deps',LEGACY/'pydeps_readable','--deps',LEGACY/'lobby_colors_1372/deps_r15']
print(run([sys.executable,S/'game/capture-knowledge/test_capture.py','--runtime',dump,'--dll',O/'native/PawsCaptureTest.dll',*deps,'--report',O/'callback-tests.json'],O/'callback-tests.log'))
print(run([sys.executable,S/'game/ui-scout-test/test_clock_picking.py','--runtime',dump,*deps,'--report',O/'clock-tests.json'],O/'clock-tests.log'))
