"""Build this fork offline; never install or execute a game or produced DLL.
MIT; original loader Copyright (c) 2025 Hinkiii.
Build and integration additions Copyright (c) 2026 DialogueOutline contributors.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'build'
UPSTREAM = '04e898e369e3019d5aa2cb13a7209de39c643a4a'
DETOURS = '9764cebcb1a75940e68fa83d6730ffaf0f669401'
DETOURS_OBJECTS = ('detours', 'modules', 'disasm', 'image', 'creatwth', 'disolx86',
                   'disolx64', 'disolia64', 'disolarm', 'disolarm64')


def build_inputs():
    """Only files used by the native build; documentation does not require rebuilding."""
    inputs = ['build.py', 'dllmain.cpp', 'proxy.cpp', 'pch.h', 'framework.h',
              'mod_loader.h', 'pe_module_check.h', 'LicenseNotice.h']
    inputs += ['external/detours/src/' + name + '.cpp' for name in DETOURS_OBJECTS]
    inputs += ['external/detours/src/' + name for name in ('detours.h', 'detver.h', 'uimports.cpp')]
    return sorted(inputs)


def verify_licenses(dll):
    for name in ('LICENSE', 'external/detours/LICENSE.md'):
        notice = (ROOT / name).read_bytes().replace(b'\r\n', b'\n').strip()
        if notice not in dll:
            raise ValueError('Complete license is missing from DLL: ' + name)
    for owner in (b'2025 Hinkiii', b'2026 DialogueOutline contributors',
                  b'2026 SoraMod contributors', b'Microsoft Corporation'):
        if owner not in dll:
            raise ValueError('Copyright notice is missing from DLL: ' + owner.decode())


def compiler_environment(sdk_root=None):
    finder = Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / \
        'Microsoft Visual Studio/Installer/vswhere.exe'
    install = subprocess.check_output([str(finder), '-latest', '-products', '*', '-requires',
        'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'],
        text=True).strip()
    if not install:
        raise RuntimeError('MSVC x64 Build Tools and Windows SDK are required')
    environment = os.environ.copy()
    environment['PATH'] = environment.get('PATH', '').replace('"', '')
    environment.update(TEMP=str(OUTPUT), TMP=str(OUTPUT), VSLANG='1033', VSCMD_SKIP_SENDTELEMETRY='1')
    setup = Path(install) / 'VC/Auxiliary/Build/vcvars64.bat'
    command = OUTPUT / 'toolchain_env.cmd'
    command.write_text(f'@echo off\ncall "{setup}" >nul\nif errorlevel 1 exit /b 1\nset\n', encoding='ascii')
    result = subprocess.run(['cmd.exe', '/d', '/c', str(command)], cwd=OUTPUT, env=environment,
        capture_output=True, text=True, encoding='mbcs', check=True)
    for line in result.stdout.splitlines():
        key, separator, value = line.partition('=')
        if separator and key:
            environment[key] = value
    environment.update(TEMP=str(OUTPUT), TMP=str(OUTPUT), VSLANG='1033')
    if sdk_root:
        sdk = sdk_root.resolve()
        versions = sorted((sdk / 'Include').glob('10.*'),
                          key=lambda path: tuple(int(part) for part in path.name.split('.')))
        if not versions:
            raise RuntimeError('SDK root must contain Include/10.x')
        include = versions[-1]
        libraries = sdk / 'Lib' / include.name
        if not libraries.is_dir():
            libraries = sdk  # Workspace SDK stores um/x64 and ucrt/x64 here.
        for path in (include / 'um/windows.h', include / 'ucrt/stdio.h',
                     libraries / 'um/x64/kernel32.lib', libraries / 'ucrt/x64/libucrt.lib'):
            if not path.is_file():
                raise RuntimeError('Incomplete SDK: ' + str(path))
        environment['INCLUDE'] = ';'.join(str(include / part) for part in
            ('ucrt', 'shared', 'um', 'winrt')) + ';' + environment.get('INCLUDE', '')
        environment['LIB'] = ';'.join(str(libraries / part / 'x64') for part in
            ('um', 'ucrt')) + ';' + environment.get('LIB', '')
        environment['WindowsSDKVersion'] = include.name + chr(92)
    return environment


def run(arguments, environment, log, commands):
    commands.append([str(value) for value in arguments])
    result = subprocess.run([str(value) for value in arguments], cwd=OUTPUT, env=environment,
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    (OUTPUT / log).write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'{Path(arguments[0]).name} failed; see {OUTPUT / log}')



def git_info():
    if not (ROOT / '.git').exists():
        snapshot = ROOT / 'SOURCE_MANIFEST.json'
        if snapshot.is_file():
            return json.loads(snapshot.read_text(encoding='utf-8'))['source_git']
        return {'commit': None, 'dirty': None}
    command = ['git', '-c', 'safe.directory=' + ROOT.as_posix()]
    commit = subprocess.check_output(command + ['rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(command + ['status', '--porcelain'], cwd=ROOT, text=True).strip())
    return dict(commit=commit, dirty=dirty)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-root', type=Path,
                        help='Optional SDK root with Include/10.x and Lib/10.x (or um/ucrt)')
    args = parser.parse_args()
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / 'report.json').unlink(missing_ok=True)
    detours = ROOT / 'external/detours/src'
    if not (detours / 'detours.cpp').is_file():
        raise RuntimeError('Missing Detours source: clone with --recursive or use the complete source archive')
    if (ROOT / 'external/detours/.git').exists():
        actual = subprocess.check_output(['git', '-C', str(detours.parent), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != DETOURS:
            raise ValueError('Detours commit differs from the pinned build dependency')
    sources = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in build_inputs()}
    environment = compiler_environment(args.sdk_root)
    locate = lambda name: shutil.which(name, path=environment['PATH'])
    compiler, librarian, linker, dumper = map(locate, ('cl.exe', 'lib.exe', 'link.exe', 'dumpbin.exe'))
    if not all((compiler, librarian, linker, dumper)):
        raise RuntimeError('Incomplete MSVC x64 toolchain')
    compiler_banner = subprocess.run([compiler], env=environment, capture_output=True,
        text=True, encoding='utf-8', errors='replace')
    compiler_version = compiler_banner.stderr.strip().splitlines()[0]
    commands = []
    objects = []
    for name in DETOURS_OBJECTS:
        obj = OUTPUT / (name + '.obj')
        run([compiler, '/nologo', '/c', '/O2', '/MT', '/EHsc', '/DWIN32_LEAN_AND_MEAN', '/DDETOUR_DEBUG=0', '/Fo' + str(obj), detours / (name + '.cpp')], environment, name + '.log', commands)
        objects.append(obj)
    library = OUTPUT / 'detours.lib'
    run([librarian, '/NOLOGO', '/OUT:' + str(library), *objects], environment, 'library.log', commands)
    loader_objects = []
    for name in ('dllmain', 'proxy'):
        obj = OUTPUT / (name + '.obj')
        run([compiler, '/nologo', '/c', '/std:c++17', '/O2', '/MT', '/W4', '/EHsc', '/I' + str(ROOT), '/I' + str(detours), '/Fo' + str(obj), ROOT / (name + '.cpp')], environment, name + '.log', commands)
        loader_objects.append(obj)
    artifact = OUTPUT / 'xinput1_4.dll'
    run([linker, '/NOLOGO', '/DLL', '/MACHINE:X64', '/INCREMENTAL:NO', '/DYNAMICBASE', '/Brepro', '/NXCOMPAT', '/OPT:REF', '/OUT:' + str(artifact), *loader_objects, library, 'kernel32.lib', 'psapi.lib'], environment, 'link.log', commands)
    run([dumper, '/NOLOGO', '/HEADERS', '/EXPORTS', '/DEPENDENTS', artifact], environment, 'pe_inspection.txt', commands)
    inspection = (OUTPUT / 'pe_inspection.txt').read_text(encoding='utf-8')
    exports = sorted([[int(ordinal), name] for ordinal, name in re.findall(r'^\s*(\d+)\s+[0-9A-F]+\s+[0-9A-F]{8}\s+(\w+)\s*$', inspection, re.MULTILINE)])
    expected = [[2, 'XInputGetState'], [3, 'XInputSetState'], [4, 'XInputGetCapabilities'], [5, 'XInputEnable'], [7, 'XInputGetBatteryInformation'], [8, 'XInputGetKeystroke'], [10, 'XInputGetAudioDeviceIds']]
    if exports != expected:
        raise ValueError('XInput export contract differs: ' + repr(exports))
    dependencies = re.findall(r'^\s+([A-Za-z0-9_.-]+\.dll)\s*$', inspection, re.MULTILINE | re.IGNORECASE)
    if not dependencies or set(name.lower() for name in dependencies) - {'kernel32.dll', 'psapi.dll'}:
        raise ValueError('Unexpected loader dependencies: ' + repr(dependencies))
    dll = artifact.read_bytes()
    verify_licenses(dll)
    report = dict(fork_repository='https://github.com/RovingAimer/sora1looseload',
        upstream_commit=UPSTREAM, detours_commit=DETOURS, source_git=git_info(), sources=sources,
        compiler=compiler, compiler_version=compiler_version,
        sdk_root=str(args.sdk_root.resolve()) if args.sdk_root else None,
        sdk_version=environment.get('WindowsSDKVersion'),
        include_paths=environment.get('INCLUDE'), library_paths=environment.get('LIB'), commands=commands,
        build_flags=['/O2', '/MT', '/W4', '/Brepro'], exports=exports, export_contract_match=True,
        dependencies=dependencies, embedded_licenses_verified=True,
        dll_sha256=hashlib.sha256(dll).hexdigest(), dll_bytes=len(dll),
        game_runtime_verified=False, dll_executed=False, game_directory_written=False,
        integration='INI-declared API 1 modules in immediate mods subdirectories')
    (OUTPUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'artifact': str(artifact), 'sha256': report['dll_sha256'], 'source_git': report['source_git']}))


if __name__ == '__main__':
    main()
