"""Mirror the lead photo's existing WebP variants to remove a fragile critical hop."""
import hashlib
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import quote
from urllib.request import Request,urlopen
from news_utils import safe_url


def cached_photo(article):
    cached=article.get('hero_image',{})
    if not isinstance(cached,dict):
        return None
    if cached.get('source') != safe_url(article.get('imazhi')):
        return None
    if not all(re.fullmatch(r'/news-images/[a-f0-9]{16}-(?:480|1000)\.webp',cached.get(key,'')) for key in ('small','large')):
        return None
    return cached


def fetch_variant(url):
    with urlopen(Request(url,headers={'User-Agent':'ZaniDigjital/1.0'}),timeout=12) as response:
        if response.headers.get_content_type() != 'image/webp':
            raise ValueError('Not a WebP image')
        return response.read(2*1024*1024+1)


def cache_lead_photo(article,root='.',fetch=fetch_variant):
    original=safe_url(article.get('imazhi'))
    if not original:
        return False
    folder=Path(root)/'news-images';folder.mkdir(exist_ok=True)
    digest=hashlib.sha256(original.encode()).hexdigest()[:16]
    paths={}
    try:
        for key,width in [('small',480),('large',1000)]:
            name=f'{digest}-{width}.webp';target=folder/name
            if not target.exists():
                data=fetch('https://wsrv.nl/?url='+quote(original,safe='')+f'&w={width}&output=webp&q=80')
                if len(data)>2*1024*1024 or len(data)<12 or data[:4]!=b'RIFF' or data[8:12]!=b'WEBP':
                    raise ValueError('Invalid WebP payload')
                fd,temporary=tempfile.mkstemp(dir=folder,prefix='.news-',suffix='.tmp')
                try:
                    with os.fdopen(fd,'wb') as stream:stream.write(data)
                    os.replace(temporary,target)
                finally:
                    if os.path.exists(temporary):os.unlink(temporary)
            paths[key]='/news-images/'+name
        article['hero_image']=dict(source=original,**paths)
        return True
    except (OSError,ValueError):
        print('Lead photo mirror unavailable; original image fallback retained.')
        return False
