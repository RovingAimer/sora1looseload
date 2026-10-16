"""Build this fork offline; never install or execute a game or produced DLL.
MIT; original loader Copyright (c) 2025 Hinkiii.
Build and integration additions Copyright (c) 2026 DialogueOutline contributors.
"""
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


def compiler_environment():
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
    environment.update(TEMP=str(OUTPUT), TMP=str(OUTPUT))
    return environment


def run(arguments, environment, log):
    result = subprocess.run([str(value) for value in arguments], cwd=OUTPUT, env=environment,
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    (OUTPUT / log).write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'{Path(arguments[0]).name} failed; see {OUTPUT / log}')



def git_info():
    if not (ROOT / '.git').exists():
        return {'commit': None, 'dirty': None}
    command = ['git', '-c', 'safe.directory=' + ROOT.as_posix()]
    commit = subprocess.check_output(command + ['rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(command + ['status', '--porcelain'], cwd=ROOT, text=True).strip())
    return dict(commit=commit, dirty=dirty)


def main():
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / 'report.json').unlink(missing_ok=True)
    detours = ROOT / 'external/detours/src'
    if not (detours / 'detours.cpp').is_file():
        raise RuntimeError('Missing Detours source: clone with --recursive or use the complete source archive')
    names = ['detours', 'modules', 'disasm', 'image', 'creatwth', 'disolx86', 'disolx64', 'disolia64', 'disolarm', 'disolarm64']
    inputs = [ROOT / name for name in ('build.py', 'dllmain.cpp', 'proxy.cpp', 'pch.h', 'framework.h', 'dialogue_outline_loader.h')]
    inputs += sorted(path for path in detours.iterdir() if path.suffix in ('.h', '.cpp'))
    sources = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    environment = compiler_environment()
    locate = lambda name: shutil.which(name, path=environment['PATH'])
    compiler, librarian, linker, dumper = map(locate, ('cl.exe', 'lib.exe', 'link.exe', 'dumpbin.exe'))
    if not all((compiler, librarian, linker, dumper)):
        raise RuntimeError('Incomplete MSVC x64 toolchain')
    objects = []
    for name in names:
        obj = OUTPUT / (name + '.obj')
        run([compiler, '/nologo', '/c', '/O2', '/MT', '/EHsc', '/DWIN32_LEAN_AND_MEAN', '/DDETOUR_DEBUG=0', '/Fo' + str(obj), detours / (name + '.cpp')], environment, name + '.log')
        objects.append(obj)
    library = OUTPUT / 'detours.lib'
    run([librarian, '/NOLOGO', '/OUT:' + str(library), *objects], environment, 'library.log')
    loader_objects = []
    for name in ('dllmain', 'proxy'):
        obj = OUTPUT / (name + '.obj')
        run([compiler, '/nologo', '/c', '/std:c++17', '/O2', '/MT', '/W4', '/EHsc', '/I' + str(ROOT), '/I' + str(detours), '/Fo' + str(obj), ROOT / (name + '.cpp')], environment, name + '.log')
        loader_objects.append(obj)
    artifact = OUTPUT / 'xinput1_4.dll'
    run([linker, '/NOLOGO', '/DLL', '/MACHINE:X64', '/INCREMENTAL:NO', '/DYNAMICBASE', '/Brepro', '/NXCOMPAT', '/OPT:REF', '/OUT:' + str(artifact), *loader_objects, library, 'kernel32.lib', 'psapi.lib'], environment, 'link.log')
    run([dumper, '/NOLOGO', '/HEADERS', '/EXPORTS', '/DEPENDENTS', artifact], environment, 'pe_inspection.txt')
    inspection = (OUTPUT / 'pe_inspection.txt').read_text(encoding='utf-8')
    exports = sorted([[int(ordinal), name] for ordinal, name in re.findall(r'^\s*(\d+)\s+[0-9A-F]+\s+[0-9A-F]{8}\s+(\w+)\s*$', inspection, re.MULTILINE)])
    expected = [[2, 'XInputGetState'], [3, 'XInputSetState'], [4, 'XInputGetCapabilities'], [5, 'XInputEnable'], [7, 'XInputGetBatteryInformation'], [8, 'XInputGetKeystroke'], [10, 'XInputGetAudioDeviceIds']]
    if exports != expected:
        raise ValueError('XInput export contract differs: ' + repr(exports))
    report = dict(fork_repository='https://github.com/RovingAimer/sora1looseload', upstream_commit=UPSTREAM, detours_commit=DETOURS, source_git=git_info(), sources=sources, compiler=compiler, build_flags=['/O2', '/MT', '/W4', '/Brepro'], exports=exports, export_contract_match=True, dll_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(), dll_bytes=artifact.stat().st_size, game_runtime_verified=False, dll_executed=False, game_directory_written=False, integration='Fixed DialogueOutline module entry, not a generic plugin framework')
    (OUTPUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'artifact': str(artifact), 'sha256': report['dll_sha256'], 'source_git': report['source_git']}))


if __name__ == '__main__':
    main()
