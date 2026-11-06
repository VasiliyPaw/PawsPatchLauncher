from pathlib import Path
import subprocess,sys,shutil
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3];OUT=WS/'outputs/mixed-biomes-r2-20261106';emit=OUT/'hud-emitted';emit.mkdir(exist_ok=True)
shutil.copy2(OUT/'hud/hud.bin',emit/'hud-layout.bin');shutil.copy2(WS/'outputs/publish-hud-20261027/emitted/uniform-phase.bin',emit/'uniform-phase.bin')
source=(HERE.parent/'widescreen-ui/test_hud_layout.py').read_text()
source=source.replace("('Other',100,456,None)","('GameMenuDialog',358.4,308,0),('StagingFileSavedDialog',128,826,0),('StagingFileLoadSavedDialog',128,826,0),('GameFileDialog',128,820,None),('GameMenuDialogExtra',358.4,308,None),('StagingFileSavedDialogExtra',128,820,None),('Other',100,456,None)")
test=OUT/'test_hud_mixed_local.py';test.write_text(source)
args=[sys.executable,str(test),'--legacy','G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work','--emitted',str(emit),'--fixups',str(OUT/'hud/hud-fixups.json')]
result=subprocess.run(args,capture_output=True,text=True);(OUT/'ui-tests.log').write_text(result.stdout+result.stderr);print(result.stdout+result.stderr);result.check_returncode()
