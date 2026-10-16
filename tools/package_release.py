"""Package this MIT loader fork and its complete build inputs; never install it."""
# Copyright (c) 2026 DialogueOutline contributors
# SPDX-License-Identifier: MIT
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/packages'
VERSION = '0.1.0'


def digest(data):
    return sha256(data).hexdigest()


def archive(name, files):
    target = OUTPUT / name
    with ZipFile(target, 'w') as z:
        for relative, data in sorted(files.items()):
            entry = ZipInfo(relative, (2026, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            z.writestr(entry, data)
    with ZipFile(target) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC check failed')
        for relative, data in files.items():
            if z.read(relative) != data:
                raise ValueError('ZIP payload differs: ' + relative)
    return dict(file=name, sha256=digest(target.read_bytes()), bytes=target.stat().st_size)


def main():
    report_bytes = (ROOT / 'build/report.json').read_bytes()
    report = json.loads(report_bytes)
    dll = (ROOT / 'build/xinput1_4.dll').read_bytes()
    if digest(dll) != report['dll_sha256']:
        raise ValueError('Loader differs from its build report')
    expected_inputs = {name: ROOT / name for name in ('build.py', 'dllmain.cpp', 'proxy.cpp', 'pch.h',
                       'framework.h', 'dialogue_outline_loader.h', 'LicenseNotice.h', 'LICENSE',
                       'external/detours/LICENSE.md')}
    expected_inputs.update({path.relative_to(ROOT).as_posix(): path
                            for path in (ROOT / 'external/detours/src').iterdir()
                            if path.suffix in ('.h', '.cpp')})
    if set(report['sources']) != set(expected_inputs):
        raise ValueError('Build input set differs; rebuild before packaging')
    for relative, expected in report['sources'].items():
        if digest(expected_inputs[relative].read_bytes()) != expected:
            raise ValueError('Source changed after build: ' + relative)
    sources = {path.name: path.read_bytes() for path in ROOT.iterdir() if path.is_file()}
    for folder in ('.github', 'tools', 'external/detours'):
        for path in sorted((ROOT / folder).rglob('*')):
            relative_parts = path.relative_to(ROOT / folder).parts
            if path.is_file() and not any(part in {'.git', '__pycache__', 'build'}
                                           or part.startswith(('bin.', 'lib.', 'obj.'))
                                           for part in relative_parts):
                sources[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    forbidden = {'.dll', '.exe', '.obj', '.lib', '.pdb', '.pac', '.dds', '.lay', '.asi'}
    if any(Path(name).suffix.lower() in forbidden for name in sources):
        raise ValueError('Source distribution contains native outputs or game resources')
    source_hashes = {name: digest(data) for name, data in sorted(sources.items())}
    sources['SOURCE_MANIFEST.json'] = (json.dumps(dict(source_git=report['source_git'],
        upstream_commit=report['upstream_commit'], detours_commit=report['detours_commit'],
        files=source_hashes), indent=2) + '\n').encode('utf-8')
    binary = {'xinput1_4.dll': dll}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    artifacts = [archive(f'sora1looseload-v{VERSION}.zip', binary),
                 archive(f'sora1looseload-v{VERSION}-source.zip', sources)]
    manifest = dict(version=VERSION, repository=report['fork_repository'], source_git=report['source_git'],
                    dll_sha256=report['dll_sha256'], game_runtime_verified=False, artifacts=artifacts,
                    files=[dict(path=name, bytes=len(data), sha256=digest(data))
                           for name, data in sorted(binary.items())],
                    native_build_report_sha256=digest(report_bytes), native_build_report=report)
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
