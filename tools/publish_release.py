"""Publish installation assets and first-release notes from the reviewed plan."""
# Copyright (c) 2026 DialogueOutline contributors. SPDX-License-Identifier: MIT
import base64
import hashlib
import io
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main():
    plan = json.loads((ROOT / 'release_plan.json').read_text(encoding='utf-8'))
    repository = os.environ['GITHUB_REPOSITORY']
    if repository != plan['repository']:
        raise ValueError('Repository differs from release plan')
    api = 'https://api.github.com/repos/' + repository
    token = os.environ['GH_TOKEN']

    def request(path, method='GET', payload=None, binary=None):
        url = path if path.startswith('https://') else api + path
        data = binary if binary is not None else (json.dumps(payload).encode() if payload is not None else None)
        headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                   'User-Agent': 'SoraMod-release', 'X-GitHub-Api-Version': '2022-11-28'}
        if data is not None:
            headers['Content-Type'] = 'application/zip' if binary is not None else 'application/json'
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=90) as response:
            return None if response.status == 204 else json.load(response)

    def optional(path):
        try:
            return request(path)
        except HTTPError as error:
            if error.code != 404:
                raise
            return None

    for name, expected in plan['source_hashes_lf'].items():
        if hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise ValueError('Compiled source differs: ' + name)
    assets = []
    for asset in plan['assets']:
        blob = request('/git/blobs/' + asset['blob_sha'])
        data = base64.b64decode(blob['content'])
        if hashlib.sha256(data).hexdigest() != asset['sha256']:
            raise ValueError('Installation ZIP hash differs: ' + asset['name'])
        with ZipFile(io.BytesIO(data)) as archive:
            if archive.testzip() is not None or sorted(archive.namelist()) != sorted(asset['entries']):
                raise ValueError('Installation ZIP contents differ: ' + asset['name'])
        assets.append((asset, data))

    # Keep superseded candidate attachments in an unpublished draft.
    for old in plan.get('hide_releases', []):
        release = request('/releases/' + str(old['id']))
        if release['tag_name'] != old['tag']:
            raise ValueError('Candidate release changed')
        if not release['draft']:
            request('/releases/' + str(old['id']), 'PATCH', {'draft': True})

    tag = plan['tag']
    commit = os.environ['GITHUB_SHA']
    replacement = plan.get('replace_release')
    if replacement:
        release = request('/releases/' + str(replacement['id']))
        if release['tag_name'] not in (tag, replacement['old_tag']):
            raise ValueError('Release to correct changed')
        if release['tag_name'] == replacement['old_tag'] and release['target_commitish'] != replacement['old_commit']:
            raise ValueError('Previous release source changed')
    else:
        release = optional('/releases/tags/' + quote(tag, safe=''))

    ref = optional('/git/ref/tags/' + quote(tag, safe=''))
    if ref is None:
        request('/git/refs', 'POST', {'ref': 'refs/tags/' + tag, 'sha': commit})
    elif ref['object']['sha'] != commit:
        raise ValueError('Release tag points to another commit')

    body = plan['body'] + '\n\n<details>\n<summary>源码版本与文件校验</summary>\n\n'
    body += '源码提交：`' + commit + '`\n\nSHA256：\n\n'
    body += '\n'.join('- `' + asset['name'] + '`: `' + asset['sha256'] + '`' for asset, _ in assets)
    body += '\n\n</details>'
    if release is None:
        release = request('/releases', 'POST', {'tag_name': tag, 'target_commitish': commit,
            'name': plan['name'], 'body': body, 'draft': True, 'prerelease': False})
    elif replacement and release['tag_name'] == replacement['old_tag']:
        release = request('/releases/' + str(release['id']), 'PATCH', {'draft': True})

    existing = {item['name']: item for item in release.get('assets', [])}
    for asset, data in assets:
        previous = asset.get('previous_name', asset['name'])
        old = existing.get(asset['name']) or existing.get(previous)
        if old:
            if old.get('digest') != 'sha256:' + asset['sha256']:
                raise ValueError('Existing asset hash differs: ' + old['name'])
            request('/releases/assets/' + str(old['id']), 'PATCH',
                    {'name': asset['name'], 'label': asset.get('label', '')})
        else:
            uploaded = request(release['upload_url'].split('{')[0] + '?name=' + quote(asset['name']), 'POST', binary=data)
            if uploaded.get('digest') != 'sha256:' + asset['sha256']:
                raise ValueError('Uploaded asset hash differs')
    current = request('/releases/' + str(release['id']) + '/assets')
    if {a['name'] for a in current} != {a['name'] for a, _ in assets}:
        raise ValueError('Release installation asset set differs')
    release = request('/releases/' + str(release['id']), 'PATCH', {'tag_name': tag,
        'target_commitish': commit, 'name': plan['name'], 'body': body, 'draft': False,
        'prerelease': False, 'make_latest': 'true'})

    if replacement and replacement['old_tag'] != tag:
        path = '/git/ref/tags/' + quote(replacement['old_tag'], safe='')
        old_ref = optional(path)
        if old_ref:
            if old_ref['object']['sha'] != replacement['old_commit']:
                raise ValueError('Old tag changed; retained')
            request('/git/refs/tags/' + quote(replacement['old_tag'], safe=''), 'DELETE')
    print(release['html_url'])


if __name__ == '__main__':
    main()
