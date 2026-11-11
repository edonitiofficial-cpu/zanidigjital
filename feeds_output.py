"""XML writers use an XML library, so feed titles and URLs stay well formed."""
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET
from news_time import news_now


def create_rss(items):
    root = ET.Element('rss', version='2.0')
    channel = ET.SubElement(root, 'channel')
    for name, text in [('title', 'Zani Digjital'), ('link', 'https://zanidigjital.com/'),
                       ('description', 'Lajmet e fundit nga Zani Digjital'), ('language', 'sq')]:
        ET.SubElement(channel, name).text = text
    for news in [n for n in items if not n.get('duplicate_of')][:30]:
        if not news.get('slug'):
            continue
        item = ET.SubElement(channel, 'item')
        url = 'https://zanidigjital.com/lajme/' + quote(news['slug'], safe='-') + '/'
        ET.SubElement(item, 'title').text = news.get('titulli', '')
        ET.SubElement(item, 'link').text = url
        ET.SubElement(item, 'guid', isPermaLink='true').text = url
        ET.SubElement(item, 'description').text = news.get('permbajtja', '')[:200]
        if news.get('published_at'):
            date = datetime.fromisoformat(news['published_at'].replace('Z', '+00:00'))
            ET.SubElement(item, 'pubDate').text = format_datetime(date)
    ET.ElementTree(root).write('rss.xml', encoding='utf-8', xml_declaration=True)


def create_sitemap(items):
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', namespace)
    root = ET.Element(f'{{{namespace}}}urlset')
    dates = {}
    for news in items:
        if news.get('slug'):
            try:
                dates[news['slug']] = datetime.strptime(news['koha'], '%d/%m/%Y %H:%M').date().isoformat()
            except (ValueError, KeyError, TypeError):
                pass
    locations = [('https://zanidigjital.com/', news_now().date().isoformat())]
    # Keep historic articles discoverable even after they leave the JSON archive.
    for path in sorted(Path('lajme').glob('*/index.html')):
        slug = path.parent.name
        locations.append(('https://zanidigjital.com/lajme/' + quote(slug, safe='-') + '/', dates.get(slug)))
    for url, modified in locations:
        entry = ET.SubElement(root, f'{{{namespace}}}url')
        ET.SubElement(entry, f'{{{namespace}}}loc').text = url
        if modified:
            ET.SubElement(entry, f'{{{namespace}}}lastmod').text = modified
    ET.ElementTree(root).write('sitemap.xml', encoding='utf-8', xml_declaration=True)
