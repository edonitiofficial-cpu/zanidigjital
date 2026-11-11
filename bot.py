import os
import json
import feedparser
import time
import re
import urllib.request
import urllib.parse
import difflib
import html
import trafilatura
from groq import Groq
from datetime import datetime
from news_time import news_now, parse_publication_time
from news_utils import slugify, safe_url, write_json_atomic, load_news_file, news_metadata, interleave_feeds, facebook_queue_path
from news_policy import find_duplicate, merge_source, select_featured, same_event
from municipalities import enrich_municipalities
from robot_report import RunReport

api_keys = [
    os.environ.get("GROQ_API_KEY"),
    os.environ.get("GROQ_API_KEY_2"),
    os.environ.get("GROQ_API_KEY_3")
]
valid_keys = [key for key in api_keys if key]

current_key_index = 0
client = Groq(api_key=valid_keys[current_key_index], timeout=30.0, max_retries=0) if valid_keys else None

def switch_api_key():
    global current_key_index, client
    current_key_index = (current_key_index + 1) % len(valid_keys)
    new_key = valid_keys[current_key_index]
    client = Groq(api_key=new_key, timeout=30.0, max_retries=0)
    print(f"🔄 Kaluam te çelësi rezervë numër {current_key_index + 1}")

RSS_FEEDS = [
    "https://telegrafi.com/feed/",
    "https://indeksonline.net/feed/",
    "https://www.gazetaexpress.com/feed/",
    "https://klankosova.tv/feed/"
]

DB_FILE = "lajmet.json"

