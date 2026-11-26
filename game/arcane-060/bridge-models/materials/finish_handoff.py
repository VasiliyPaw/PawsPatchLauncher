"""Package source and evidence only after the complete material manifest exists."""
from pathlib import Path
import json, shutil, sys
import numpy as np
import generate as core
import pyffi

HERE = Path(__file__).resolve().parent


def main():
    manifest = json.loads((HERE / 'final-manifest.json').read_text(encoding='utf-8'))
    checkpoint = json.loads((HERE / 'checkpoint.json').read_text(encoding='utf-8'))
    inputs = json.loads((HERE / 'inputs-manifest.json').read_text(encoding='utf-8'))
    assert manifest['complete'] and manifest['models'] == len(checkpoint['models']) == 672
    assert not manifest['newCastShadows'] and not manifest['newProjectedShadows']
    assert core.sha(HERE / 'checkpoint.json') == manifest['scriptAndEvidenceSha256']['checkpoint.json']
    refs = {}
    for relative, approved in inputs['approvedReferences'].items():
        row = checkpoint['models'][relative]
        assert row['approvedBytesReused'] and row['invariantsExact']
        assert row['referenceMaxColorDelta'] <= 2e-6
        assert row['sha256'] == approved['candidateSha256']
        refs[relative] = {
            'approvedSha256': approved['candidateSha256'],
            'outputSha256': row['sha256'],
            'maxColorDelta': row['referenceMaxColorDelta'],
            'invariantsExact': True,
        }
    assert len(refs) == 24
    core.atomic(HERE / 'reference-parity.json', {
        'complete': True, 'references': refs, 'count': 24,
        'observedMaximumColorDelta': max(r['maxColorDelta'] for r in refs.values()),
        'approvedOutputsByteExact': True,
    })
    core.atomic(HERE / 'build-environment.json', {
        'python': sys.version, 'pythonExecutable': sys.executable,
        'pythonExecutableSha256': core.sha(Path(sys.executable)),
        'numpy': np.__version__, 'pyffi': getattr(pyffi, '__version__', 'unknown'),
        'algorithmUnchanged': True, 'gameSdkGpuUsed': False,
    })
    paths = [HERE / name for name in [
        'generate.py', 'ao_trace.c', 'prepare_inputs.py', 'finalize.py',
        'run_batch.ps1', 'generate_shard.py', 'merge_shards.py', 'finish_handoff.py',
        'REPRODUCE.txt', 'inputs-manifest.json', 'checkpoint.json',
        'dispatch-checkpoint.json', 'shard-0.json', 'shard-1.json',
        'final-manifest.json', 'reference-parity.json', 'build-environment.json',
        'compile.json', 'last-closure.json', 'closure-shard-0.json', 'closure-shard-1.json',
    ]]
    paths += [core.OLD / name for name in [
        'build_candidate.py', 'candidate-manifest.json', 'candidate-manifest-16.json',
    ]]
    target = HERE / 'source-handoff'
    target.mkdir(exist_ok=True)
    records = {}
    for source in paths:
        out = target / source.name
        shutil.copy2(source, out)
        assert core.sha(out) == core.sha(source)
        records[source.name] = {
            'source': str(source), 'sha256': core.sha(out), 'bytes': out.stat().st_size,
        }
    core.atomic(target / 'source-manifest.json', records)
    core.atomic(HERE / 'handoff.json', {
        'complete': True, 'models': 672, 'files': len(manifest['files']),
        'overlay': str(HERE / 'overlay'),
        'manifestSha256': core.sha(HERE / 'final-manifest.json'),
        'sourceManifestSha256': core.sha(target / 'source-manifest.json'),
        'newCastShadows': False, 'newProjectedShadows': False,
        'installedOrPublished': False,
        'nativeReviewLimit': 'Prior native screenshots covered count16 only; all672 structurally checked.',
    })
    print((HERE / 'handoff.json').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    main()
