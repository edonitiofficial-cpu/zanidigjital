"""Build only derived presentation files from this repository's current news."""
import os
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from news_utils import load_news_file,news_metadata
from archive_output import create_archive
from homepage_output import render_homepage


def prepare(root):
    root=Path(root)
    archive=root/'news-index.json'
    if not archive.exists():archive=root/'lajmet.json'
    if not archive.exists():raise FileNotFoundError('Mungon arkivi aktual i repository-t.')
    current=news_metadata(load_news_file(archive))
    if not current:raise ValueError('Arkivi aktual është bosh; përgatitja u ndal.')
    homepage=load_news_file(root/'ballina.json') if (root/'ballina.json').exists() else current[:150]
    if not homepage:raise ValueError('Ballina aktuale është bosh; përgatitja u ndal.')
    pages=create_archive(current,root)
    render_homepage(homepage,root/'index.html')
    page=root/'index.html'
    text=page.read_text(encoding='utf-8')
    if 'data-static-news="true"' not in text:
        text=text.replace('<div id="bento-grid"','<div id="bento-grid" data-static-news="true"',1)
        page.write_text(text,encoding='utf-8')
    print(f'Pamja u përgatit nga {len(current)} lajme aktuale; {pages} faqe katalogu. Arkivi dhe artikujt nuk u rishkruan.')


if __name__=='__main__':prepare(root)