def kontrollo_ballinen_e_burimit(link):
    try:
        domain = "{0.scheme}://{0.netloc}/".format(urllib.parse.urlsplit(link))
        req = urllib.request.Request(domain, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8', errors='ignore')
        path = urllib.parse.urlparse(link).path
        if path and len(path) > 5 and path in html: return True
        elif link in html: return True
        return False
    except: return False

def is_duplicate_news(title1, title2):
    return same_event({'titulli': title1}, {'titulli': title2})


def krijo_slug(titulli):
    return slugify(titulli)

def get_category_bg(cat):
    colors = { 'Sport': 'bg-green-600', 'Politikë': 'bg-red-600', 'Teknologji': 'bg-blue-600', 'Tech': 'bg-blue-600', 'Ekonomi': 'bg-yellow-600', 'Lajme': 'bg-black' }
    return colors.get(cat, 'bg-black')

def get_category_text(cat):
    colors = { 'Sport': 'text-green-600', 'Politikë': 'text-red-600', 'Teknologji': 'text-blue-600', 'Tech': 'text-blue-600', 'Ekonomi': 'text-yellow-600', 'Lajme': 'text-black' }
    return colors.get(cat, 'text-black')

from article_renderer import render_article as gjenero_artikullin_html
from feeds_output import create_rss as krijo_rss, create_sitemap as krijo_sitemap

def gjenero_lajmet_manuale(te_gjitha_lajmet):
    print("Duke kontrolluar për lajme manuale nga Admini...")
    generated = []
    supabase_url = "https://qqgkhioaqsbzygwconbh.supabase.co/rest/v1/manual_news"
    supabase_key = "sb_publishable_2LH0wWF2qnbrWZjwZWBlyg_6-4sSYai"
    req = urllib.request.Request(f"{supabase_url}?select=*", headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"})
    try:
        response = urllib.request.urlopen(req, timeout=20)
        manual_news_data = json.loads(response.read().decode('utf-8'))
        for m in manual_news_data:
            date_str = m.get('created_at', '')
            if not date_str: continue
            try: publication = parse_publication_time(date_str)
            except (ValueError, TypeError): publication = news_now()
            koha_format = publication.strftime("%d/%m/%Y %H:%M")
            article = { "titulli": m['title'], "permbajtja": m['content'], "kategoria": m['category'], "imazhi": m['image_url'], "koha": koha_format, "published_at": publication.isoformat(), "slug": krijo_slug(m['title']), "eshte_balline": True }
            gjenero_artikullin_html(article, te_gjitha_lajmet)
            generated.append(article)
    except Exception as error:
        print(f'Lajmet manuale nuk u gjeneruan: {error}')
    return generated

def load_news():
    # Invalid JSON must stop publication, never silently erase the archive.
    return load_news_file(DB_FILE)

def save_news(news_list):
    write_json_atomic(DB_FILE, news_list[:7000], indent=2)
    write_json_atomic('ballina.json', news_metadata(news_list[:150]))
    write_json_atomic('news-index.json', news_metadata(news_list[:7000]))

def fetch_full_text(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False, fast=True)
            if text: return text
        return ""
    except: return ""

def gjenero_kategori_dhe_hashtags(original_title, full_text):
    prompt = f"""
    Ti je redaktori i portalit "Zani Digjital".
    DETYRA JOTE:
    1. Përcakto KATEGORINË bazuar në titull dhe tekst (Politikë, Sport, Ekonomi, Teknologji, Lajme).
    2. Nëse lajmi është Showbiz, VIP, Thashetheme, ose ekskluzivisht për Maqedoninë e Veriut, kthe VETËM kategorinë "Kalo". 
    3. Gjenero 3-4 HASHTAGS strategjikë.
    
    Titulli origjinal: {original_title}
    Teksti: {full_text[:1000]}
    
    KTHE VETËM SKEDARIN JSON me strukturën:
    {{
      "kategoria": "Kategoria",
      "hashtags": "#hashtag1 #hashtag2"
    }}
    """
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="openai/gpt-oss-120b", temperature=0.0)
            text = response.choices[0].message.content.strip()
            if text.startswith("```json"): text = text[7:-3].strip()
            elif text.startswith("```"): text = text[3:-3].strip()
            result = json.loads(text)
            return result if isinstance(result, dict) else None
        except Exception as e:
            if "429" in str(e):
                if len(valid_keys) > 1: switch_api_key()
                time.sleep(2)
            else: return None
    return None

def main():
    report = RunReport()
    featured = []
    try:
        if client is None:
            raise RuntimeError('Nuk është konfiguruar GROQ_API_KEY.')
        deadline = time.monotonic() + 12 * 60
        existing_news = load_news()
        reference_news = [n for n in existing_news if not n.get('duplicate_of')]
        new_entries, changed, fb_posts_queue = [], {}, []
        write_json_atomic(facebook_queue_path(), [])
        feeds = []
        for feed_url in RSS_FEEDS:
            try:
                request = urllib.request.Request(feed_url, headers={'User-Agent': 'ZaniDigjital/1.0 (+https://zanidigjital.com)'})
                with urllib.request.urlopen(request, timeout=20) as response:
                    parsed = feedparser.parse(response.read())
                entries = parsed.entries[:30]
                feeds.append(entries)
                report.sources.append({'url': feed_url, 'status': 'ok', 'candidates': len(entries)})
            except Exception as error:
                feeds.append([])
                report.sources.append({'url': feed_url, 'status': 'error', 'candidates': 0, 'error_type': type(error).__name__})
        report.counts['discovered'] = sum(map(len, feeds))
        if not any(feeds) and all(s['status'] == 'error' for s in report.sources):
            raise RuntimeError('Asnjë burim RSS nuk u lexua.')
        rotation = (int(time.time()) // 900) % len(feeds)
        feeds = feeds[rotation:] + feeds[:rotation]
        for entry in interleave_feeds(feeds):
            if len(new_entries) >= 5 or time.monotonic() >= deadline:
                break
            title, link = entry.get('title', '').strip(), entry.get('link', '')
            candidate = {'titulli': title, 'link_origjinal': link}
            if not title or not safe_url(link):
                report.event(title, link, 'rejected', 'invalid_entry'); continue
            duplicate, reason = find_duplicate(candidate, new_entries + reference_news[:600])
            if duplicate:
                if reason == 'same_event' and merge_source(duplicate, candidate):
                    changed[duplicate['slug']] = duplicate
                    report.event(title, link, 'merged', 'same_event', target_slug=duplicate['slug'])
                else:
                    report.event(title, link, 'skipped', 'known_url')
                continue
            if any(word in title.lower() for word in ['maqedoni', 'shkup', 'rmv']):
                report.event(title, link, 'rejected', 'excluded_region'); continue
            parsed_time = entry.get('published_parsed') or entry.get('updated_parsed')
            if parsed_time:
                import calendar
                if time.time() - calendar.timegm(parsed_time) > 72 * 3600:
                    report.event(title, link, 'rejected', 'stale_source'); continue
            image = ''
            if entry.get('media_content'):
                image = entry['media_content'][0].get('url', '')
            if not image:
                image = next((item.get('href', '') for item in entry.get('links', []) if item.get('type', '').startswith('image') or item.get('rel') == 'enclosure'), '')
            if not image:
                match = re.search(r'<img[^>]+src=["\x27]([^"\x27>]+)', entry.get('summary', ''))
                if match: image = match[1]
            if not safe_url(image):
                try:
                    with urllib.request.urlopen(urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'}), timeout=8) as response:
                        page = response.read().decode('utf-8', errors='ignore')
                    match = re.search(r'<meta[^>]+property=["\x27]og:image["\x27][^>]+content=["\x27]([^"\x27]+)', page, re.I)
                    if match: image = html.unescape(match[1])
                except Exception:
                    pass
            if not safe_url(image):
                report.event(title, link, 'rejected', 'missing_image'); continue
            content = fetch_full_text(link)
            if len(content) < 200:
                report.event(title, link, 'rejected', 'insufficient_text'); continue
            candidate['permbajtja'] = content
            duplicate, reason = find_duplicate(candidate, new_entries + reference_news[:600])
            if duplicate:
                if merge_source(duplicate, candidate):
                    changed[duplicate['slug']] = duplicate
                    report.event(title, link, 'merged', 'same_event', target_slug=duplicate['slug'])
                else:
                    report.event(title, link, 'skipped', 'known_url')
                continue
            result = gjenero_kategori_dhe_hashtags(title, content)
            time.sleep(3)
            if not result:
                report.event(title, link, 'rejected', 'classification_failed'); continue
            category = result.get('kategoria', 'Lajme')
            if category == 'Kalo':
                report.event(title, link, 'rejected', 'excluded_topic'); continue
            if category not in ('Politikë', 'Sport', 'Ekonomi', 'Teknologji', 'Lajme'):
                category = 'Lajme'
            paragraphs = [p.strip() for p in content.splitlines() if p.strip()]
            if paragraphs and difflib.SequenceMatcher(None, paragraphs[0].lower(), title.lower()).ratio() > .8:
                paragraphs.pop(0)
            while paragraphs and paragraphs[0].lower().startswith(('advertisement', 'reklamë', 'reklama', 'lexo edhe')):
                paragraphs.pop(0)
            while paragraphs and paragraphs[-1].lower().startswith(('lexo edhe', 'lexo më shumë', 'na ndiqni', 'reklamo', 'top lajme')):
                paragraphs.pop()
            content = '\n'.join(paragraphs)
            slug = krijo_slug(title)
            if not slug or len(content) < 200:
                report.event(title, link, 'rejected', 'insufficient_clean_text'); continue
            used = {n.get('slug') for n in existing_news + new_entries}
            if slug in used or os.path.exists(os.path.join('lajme', slug)):
                import hashlib
                slug += '-' + hashlib.sha256(link.encode()).hexdigest()[:8]
            now = news_now()
            article = enrich_municipalities({
                'titulli': title, 'permbajtja': content, 'kategoria': category, 'imazhi': image,
                'koha': now.strftime('%d/%m/%Y %H:%M'), 'published_at': now.isoformat(),
                'source_published_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', parsed_time) if parsed_time else None,
                'link_origjinal': link, 'slug': slug, 'eshte_balline': kontrollo_ballinen_e_burimit(link),
                'burime': [{'url': link, 'titulli': title}], 'source_count': 1,
            })
            new_entries.append(article)
            report.event(title, link, 'prepared', 'accepted', komunat=article['komunat'])
            hashtags = result.get('hashtags', '')
            fb_posts_queue.append({'mesazhi': f"{paragraphs[0]}\n\n{hashtags}".strip(), 'linku': f'https://zanidigjital.com/lajme/{slug}/', 'eshte_balline': article['eshte_balline']})
        updated = new_entries + existing_news
        for article in changed.values():
            article['source_count'] = len({urllib.parse.urlsplit(s['url']).netloc.removeprefix('www.') for s in article.get('burime', [])})
        manual = gjenero_lajmet_manuale(updated)
        combined = list({n['slug']: n for n in updated + manual if n.get('slug') and n.get('titulli')}.values())
        for article in combined:
            if 'komunat' not in article:
                enrich_municipalities(article)
        from news_policy import publication_date
        combined.sort(key=lambda n: publication_date(n).timestamp() if publication_date(n) else 0, reverse=True)
        public_news = [n for n in combined if not n.get('duplicate_of')]
        featured = select_featured(public_news)
        if new_entries or changed:
            save_news(updated)
        for article in new_entries + list(changed.values()):
            gjenero_artikullin_html(article, combined)
        write_json_atomic('ballina.json', news_metadata(public_news[:150]))
        write_json_atomic('news-index.json', news_metadata(public_news[:7000]))
        if new_entries or changed or manual:
            krijo_rss(combined); krijo_sitemap(combined)
        fb_posts_queue.sort(key=lambda n: n['eshte_balline'], reverse=True)
        write_json_atomic(facebook_queue_path(), fb_posts_queue[:2])
        processed = sum(report.counts[key] for key in ('prepared', 'merged', 'skipped', 'rejected'))
        report.counts['unprocessed'] = max(0, report.counts['discovered'] - processed)
        report.finish('degraded' if any(s['status'] == 'error' for s in report.sources) or any(e['reason'] == 'classification_failed' for e in report.events) else 'ok', featured)
    except Exception as error:
        report.finish('error', featured, error)
        raise


if __name__ == '__main__':
    main()
