"""Request a Pages build after a successful push; never log the workflow token."""
import json
import os
import re
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen


def request_build(repository,token,opener=urlopen):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository) or not token:
        raise ValueError('Mungon repository ose token-i i workflow-t.')
    req=Request(f'https://api.github.com/repos/{repository}/pages/builds',data=b'{}',method='POST',headers={
        'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,
        'Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'ZaniDigjital-workflow',
    })
    try:
        with opener(req,timeout=30) as response:
            data=json.load(response)
        print('GitHub Pages: u kërkua ndërtimi i versionit të fundit.')
        return data.get('status')
    except HTTPError as error:
        raise RuntimeError(f'GitHub Pages nuk e pranoi nisjen: HTTP {error.code}. Kontrollo lejen pages:write dhe konfigurimin Pages.') from None
    except URLError:
        raise RuntimeError('Nisja e GitHub Pages dështoi nga lidhja e rrjetit.') from None


if __name__=='__main__':request_build(os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_TOKEN',''))
