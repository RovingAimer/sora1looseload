"""Validate and preview prepared packages; network publication requires --publish."""
# Copyright (c) 2026 DialogueOutline contributors
# Copyright (c) 2026 SoraMod contributors
# SPDX-License-Identifier: MIT
import argparse
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return sha256(data).hexdigest()


def validate_packages(folder, plan):
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['version'] != plan['version'] or manifest['repository'] != plan['repository']:
        raise ValueError('Packages differ from the current release plan')
    source_git = manifest['source_git']
    commit = source_git['commit']
    if not re.fullmatch(r'[0-9a-f]{40}', commit or '') or source_git['dirty'] is not False:
        raise ValueError('Packages must identify a committed clean source snapshot')
    if (ROOT / '.git').exists():
        current = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        if current != commit:
            raise ValueError('Check out the prepared package source commit before publishing')
    version = plan['version']
    expected = {'installation': f'sora1looseload-v{version}.zip',
                'source': f'sora1looseload-v{version}-source.zip'}
    if len(manifest['artifacts']) != 2 or {asset['kind']: asset['file'] for asset in manifest['artifacts']} != expected:
        raise ValueError('Expected exactly the current installation and complete source ZIPs')
    assets, contents = [], {}
    for asset in manifest['artifacts']:
        data = (folder / asset['file']).read_bytes()
        if digest(data) != asset['sha256'] or len(data) != asset['bytes']:
            raise ValueError('Prepared ZIP hash or size differs: ' + asset['file'])
        with ZipFile(io.BytesIO(data)) as zipped:
            members = asset['members']
            if zipped.testzip() is not None or sorted(zipped.namelist()) != sorted(item['path'] for item in members):
                raise ValueError('Prepared ZIP members differ: ' + asset['file'])
            files = {name: zipped.read(name) for name in zipped.namelist()}
            for member in members:
                payload = files[member['path']]
                if digest(payload) != member['sha256'] or len(payload) != member['bytes']:
                    raise ValueError('ZIP member differs: ' + member['path'])
        assets.append((asset, data))
        contents[asset['kind']] = files
    installation, sources = contents['installation'], contents['source']
    if set(installation) != {'xinput1_4.dll', 'mods/DialogueOutline/sora_mod.ini'}:
        raise ValueError('Installation ZIP must contain only the loader and subtitle declaration')
    if digest(installation['xinput1_4.dll']) != manifest['dll_sha256']:
        raise ValueError('Installation DLL differs from manifest')
    if installation['mods/DialogueOutline/sora_mod.ini'] != sources['mods/DialogueOutline/sora_mod.ini']:
        raise ValueError('Installed module declaration differs from the source snapshot')
    snapshot = json.loads(sources['SOURCE_MANIFEST.json'])
    if snapshot['source_git'] != source_git or set(snapshot['files']) != set(sources) - {'SOURCE_MANIFEST.json'}:
        raise ValueError('Complete source snapshot differs from manifest')
    for name, expected_hash in snapshot['files'].items():
        if digest(sources[name]) != expected_hash:
            raise ValueError('Source snapshot member differs: ' + name)
    if json.loads(sources['release_plan.json']) != plan:
        raise ValueError('Release plan differs from the prepared source snapshot')
    report = manifest['native_build_report']
    if report['dll_sha256'] != manifest['dll_sha256'] or snapshot['detours_commit'] != report['detours_commit']:
        raise ValueError('Build report differs from prepared packages')
    report_bytes = (folder / 'build-report.json').read_bytes()
    if digest(report_bytes) != manifest['native_build_report_sha256'] or json.loads(report_bytes) != report:
        raise ValueError('Native build report hash differs')
    for name, expected_hash in report['sources'].items():
        if name not in sources or digest(sources[name]) != expected_hash:
            raise ValueError('Source archive does not cover the compiled input: ' + name)
    return manifest, assets


def publish(plan, manifest, assets, body):
    repository = os.environ.get('GITHUB_REPOSITORY', plan['repository'])
    if repository != plan['repository']:
        raise ValueError('Repository differs from release plan')
    api = 'https://api.github.com/repos/' + repository
    token = os.environ.get('GH_TOKEN') or os.environ['GITHUB_TOKEN']

    def request(path, method='GET', payload=None, binary=None):
        url = path if path.startswith('https://') else api + path
        data = binary if binary is not None else (json.dumps(payload).encode() if payload is not None else None)
        headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                   'User-Agent': 'SoraMod-release', 'X-GitHub-Api-Version': '2022-11-28'}
        if data is not None:
            headers['Content-Type'] = 'application/zip' if binary is not None else 'application/json'
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=90) as response:
            return json.load(response)

    def optional(path):
        try:
            return request(path)
        except HTTPError as error:
            if error.code != 404:
                raise
            return None

    tag = 'v' + plan['version']
    commit = manifest['source_git']['commit']
    ref = optional('/git/ref/tags/' + quote(tag, safe=''))
    if ref and ref['object']['sha'] != commit:
        raise ValueError('Existing release tag points to another commit; retained')
    release = optional('/releases/tags/' + quote(tag, safe=''))
    if release is not None and release['target_commitish'] != commit and ref is None:
        raise ValueError('Existing draft targets another source commit; retained')
    expected_assets = {asset['file']: asset for asset, _ in assets}
    existing = {item['name']: item for item in release.get('assets', [])} if release else {}
    if set(existing) - set(expected_assets):
        raise ValueError('Existing release has other attachments; retained')
    for name, old in existing.items():
        if old.get('digest') != 'sha256:' + expected_assets[name]['sha256']:
            raise ValueError('Same-named attachment has different content; retained: ' + name)
    title = tag + ' · ' + plan['name']
    if release is None:
        release = request('/releases', 'POST', {'tag_name': tag, 'target_commitish': commit,
            'name': title, 'body': body, 'draft': True, 'prerelease': False})
    for asset, data in assets:
        if asset['file'] not in existing:
            uploaded = request(release['upload_url'].split('{')[0] + '?name=' + quote(asset['file']),
                               'POST', binary=data)
            if uploaded.get('digest') != 'sha256:' + asset['sha256']:
                raise ValueError('Uploaded attachment hash differs; draft retained')
    current = request('/releases/' + str(release['id']) + '/assets')
    if {item['name']: item.get('digest') for item in current} != {
            asset['file']: 'sha256:' + asset['sha256'] for asset, _ in assets}:
        raise ValueError('Release attachment set or hashes differ; draft retained')
    release = request('/releases/' + str(release['id']), 'PATCH', {'tag_name': tag,
        'target_commitish': commit, 'name': title, 'body': body, 'draft': False,
        'prerelease': False, 'make_latest': 'true'})
    print(release['html_url'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages', type=Path, default=ROOT / 'build/packages')
    parser.add_argument('--publish', action='store_true', help='Publish the verified, accepted packages to GitHub')
    args = parser.parse_args()
    plan = json.loads((ROOT / 'release_plan.json').read_text(encoding='utf-8'))
    manifest, assets = validate_packages(args.packages, plan)
    body = plan['body'].replace('{version}', plan['version'])
    body += '\n\n<details>\n<summary>源码版本与文件校验</summary>\n\n'
    body += '源码提交：`' + manifest['source_git']['commit'] + '`\n\nSHA256：\n\n'
    body += '\n'.join('- `' + asset['file'] + '`: `' + asset['sha256'] + '`' for asset, _ in assets)
    body += '\n\n</details>'
    if args.publish:
        publish(plan, manifest, assets, body)
    else:
        print('Validated local packages. Preview only; use --publish after final acceptance.\n')
        print(body)


if __name__ == '__main__':
    main()
