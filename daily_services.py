"""Evening public-service collection, independent of AI and news publication."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from news_time import NEWS_TIMEZONE, news_now
from news_utils import write_json_atomic

KEDS_URL = 'https://www.keds-energy.com/shq/punime-ne-rrjet/njoftime-per-punime-ne-rrjet/'
METEO_URL = 'https://www.meteokosova.com/'
DATA_FILE = Path('daily-services.json')


def request(url, data=None):
    req = urllib.request.Request(url, data=data, headers={
        'User-Agent': 'ZaniDigjital/1.0 (+https://zanidigjital.com)',
        'Accept': 'application/json, application/xml, text/html',
    })
    with urllib.request.urlopen(req, timeout=25) as response:
        if data is not None and response.headers.get_content_type() != 'application/json':
            raise ValueError('Unexpected KEDS response type')
        return response.read().decode('utf-8-sig')


def plain_text(markup):
    markup = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', markup, flags=re.I | re.S)
    markup = re.sub(r'</(?:p|div|li|tr|h[1-6])\s*>|<br\s*/?>', '\n', markup, flags=re.I)
    markup = unescape(re.sub(r'<[^>]+>', '', markup))
    return '\n'.join(' '.join(line.split()) for line in markup.splitlines() if line.strip())


def collect_keds(now, fetch=request):
    page = fetch(KEDS_URL)
    regions = re.findall(r'<li\b[^>]*data-districtid="(\d+)"[^>]*>(.*?)</li>', page, re.S)
    if len(regions) != 7 or 'GetNetworkWorksByFilters' not in page:
        raise ValueError('KEDS page structure changed')
    regions = [(region_id, plain_text(name)) for region_id, name in regions]
    dates = [(now.date() + timedelta(days=offset)).isoformat() for offset in range(1, 5)]

    def collect_pair(pair):
        (region_id, region), date = pair
        day = datetime.fromisoformat(date)
        body = urllib.parse.urlencode(dict(district=region_id, day=day.day, month=day.month, languageId=1)).encode()
        raw = fetch('https://www.keds-energy.com/NetworkWorksFront/GetNetworkWorksByFilters', body)
        # This ASP.NET endpoint returns HTTP 200 application/json with an empty
        # body for absent notices, as well as the literal JSON null.
        result = json.loads(raw) if raw.strip() else None
        text = ''
        if result is not None:
            text = plain_text(result['Description']['Description'])
            if not text:
                raise ValueError('Empty KEDS notice')
            # The endpoint takes no year: reject a notice from a different date/year.
            match = re.search(r'/Date\((\d+)', result.get('Date', ''))
            if not match or datetime.fromtimestamp(int(match[1]) / 1000, NEWS_TIMEZONE).date() != day.date():
                raise ValueError('Unexpected KEDS notice date')
        return dict(region=region, date=date, text=text, status='notice' if text else 'none')

    with ThreadPoolExecutor(max_workers=4) as pool:
        notices = list(pool.map(collect_pair, [(region, date) for date in dates for region in regions]))
    return dict(source_url=KEDS_URL, regions=[name for _, name in regions], dates=dates, notices=notices)


def collect_weather(now, fetch=request):
    root = ET.fromstring(fetch(METEO_URL + 'feed/'))
    forecasts = []
    for item in root.findall('./channel/item'):
        title = plain_text(item.findtext('title', ''))
        # General curiosities and world news are not local forecasts.
        if not title.casefold().startswith('parashikimi i motit'):
            continue
        match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', title)
        if not match:
            continue
        date = datetime.strptime(match[0], '%d.%m.%Y').date()
        link = item.findtext('link', '')
        parsed = urllib.parse.urlsplit(link)
        if parsed.scheme != 'https' or parsed.hostname not in ('www.meteokosova.com', 'meteokosova.com'):
            raise ValueError('Unexpected weather link')
        published = parsedate_to_datetime(item.findtext('pubDate', '')).isoformat()
        description = plain_text(item.findtext('description', '')).split('The post ')[0].strip()
        excerpt = description[:240].rsplit(' ', 1)[0] if len(description) > 240 else description
        forecasts.append(dict(title=title, date=date.isoformat(), url=link,
                              published_at=published, excerpt=excerpt.rstrip(' .…') + '…'))
    if not forecasts:
        raise ValueError('No dated forecasts in feed')
    forecasts.sort(key=lambda item: item['date'], reverse=True)
    return dict(source_url=METEO_URL, forecasts=forecasts[:5])


def update_services(now=None, path=DATA_FILE, force=False, fetch=request):
    now = (now or news_now()).astimezone(NEWS_TIMEZONE)
    evening = (now.hour, now.minute) >= (21, 30)
    if not force and not evening:
        return False
    path = Path(path)
    # A corrupt snapshot must not silently become an empty one.
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'version': 1}
    changed = False
    for key, collector in [('keds', collect_keds), ('weather', collect_weather)]:
        previous = data.get(key, {})
        if not force and previous.get('collected_on') == now.date().isoformat():
            continue
        try:
            # A daytime bootstrap must not suppress tonight's scheduled collection.
            collected_on = now.date().isoformat() if evening else None
            data[key] = dict(collector(now, fetch), status='ok', collected_on=collected_on,
                             updated_at=now.isoformat(), checked_at=now.isoformat())
        except Exception as error:
            data[key] = dict(previous, status='error', checked_at=now.isoformat(), error_type=type(error).__name__)
            print(f'{key}: {type(error).__name__}; retained previous snapshot')
        changed = True
    if changed:
        write_json_atomic(path, data, indent=2)
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Explicit one-off refresh outside evening schedule')
    args = parser.parse_args()
    update_services(force=args.refresh)
