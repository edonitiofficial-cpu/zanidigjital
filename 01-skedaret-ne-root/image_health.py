"""Bounded, cached photo inspection. Never alters articles or treats a timeout as loss."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, UnidentifiedImageError
from news_utils import safe_url, write_json_atomic
from photo_utils import photo_variant

MAX_BYTES = 5 * 1024 * 1024


def probe(url, opener=urlopen):
    try:
        request = Request(url, headers={'User-Agent': 'ZaniDigjital/1.0 photo-check', 'Accept': 'image/*'})
        with opener(request, timeout=6) as response:
            payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            return 'unverified', 'size_limit'
        with Image.open(BytesIO(payload)) as picture:
            if picture.width < 120 or picture.height < 80:
                return 'broken', 'too_small'
            picture.verify()
        return 'ok', 'decoded'
    except HTTPError as error:
        return ('broken', 'not_found') if error.code in (404, 410) else ('unverified', 'source_unavailable')
    except (UnidentifiedImageError, SyntaxError, ValueError):
        return 'broken', 'invalid_image'
    except (OSError, URLError, Image.DecompressionBombError):
        return 'unverified', 'source_unavailable'


def inspect_photo(item, check=probe):
    optimized = photo_variant(item['url'], 768)
    status, reason = check(optimized)
    if status == 'ok':
        return dict(item, status='ok', reason='optimized_ok')
    original_status, original_reason = check(item['url'])
    if original_status == 'ok':
        return dict(item, status='fallback', reason='original_ok')
    # A blocked proxy cannot confirm loss; only the source can confirm 404/invalid bytes.
    return dict(item, status=original_status, reason=original_reason)


def audit_photos(articles, path='image-health.json', limit=5, check=probe, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        previous = json.loads(Path(path).read_text(encoding='utf-8')).get('images', [])
    except (OSError, ValueError, AttributeError):
        previous = []
    cached = {item['url']: item for item in previous if isinstance(item, dict) and item.get('url')}
    candidates = {}
    for article in articles[:150]:
        photos = [('main', article.get('imazhi'))]
        photos += [('inline', b.get('url') or b.get('src')) for b in article.get('content_blocks', []) if b.get('type') == 'image'][:2]
        for role, raw in photos:
            url = safe_url(raw)
            if url and not url.endswith('/zanidigjitalfavicon.png'):
                candidates.setdefault(url, dict(url=url, slug=article.get('slug', ''), title=str(article.get('titulli', ''))[:350], role=role))
    pending = []
    results = []
    for url, item in candidates.items():
        saved = cached.get(url)
        try:
            elapsed = (now - datetime.fromisoformat(saved['checked_at'])).total_seconds()
        except (KeyError, TypeError, ValueError):
            elapsed = float('inf')
        ttl = 3600 if saved and saved.get('status') == 'unverified' else 21600
        if elapsed >= ttl and len(pending) < limit:
            pending.append(item)
        elif saved:
            results.append(dict(saved, **item))
    with ThreadPoolExecutor(max_workers=3) as pool:
        checked = list(pool.map(lambda item: inspect_photo(item, check), pending))
    results += [dict(item, checked_at=now.isoformat()) for item in checked]
    counts = dict(Counter(item['status'] for item in results))
    report = dict(schema_version=1, updated_at=now.isoformat(), checked_this_run=len(checked),
                  pending=max(0, len(candidates)-len(results)), counts=counts, images=results[:450])
    write_json_atomic(path, report)
    print('Photo check: ' + ', '.join(f'{key}={value}' for key, value in sorted(counts.items())))
    return {key: report[key] for key in ('checked_this_run', 'pending', 'counts')}
