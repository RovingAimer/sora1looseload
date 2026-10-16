"""Publish verified installation assets declared in this repository's release plan."""
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
        raise ValueError('Release repository differs from the plan')
    token = os.environ['GH_TOKEN']
    api = 'https://api.github.com/repos/' + repository

    def request(url, method='GET', payload=None, binary=None):
        data = binary if binary is not None else (json.dumps(payload).encode('utf-8') if payload is not None else None)
        headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                   'User-Agent': 'SoraMod-release', 'X-GitHub-Api-Version': '2022-11-28'}
        if data is not None:
            headers['Content-Type'] = 'application/zip' if binary is not None else 'application/json'
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=90) as response:
            return json.load(response)

    for name, expected in plan['source_hashes_lf'].items():
        actual = hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        if actual != expected:
            raise ValueError('Compiled source differs: ' + name)
    assets = []
    for asset in plan['assets']:
        blob = request(api + '/git/blobs/' + asset['blob_sha'])
        data = base64.b64decode(blob['content'])
        if hashlib.sha256(data).hexdigest() != asset['sha256']:
            raise ValueError('Installation ZIP hash differs: ' + asset['name'])
        with ZipFile(io.BytesIO(data)) as archive:
            if archive.testzip() is not None or sorted(archive.namelist()) != sorted(asset['entries']):
                raise ValueError('Installation ZIP contents differ: ' + asset['name'])
        assets.append((asset, data))
    tag = plan['tag']
    commit = os.environ['GITHUB_SHA']
    try:
        release = request(api + '/releases/tags/' + quote(tag, safe=''))
    except HTTPError as error:
        if error.code != 404:
            raise
        drafts = request(api + '/releases?per_page=100')
        release = next((item for item in drafts if item['tag_name'] == tag), None)
        if release is None:
            body = plan['body'] + '\n\n源码提交：`' + commit + '`\n\nSHA256：\n'
            body += '\n'.join('- `' + asset['name'] + '`: `' + asset['sha256'] + '`' for asset, _ in assets)
            release = request(api + '/releases', 'POST', dict(tag_name=tag, target_commitish=commit,
                name=plan['name'], body=body, draft=True, prerelease=False))
    if release['target_commitish'] not in (commit, 'main'):
        raise ValueError('Existing release points to another commit')
    existing = {item['name']: item for item in release.get('assets', [])}
    for asset, data in assets:
        if asset['name'] in existing:
            old = existing[asset['name']]
            if old.get('digest') != 'sha256:' + asset['sha256']:
                raise ValueError('Existing asset has another hash: ' + asset['name'])
            continue
        uploaded = request(release['upload_url'].split('{')[0] + '?name=' + quote(asset['name']),
                           'POST', binary=data)
        if uploaded.get('digest') != 'sha256:' + asset['sha256']:
            raise ValueError('Uploaded asset hash differs: ' + asset['name'])
    release = request(api + '/releases/' + str(release['id']), 'PATCH', dict(draft=False, prerelease=False))
    print(release['html_url'])


if __name__ == '__main__':
    main()
