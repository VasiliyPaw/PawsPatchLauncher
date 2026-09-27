"""Stage beta.8 lobby/UI fixes using the signed runtime-only release pipeline."""
import argparse
from pathlib import Path
import PrepareDesyncBeta4 as release
from PrepareFiberSyncBeta6 import checks as retained_checks

release.VERSION='0.4.0-beta.8'
release.BASELINE_VERSION='0.4.0-beta.7'
release.AI_POLICY_REVISION=38
release.RELEASE_DATE='2026-09-27'
release.TAG='patch-'+release.VERSION
release.URL='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+release.TAG+'/'

def clean_recent_notes(entries):
    for entry in entries:
        if entry.get('category')=='patch' and entry.get('mods')==['arcane-wars'] and entry.get('version') in ['0.4.0-beta.'+str(n) for n in range(4,9)]:
            entry['body']=release.read(release.REPO/('docs/release-patch-'+entry['version']+'.json'))
    return entries

release.extra_changelog_transform=clean_recent_notes

def checks(stage):
    retained_checks(stage)
    report=release.read(stage/'offline-verification.json')
    assert report['passed'] and not report['gameLaunched'] and report['launcherTestsPassed']
    assert report['botLobbyCases']==120 and report['botLobbyInstallChecks']==675
    assert report['presentationInstallChecks']==203 and report['helperSelfTests']==40
    assert report['buttonTests']['tooltip-hover-tests.json']['checks']==276
    for path,digest in report['sourceSha256'].items():
        assert release.sha(release.REPO/path)==digest,'Tested source changed: '+path
    for name,digest in report['helperSha256'].items():
        assert release.sha(stage/'beta-helpers'/name)==digest,'Tested helper changed: '+name
        assert release.feature(stage/'beta-helpers'/name)['bulkBotLobbyRevision']==3

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--signing-dir',type=Path)
    p.add_argument('--action',choices=['prepare','public','promote'],default='prepare');a=p.parse_args()
    checks(a.stage)
    if a.action=='promote':assert release.read(a.stage/'lobby-tooltip-package-verification.json')['passed']
    {'prepare':release.prepare,'public':release.public,'promote':release.promote}[a.action](a)
