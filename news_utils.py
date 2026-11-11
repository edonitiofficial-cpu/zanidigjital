"""Pure helpers shared by the bot and its checks; no network or API keys."""
import json
import os
import re
import tempfile
from itertools import zip_longest
from urllib.parse import urlsplit


def slugify(title):
    slug = str(title or '').lower().replace('ë', 'e').replace('ç', 'c')
    slug = re.sub(r'[^a-z0-9 -]', '', slug)
    return re.sub(r'-+', '-', re.sub(r'\s+', '-', slug)).strip('-')


def safe_url(value):
    value = str(value or '').strip()
    try:
        parsed = urlsplit(value)
    except ValueError:
        return ''
    return value if parsed.scheme in ('http', 'https') and parsed.netloc else ''


def write_json_atomic(path, data, indent=None):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=directory, prefix='.news-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=indent)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_news_file(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as stream:
        data = json.load(stream)
    if not isinstance(data, list) or any(not isinstance(n, dict) for n in data):
        raise ValueError('Arkivi i lajmeve duhet të jetë listë artikujsh.')
    return data


def news_metadata(items):
    keys = ('titulli', 'kategoria', 'imazhi', 'koha', 'published_at', 'slug', 'eshte_balline', 'komunat', 'featured_rank', 'selection_reasons', 'source_count')
    return [{key: n[key] for key in keys if key in n} for n in items if n.get('slug') and n.get('titulli') and not n.get('duplicate_of')]


def interleave_feeds(feeds):
    """Take one candidate per source per round, newest first within each source."""
    def timestamp(entry):
        return entry.get('published_parsed') or entry.get('updated_parsed') or (0,) * 9
    ordered = [sorted(entries, key=timestamp, reverse=True) for entries in feeds]
    for row in zip_longest(*ordered):
        for entry in row:
            if entry is not None:
                yield entry


def facebook_queue_path():
    return os.path.join(os.environ.get('RUNNER_TEMP', tempfile.gettempdir()), 'zani-facebook-queue.json')
