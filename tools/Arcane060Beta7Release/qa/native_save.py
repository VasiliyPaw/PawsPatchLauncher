"""Owned Arcane save-load observation. Authoring only until owner grants slot.
No start/swap/build, no !sp/API binding, no capture and no force termination.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, json, math, struct, sys, time, zipfile

WS = Path('G:/CodexData/projects/Codex/2026-09-09/paws-patch-kohan-ii-3')
ROOT = Path('G:/PawsWork/QA/ArcaneFix-20261125')
TOOLS = WS/'work/arcane-bridge-terrain-fixes-20261125/qa-tools'
OUT = WS/'outputs/arcane060-beta7-release-20261126/native-save'
SAVE = ROOT/'game/Userdata/Save/Mixed2.RSG'
SAVE_SOURCE = WS/'outputs/arcane-bridge-terrain-fixes-20261125/inputs/Смешанные биомы2.RSG'
OLD_CORE = WS/'outputs/ui-revert-release-20261118/arcane/assets/pawpatch-core-0.6.0-beta.6.zip'
EXPECTED = {
 'baseline': '5bc48f3d6639a70f34cd7f1a01ce948804350e927a873b4ff52f70fdbd2d7792',
 'final': 'b3c13e79390327e698e75c0bf380b78aea73a3c9c9945091bf058b1b4cad38e5',
}
IDS = (126895, 137800, 164550, 68772, 36003, 168153, 103335)
SITE_IDS = (126895, 137800, 164550)
NORMAL_BRIDGE_IDS = (68772, 36003, 168153, 103335)
FRONTEND = ('RequestSinglePlayer', 'RequestCustom',
 'SelectLaunchType LOAD_SAVED_GAME', 'Select save/mixed2.rsg', 'Commit', 'StagingLaunch')


def guarded(path, root):
 p, r = path.resolve(), root.resolve()
 if p.drive.upper() != 'G:' or not p.is_relative_to(r):
  raise RuntimeError('Outside the exact owned G: tree: '+str(path))
 return p


for directory, owner in ((ROOT, ROOT), (TOOLS, WS), (OUT, WS), (SAVE, ROOT),
                         (SAVE_SOURCE, WS)):
 guarded(directory, owner)
sys.path.insert(0, str(TOOLS))
import control as ctl
from memory import Memory
if ctl.folder('preview').resolve() != ROOT.resolve():
 raise RuntimeError('Legacy control is bound to a different private game')


def sha(path):
 with path.open('rb') as f:
  h = hashlib.sha256()
  for chunk in iter(lambda: f.read(65536), b''): h.update(chunk)
 return h.hexdigest()


def write(path, value):
 guarded(path, OUT)
 path.parent.mkdir(parents=True, exist_ok=True)
 temp = path.with_suffix(path.suffix+'.tmp')
 temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
 temp.replace(path)


def identity():
 j = json.loads((ROOT/'qa-process.json').read_text())
 if Path(j['exe']).resolve() != (ROOT/'game/k2.exe').resolve():
  raise RuntimeError('qa-process.json does not name the exact owned executable')
 matches = [p for p in ctl.own() if p['pid'] == j['pid'] and
            Path(p['path']).resolve() == (ROOT/'game/k2.exe').resolve()]
 if len(matches) != 1: raise RuntimeError('The recorded owned game is not running')
 return j


def observer(pid):
 path = ROOT/'game/Mods/network-state.json'
 s = json.loads(path.read_text())
 if s.get('pid') != pid: raise RuntimeError('Stale observer PID')
 return s, path.stat().st_mtime_ns


def wait_state(pid, predicate, seconds=30, newer=None):
 end, last = time.monotonic()+seconds, None
 while time.monotonic() < end:
  if not any(p['pid'] == pid for p in ctl.own()):
   raise RuntimeError('Owned game exited while waiting for observer')
  try:
   last, stamp = observer(pid)
   if (newer is None or stamp > newer) and predicate(last): return last, stamp
  except (OSError, ValueError): pass
  time.sleep(.08)
 raise TimeoutError('Observer wait timed out: '+repr(last))


def send(text):
 if '\n' in text or '\r' in text or text.startswith('!'):
  raise RuntimeError('Only the explicit ordinary native command is allowed')
 # control.command writes serial + command without a trailing newline.
 ctl.command('preview', text)


def reader(j, s):
 # Reuse Memory's existing read/u/f/name methods. Its usual initializer also
 # resolves bridge export/cave metadata, which differs for baseline vs final.
 # This read-only initializer needs ONLY a fresh observer base and owned PID.
 # It never resolves/calls an export, writes process memory or binds a QA API.
 m = Memory.__new__(Memory)
 m.role, m.root, m.identity, m.pid = 'preview', ROOT, j, j['pid']
 m.h = ctl.k.OpenProcess(0x410, False, m.pid)
 if not m.h: raise OSError('OpenProcess(read-only) failed')
 try:
  buf, count = C.create_unicode_buffer(32768), C.c_uint(32768)
  if not ctl.k.QueryFullProcessImageNameW(m.h, 0, buf, C.byref(count)) or \
     Path(buf.value).resolve() != (ROOT/'game/k2.exe').resolve():
   raise RuntimeError('Process image does not match the exact owned game')
  m.base = int(s['base'])
  if m.u(m.base) & 0xffff != 0x5a4d: raise RuntimeError('Observer base is not PE/MZ')
  return m
 except BaseException:
  m.close()
  raise


def definition(m, pointer):
 try: return m.name(pointer)
 except (AssertionError, OSError): return '<unreadable-definition>'


def target_record(m, reg, requested_id, players):
 slot = requested_id & 65535
 a = m.u(reg+0x20004+slot*4)
 row = {'requestedID': requested_id, 'slot': slot,
        'requestedGeneration': requested_id >> 16, 'pointer': a, 'present': bool(a)}
 if not a: return row
 try:
  actual = m.u(a+0x14)
  row.update(actualID=actual, actualGeneration=actual >> 16,
             exactIDMatch=actual == requested_id, vtable=m.u(a),
             nativeActorVtable=m.u(a) == m.base+0x4e5c58)
  if actual != requested_id:
   row['note'] = 'Slot reused or stale generation; this is not the requested actor'
   return row
  flags, runtime, body, owner = m.u(a+8), m.u(a+0x100), m.u(a+0x60), m.u(a+0xe8)
  owner_id = m.u(owner+0x14) if owner else None
  row.update(name=definition(m, m.u(a+4)), flags=flags, flagsHex=hex(flags),
             deadBit1=bool(flags & 1), dyingBit2=bool(flags & 2),
             corpseOrDyingBits=flags & 3, runtimeFlags=runtime,
             construction=bool(runtime & 0x200000), body=body,
             hp=m.f(body+0x10) if body else None,
             maxHP=m.f(body+0x14) if body else None,
             position=list(struct.unpack('<3f', m.read(a+0x20, 12))),
             ownerPointer=owner, ownerID=owner_id,
             ownerPlayers=[p for p in players if p.get('kingdom') == owner_id],
             corpseInterpretation='Native dead/dying bits recorded; no guessed ghost flag')
 except (AssertionError, OSError, ValueError) as error:
  row['readError'] = repr(error)
 return row


def registry_snapshot(j, s, full=False):
 m = reader(j, s)
 try:
  w, reg = m.u(m.base+0x5f3fb8), m.u(m.base+0x5ef72c)
  if not w or not reg: raise RuntimeError('Native world/registry not available')
  slots = struct.unpack('<65536I', m.read(reg+0x20004, 0x40000))
  counts = {'nonzeroRegistrySlots': sum(bool(a) for a in slots),
            'nativeActorVtableCount': 0, 'deadBit1': 0, 'dyingBit2': 0, 'readErrors': 0}
  bridges = []
  for a in dict.fromkeys(p for p in slots if p):
   try:
    if m.u(a) != m.base+0x4e5c58: continue
    counts['nativeActorVtableCount'] += 1
    flags = m.u(a+8)
    counts['deadBit1'] += bool(flags & 1)
    counts['dyingBit2'] += bool(flags & 2)
    if full and definition(m, m.u(a+4)).startswith('paws_bridge_'):
     bridges.append(target_record(m, reg, m.u(a+0x14), s.get('players', [])))
   except (AssertionError, OSError): counts['readErrors'] += 1
  sim, session = m.u(m.base+0x5f3fe8), m.u(m.base+0x5f3fe4)
  result = {'world': w, 'registry': reg, 'time': m.f(w+0xe8), 'tick': m.u(w+0xe4),
            'mode': m.u(session+0xf0) if session else None,
            'simulationPausedByte': m.read(sim+0x28, 1)[0] if sim else None,
            'simulationFrozenByte': m.read(sim+0x29, 1)[0] if sim else None,
            'counts': counts}
  if full:
   result['requestedActors'] = {str(i): target_record(m, reg, i, s.get('players', [])) for i in IDS}
   result['allBridgeActors'] = bridges
   result['allBridgeCounts'] = {'total': len(bridges),
    'alive': sum(not a.get('corpseOrDyingBits', 0) for a in bridges),
    'deadOrDying': sum(bool(a.get('corpseOrDyingBits', 0)) for a in bridges),
    'menuSites': sum(a.get('name', '').endswith('_site') for a in bridges),
    'construction': sum(bool(a.get('construction')) for a in bridges)}
  return result
 finally: m.close()


def inputs(label):
 dll = ROOT/'game/Mods/PawsBridges.dll'
 if sha(dll) != EXPECTED[label]: raise RuntimeError('Wrong DLL for '+label+'; owner must swap/re-pin it before starting')
 if sha(SAVE) != sha(SAVE_SOURCE): raise RuntimeError('Private Mixed2 differs from the original supplied save')
 copies = []
 for p in (SAVE, ROOT/'Documents/Kohan2/data/Save/Mixed2.RSG'):
  copies.append({'path': str(p), 'sha256': sha(p) if p.is_file() else None})
 if any(c['sha256'] != sha(SAVE_SOURCE) for c in copies):
  raise RuntimeError('Both private mounted Mixed2 copies must match the supplied save')
 return {'label': label, 'dll': str(dll), 'dllSHA256': sha(dll),
         'dllKind': 'baseline production beta.6' if label == 'baseline' else 'final109 production beta.7',
         'save': str(SAVE), 'saveSHA256': sha(SAVE), 'originalSave': str(SAVE_SOURCE),
         'mountedSaveCopies': copies, 'helperSHA256': sha(ROOT/'game/TestInstalledRuntime.exe'),
         'waterSHA256': sha(ROOT/'game/Mods/PawsWaterBiomes.dll')}


def prepare(label):
 if ctl.own(): raise RuntimeError('prepare requires the owned game/helper already closed')
 report = inputs(label)
 report.update(status='PREPARED_NOT_RUN', noProcessesStarted=True, noFilesCopied=True,
  staleAPIPaths=[str(p) for p in (ROOT/'game/Mods').glob('network-*-api.txt')],
  ownerBeforeStart=['Swap DLL/rebuild only its helper pin outside this script as required.',
   'Archive every old network-*-api.txt and observer/command file before control.start.',
   'Start preview using existing control, then activate only its owned window through AX.',
   'Run load-snapshot; this script never starts a process or activates a window.'])
 if label == 'baseline':
  with zipfile.ZipFile(OLD_CORE) as archive:
   names = [n for n in archive.namelist() if n.replace('\\', '/').lower() == 'payload/mods/pawsbridges.dll']
   if len(names) != 1: raise RuntimeError('Baseline ZIP does not have one expected Bridges entry')
   digest = hashlib.sha256(archive.read(names[0])).hexdigest()
   if digest != EXPECTED['baseline']: raise RuntimeError('Original signed core ZIP module hash differs')
   report['baselineArchiveMember'] = {'archive': str(OLD_CORE), 'member': names[0], 'sha256': digest}
 write(OUT/(label+'-prepare.json'), report)
 print('PREPARED_NOT_RUN', label)


def load_snapshot(label, timeout):
 report = inputs(label)
 j = identity()
 report.update(pid=j['pid'], startedUtc=time.time(), userReadySent=False,
               claimsPass=False, status='IN_PROGRESS', commandTrace=[])
 path = OUT/(label+'-pre-ready.json')
 try:
  s, _ = wait_state(j['pid'], lambda s: not s.get('world') and s.get('phase') == 3, 8)
  report['initialMenuObserver'] = s
  for text in FRONTEND:
   send(text)
   report['commandTrace'].append(text)
  s, stamp = wait_state(j['pid'], lambda s: bool(s.get('world')) and s.get('mode') == 2, timeout)
  report['firstLoadedObserver'] = s
  # RSG actors stream into the native registry after world creation. Wait for
  # that stream to settle before taking the frozen retention reference.
  settle_start, settled, previous, equal_run = time.monotonic(), [], None, 0
  while time.monotonic()-settle_start < 35:
   s, stamp = wait_state(j['pid'], lambda s: bool(s.get('world')) and s.get('mode') == 2, 3, stamp)
   probe = registry_snapshot(j, s)
   signature = (probe['world'], probe['tick'], probe['time'], json.dumps(probe['counts'], sort_keys=True))
   settled.append({'seconds': round(time.monotonic()-settle_start, 3), 'counts': probe['counts']})
   equal_run = equal_run+1 if signature == previous else 1
   previous = signature
   if time.monotonic()-settle_start >= 5 and equal_run >= 3:
    break
   time.sleep(.35)
  else:
   raise TimeoutError('Native save actor registry did not settle')
  report['actorLoadSettling'] = settled
  samples = []
  for index in range(3):
   if index: s, stamp = wait_state(j['pid'], lambda s: bool(s.get('world')) and s.get('mode') == 2, 3, stamp)
   samples.append({'observer': s, 'observerFileStampNs': stamp,
                   'native': registry_snapshot(j, s), 'recordedUtc': time.time()})
  native = registry_snapshot(j, s, full=True)
  same_clock = len({(v['native']['world'], v['native']['tick'], v['native']['time']) for v in samples}) == 1
  same_counts = len({json.dumps(v['native']['counts'], sort_keys=True) for v in samples}) == 1
  frozen = all(v['observer'].get('frozen') == 1 and v['native']['simulationFrozenByte'] == 1 for v in samples)
  valid_reads = all(v['native']['counts']['readErrors'] == 0 and math.isfinite(v['native']['time']) for v in samples)
  full_clock_stable = (native['world'], native['tick'], native['time']) == (samples[0]['native']['world'], samples[0]['native']['tick'], samples[0]['native']['time'])
  full_counts_stable = native['counts'] == samples[0]['native']['counts']
  full_frozen = native['simulationFrozenByte'] == 1
  expected_bridges = all(native['requestedActors'].get(str(i), {}).get('exactIDMatch') and
   native['requestedActors'][str(i)].get('name', '').startswith('paws_bridge_') and
   not native['requestedActors'][str(i)].get('name', '').endswith('_site') for i in NORMAL_BRIDGE_IDS)
  report.update(samples=samples, snapshot=native, initialWorldTime=samples[0]['native']['time'],
   freezeEvidence={'allThreeObserverAndNativeFrozen': frozen, 'stableWorldTickTime': same_clock,
    'threeStableActorCountSamples': same_counts, 'nativeReadsValid': valid_reads, 'fullSnapshotClockStable': full_clock_stable,
    'fullSnapshotCountsStable': full_counts_stable, 'fullSnapshotFrozen': full_frozen,
    'noAITicksObservedDuringSamples': bool(frozen and same_clock),
    'beforeFirstObservedSample': 'Not directly measured; never infer zero prior ticks from three later samples.'},
   expectedNormalBridgeIdsPresent=expected_bridges,
   eligibleForRetentionComparison=bool(frozen and same_clock and same_counts and valid_reads and full_clock_stable and full_counts_stable and full_frozen and expected_bridges),
   status='RECORDED_PRE_USER_READY', userReadySent=False)
  # Secondary legacy snap is intentionally not the retention authority: it
  # excludes dead/dying actors. Its failure cannot erase the raw registry data.
  try:
   import review
   original_reader = review.Memory
   try:
    # Existing snap logic, with the same baseline-safe read-only reader.
    review.Memory = lambda role: reader(j, s)
    report['legacyAliveOnlyReviewSnap'] = review.snap()
   finally: review.Memory = original_reader
  except Exception as error: report['legacyReviewSnapError'] = repr(error)
  write(path, report)
  print('RECORDED_PRE_USER_READY', label, 'eligible='+str(report['eligibleForRetentionComparison']))
 except BaseException as error:
  report.update(status='INCOMPLETE', error=repr(error), eligibleForRetentionComparison=False)
  write(path, report)
  raise


def resume_smoke(label, timeout):
 before = json.loads((OUT/(label+'-pre-ready.json')).read_text())
 j = identity()
 if j['pid'] != before['pid']: raise RuntimeError('Resume must use the same observed owned process')
 report = dict(inputs(label), pid=j['pid'], preReadyRecord=str(OUT/(label+'-pre-ready.json')),
               claimsRetentionPass=False, status='IN_PROGRESS')
 try:
  send('UserReady')
  s, stamp = wait_state(j['pid'], lambda s: s.get('phase') == 4, timeout)
  send('GamePause 1')
  send('GameSpeed 0')
  samples = []
  until = time.monotonic()+1.0
  while time.monotonic() < until:
   s, stamp = wait_state(j['pid'], lambda s: s.get('phase') == 4, 3, stamp)
   samples.append(s)
  report.update(status='POST_USER_READY_RECORDED', userReadySent=True, observerSamples=samples,
   snapshot=registry_snapshot(j, s, full=True),
   processStillOwned=any(p['pid'] == j['pid'] for p in ctl.own()), gamePausedObserved=bool(s.get('paused')),
   gameplayDifferenceExpected='AI/load callbacks may act after UserReady; this is a crash smoke, not the retention comparison.')
  write(OUT/(label+'-post-ready.json'), report)
  print('POST_USER_READY_RECORDED', label)
 except BaseException as error:
  report.update(status='INCOMPLETE', error=repr(error))
  write(OUT/(label+'-post-ready.json'), report)
  raise


def compare():
 records = {label: json.loads((OUT/(label+'-pre-ready.json')).read_text()) for label in EXPECTED}
 eligible = all(r.get('eligibleForRetentionComparison') and r.get('expectedNormalBridgeIdsPresent') and not r.get('userReadySent') and
  r.get('status') == 'RECORDED_PRE_USER_READY' and r.get('commandTrace') == list(FRONTEND) and
  r.get('dllSHA256') == EXPECTED[label] for label, r in records.items())
 inputs_equal = len({r['saveSHA256'] for r in records.values()}) == 1
 keys = ('present', 'exactIDMatch', 'actualID', 'name', 'flags', 'runtimeFlags', 'hp', 'maxHP', 'ownerID', 'position')
 differences = []
 for requested in map(str, IDS):
  a = records['baseline'].get('snapshot', {}).get('requestedActors', {}).get(requested, {})
  b = records['final'].get('snapshot', {}).get('requestedActors', {}).get(requested, {})
  delta = {k: {'baseline': a.get(k), 'final': b.get(k)} for k in keys if a.get(k) != b.get(k)}
  if delta: differences.append({'requestedID': requested, 'differences': delta})
 clocks = {label: r.get('initialWorldTime') for label, r in records.items()}
 same_initial_time = len(set(clocks.values())) == 1 and all(v is not None for v in clocks.values())
 counts = {label: r.get('snapshot', {}).get('allBridgeCounts') for label, r in records.items()}
 read_errors = any('readError' in actor for r in records.values() for actor in r.get('snapshot', {}).get('requestedActors', {}).values())
 report = {'passed': bool(eligible and inputs_equal and same_initial_time and not differences and not read_errors and counts['baseline'] == counts['final']),
  'eligiblePreReadyRecords': eligible, 'sameOriginalSave': inputs_equal, 'sameInitialWorldTime': same_initial_time,
  'initialWorldTimes': clocks, 'allBridgeCounts': counts, 'differences': differences,
  'baselineSiteExactPresence': {str(i): bool(records['baseline'].get('snapshot', {}).get('requestedActors', {}).get(str(i), {}).get('exactIDMatch')) for i in SITE_IDS},
  'allSevenExactIDsPresentInBoth': all(records[label].get('snapshot', {}).get('requestedActors', {}).get(str(i), {}).get('exactIDMatch') for label in EXPECTED for i in IDS),
  'interpretation': 'A matching baseline can already lack a dead/removed saved ID. Passing means no additional difference from baseline, not that every historical actor exists.',
  'scope': 'Only pre-UserReady actor retention for the exact baseline/final DLL hashes and Mixed2 SHA; no AI planning or multiplayer claim.'}
 write(OUT/'comparison.json', report)
 print(json.dumps(report, ensure_ascii=False, indent=2))


def quit_owned(label):
 report = {'label': label, 'status': 'QUIT_REQUESTED', 'command': 'ReallyQuit',
           'newlineAppended': False, 'forceTermination': False}
 try:
  current = ctl.own()
  game = [p for p in current if Path(p['path']).resolve() == (ROOT/'game/k2.exe').resolve()]
  if game:
   j = identity()
   report['pid'] = j['pid']
   try: send('ReallyQuit')
   except Exception as error: report['commandAckError'] = repr(error)
  else: report['gameAlreadyExited'] = True
  end = time.monotonic()+15
  while ctl.own() and time.monotonic() < end: time.sleep(.1)
  report['remainingOwn'] = ctl.own()
  report['status'] = 'OWNED_CLOSED' if not report['remainingOwn'] else 'OWNED_EXIT_NOT_CONFIRMED'
  write(OUT/(label+'-quit.json'), report)
  print(report['status'])
 finally:
  # No final-plugins.txt restore/read, no capture APIs and no force-kill fallback.
  pass


def main():
 p = argparse.ArgumentParser(description=__doc__)
 p.add_argument('mode', choices=('prepare', 'load-snapshot', 'resume-smoke', 'quit', 'compare'))
 p.add_argument('--label', choices=tuple(EXPECTED))
 p.add_argument('--timeout', type=float, default=45)
 args = p.parse_args()
 if args.mode != 'compare' and not args.label: p.error('--label is required')
 if not 1 <= args.timeout <= 60: p.error('--timeout must be within1..60 seconds')
 if args.mode == 'prepare': prepare(args.label)
 elif args.mode == 'load-snapshot': load_snapshot(args.label, args.timeout)
 elif args.mode == 'resume-smoke': resume_smoke(args.label, args.timeout)
 elif args.mode == 'quit': quit_owned(args.label)
 else: compare()


if __name__ == '__main__': main()
