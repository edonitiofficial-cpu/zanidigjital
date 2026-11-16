"""Use source-provided image sizes when verified, proxy variants otherwise."""
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode,quote
from news_utils import safe_url


def photo_variant(value,width):
    original=safe_url(value)
    if not original:
        return '/zanidigjitalfavicon.png'
    parsed=urlsplit(original)
    query=parse_qsl(parsed.query,keep_blank_values=True)
    if parsed.hostname in ('telegrafi.com','www.telegrafi.com') and parsed.path.startswith('/media-library/') and any(key=='width' for key,_ in query):
        query=[(key,str(width) if key=='width' else value) for key,value in query]
        return urlunsplit(parsed._replace(query=urlencode(query)))
    return 'https://wsrv.nl/?url='+quote(original,safe='')+f'&w={width}&output=webp&q=80'
