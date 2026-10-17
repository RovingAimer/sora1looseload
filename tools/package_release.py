"""Package the current loader and complete tracked source; never install it."""
# Copyright (c) 2026 DialogueOutline contributors
# Copyright (c) 2026 SoraMod contributors
# SPDX-License-Identifier: MIT
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/packages'
sys.path.insert(0, str(ROOT))
import build


def digest(data):
    return sha256(data).hexdigest()


def archive(name, kind, files):
    target = OUTPUT / name
    with ZipFile(target, 'w') as zipped:
        for relative, data in sorted(files.items()):
            entry = ZipInfo(relative, (2026, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            zipped.writestr(entry, data)
    with ZipFile(target) as zipped:
        if zipped.testzip() is not None:
            raise ValueError('ZIP CRC check failed')
        for relative, data in files.items():
            if zipped.read(relative) != data:
                raise ValueError('ZIP payload differs: ' + relative)
    return dict(file=name, kind=kind, sha256=digest(target.read_bytes()),
        bytes=target.stat().st_size, members=[dict(path=name, bytes=len(data), sha256=digest(data))
            for name, data in sorted(files.items())])


def tracked_files(folder):
    result = subprocess.check_output(['git', '-C', str(folder), 'ls-files', '-z'])
    return [name for name in result.decode('utf-8').split('\0') if name]


def source_files():
    # Git excludes ignored research, local game inputs and build outputs.
    # Include the entire pinned Detours checkout and its original licenses.
    if (ROOT / '.git').exists():
        names = [name for name in tracked_files(ROOT)
                 if name != 'external/detours' and not name.startswith('docs/superpowers/')]
        names += ['external/detours/' + name for name in tracked_files(ROOT / 'external/detours')]
    else:
        snapshot = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
        names = list(snapshot['files'])
        for name, expected in snapshot['files'].items():
            if digest((ROOT / name).read_bytes()) != expected:
                raise ValueError('Source archive was modified: ' + name)
    forbidden = {'.dll', '.exe', '.obj', '.lib', '.pdb', '.pac', '.dds', '.lay', '.asi', '.pyc'}
    for name in names:
        parts = Path(name).parts
        if (Path(name).suffix.lower() in forbidden or
                any(part in {'.git', '.superpowers', '__pycache__', 'build', 'research'} for part in parts)):
            raise ValueError('Source distribution contains an excluded input: ' + name)
    return {name: (ROOT / name).read_bytes() for name in names}


def main():
    plan = json.loads((ROOT / 'release_plan.json').read_text(encoding='utf-8'))
    version = plan['version']
    source_git = build.git_info()
    if not source_git['commit'] or source_git['dirty'] is not False:
        raise ValueError('Commit the source snapshot before packaging')
    report_bytes = (ROOT / 'build/report.json').read_bytes()
    report = json.loads(report_bytes)
    dll = (ROOT / 'build/xinput1_4.dll').read_bytes()
    if digest(dll) != report['dll_sha256']:
        raise ValueError('Loader differs from its build report')
    if set(report['sources']) != set(build.build_inputs()):
        raise ValueError('Build input set differs; rebuild before packaging')
    for name, expected in report['sources'].items():
        if digest((ROOT / name).read_bytes()) != expected:
            raise ValueError('Compiled input changed; rebuild before packaging: ' + name)
    if report['detours_commit'] != build.DETOURS:
        raise ValueError('Build dependency differs from the pinned Detours commit')
    build.verify_licenses(dll)
    sources = source_files()
    for name, expected in report['sources'].items():
        if name not in sources or digest(sources[name]) != expected:
            raise ValueError('Source distribution does not cover the build input: ' + name)
    source_hashes = {name: digest(data) for name, data in sorted(sources.items())}
    sources['SOURCE_MANIFEST.json'] = (json.dumps(dict(source_git=source_git,
        upstream_commit=report['upstream_commit'], detours_commit=report['detours_commit'],
        files=source_hashes), indent=2) + '\n').encode('utf-8')
    binary = {'xinput1_4.dll': dll,
              'mods/DialogueOutline/sora_mod.ini': (ROOT / 'mods/DialogueOutline/sora_mod.ini').read_bytes()}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'build-report.json').write_bytes(report_bytes)
    artifacts = [archive(f'sora1looseload-v{version}.zip', 'installation', binary),
                 archive(f'sora1looseload-v{version}-source.zip', 'source', sources)]
    manifest = dict(version=version, repository=plan['repository'], source_git=source_git,
        dll_sha256=report['dll_sha256'], game_runtime_verified=False, artifacts=artifacts,
        native_build_report_sha256=digest(report_bytes), native_build_report=report)
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(version=version, source_git=source_git,
        artifacts=[{key: asset[key] for key in ('file', 'sha256', 'bytes')} for asset in artifacts]), indent=2))


if __name__ == '__main__':
    main()
