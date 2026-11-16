"""A text-only search catalog plus small, immutable metadata pages."""
import hashlib
import json
from pathlib import Path
from news_utils import news_metadata, write_json_atomic


def create_archive(news, root='.'):
    root = Path(root)
    folder = root / 'news-archive'
    folder.mkdir(exist_ok=True)
    items = news_metadata(news)
    pages, catalog = [], []
    for offset in range(0, len(items), 200):
        batch = items[offset:offset + 200]
        digest = hashlib.sha256(json.dumps(batch, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()[:16]
        target = folder / f'{digest}.json'
        if not target.exists():
            write_json_atomic(target, batch)
        page = len(pages)
        pages.append('/news-archive/' + target.name)
        for n in batch:
            catalog.append([n['slug'], n['titulli'], n.get('kategoria', 'Lajme'),
                            n.get('komunat', []), n.get('published_at'), n.get('koha'), page])
    write_json_atomic(root / 'news-catalog.json', dict(version=1, pages=pages, items=catalog))
    # Retain old immutable pages for readers holding the previous catalog.
    return len(pages)


if __name__ == '__main__':
    from news_utils import load_news_file
    print(f'Archive pages: {create_archive(load_news_file("lajmet.json"))}')
