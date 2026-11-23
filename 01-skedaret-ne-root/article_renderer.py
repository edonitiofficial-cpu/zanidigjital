"""Static article pages: escape feed text and reuse the site's shared assets."""
import html
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote, urlsplit
from news_utils import safe_url
from news_policy import tokens, same_event, publication_date
from featured_image import cached_photo
from photo_utils import photo_variant
from article_content import clean_article_text


def editorial_content(article,esc):
    blocks=article.get('content_blocks')
    if not isinstance(blocks,list) or not blocks:return None
    pieces=[]
    text_blocks=[block for block in blocks if block.get('type') in ('paragraph','heading')]
    clean=clean_article_text('\n'.join(str(b.get('text','')) for b in text_blocks))
    remaining=len(clean.splitlines())
    lead_used=False
    for block in blocks:
        kind=block.get('type')
        if kind in ('paragraph','heading'):
            if remaining<=0:break
            remaining-=1
            text=str(block.get('text','')).strip()
            if not text:continue
            tag='h2' if kind=='heading' else 'p'
            lead=not lead_used and kind=='paragraph' and len(text.split())>=25
            if lead:lead_used=True
            pieces.append(f'<{tag} class="{"article-lead" if lead else "article-paragraph"}">{esc(text)}</{tag}>')
        elif kind=='image':
            original=safe_url(block.get('url'))
            if not original or original==safe_url(article.get('imazhi')):continue
            _,src,srcset=responsive_image(original,True)
            caption=f'<figcaption>{esc(block.get("caption"))}</figcaption>' if block.get('caption') else ''
            pieces.append(f'<figure class="article-inline-media"><a href="{esc(original)}" target="_blank" rel="noopener noreferrer" aria-label="Hape fotografinë e plotë"><img src="{esc(src)}" srcset="{esc(srcset)}" sizes="(max-width: 767px) calc(100vw - 68px), 680px" data-original="{esc(original)}" alt="{esc(block.get("alt"))}" loading="lazy" decoding="async" onerror="this.removeAttribute(\'srcset\');imageFallback(this)"></a>{caption}</figure>')
        elif kind=='embed':
            source=safe_url(block.get('url'));host=(urlsplit(source).hostname or '').removeprefix('www.')
            if host not in ('x.com','twitter.com','youtube.com','youtu.be','facebook.com','instagram.com'):continue
            pieces.append(f'<p class="article-embed"><a href="{esc(source)}" target="_blank" rel="noopener noreferrer">{esc(block.get("label") or "Shiko postimin origjinal")} ↗ <span>{esc(host)}</span></a></p>')
    return ''.join(pieces) or None


def related_articles(article, suggestions):
    words = tokens(article.get('titulli',''))
    places = set(article.get('komunat',[]))
    date = publication_date(article)
    ranked = []
    seen = {article.get('slug'), article.get('duplicate_of')}
    for item in suggestions[:300]:
        if not item.get('slug') or not item.get('titulli') or item['slug'] in seen or item.get('duplicate_of'):
            continue
        seen.add(item['slug'])
        common = len(words & tokens(item['titulli']))
        category = item.get('kategoria') == article.get('kategoria')
        local = bool(places & set(item.get('komunat',[])))
        published = publication_date(item)
        close = bool(date and published and abs((date-published).total_seconds()) < 72*3600)
        score = min(common,6)*3 + category*8 + local*6 + close*2
        ranked.append((score,item))
    result = []
    for _, item in sorted(ranked,key=lambda row:row[0],reverse=True):
        if same_event(article,item) or any(same_event(item,prior) for prior in result):
            continue
        result.append(item)
        if len(result) == 4:
            break
    return result


def responsive_image(value, large=False, cached=None):
    original = safe_url(value) or 'https://zanidigjital.com/zanidigjitalfavicon.png'
    if cached:
        return original, cached['large' if large else 'small'], cached['small']+' 480w'+(', '+cached['large']+' 1000w' if large else '')
    widths = [480,768,1100] if large else [240,480]
    urls = [photo_variant(original,width) for width in widths]
    return original, urls[-1], ', '.join(f'{url} {width}w' for url,width in zip(urls,widths))


def render_article(article, suggestions):
    slug = article['slug']
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', slug):
        raise ValueError('Slug jo i vlefshëm.')
    esc = lambda value: html.escape(str(value or ''), quote=True)
    title = esc(article['titulli'])
    category = esc(article.get('kategoria', 'Lajme'))
    image = esc(safe_url(article.get('imazhi')) or 'https://zanidigjital.com/zanidigjitalfavicon.png')
    _, hero_src, hero_srcset = responsive_image(article.get('imazhi'), True, cached_photo(article))
    clean_text=clean_article_text(article.get('permbajtja',''))
    reading_minutes = max(1, (len(re.findall(r'\w+',clean_text)) + 199)//200)
    url = f"https://zanidigjital.com/lajme/{article.get('duplicate_of') or slug}/"
    paragraphs=[p.strip() for p in clean_text.splitlines() if p.strip()]
    credit=lambda p: bool(re.match(r'^(?:nga|perkthimi|përkthimi|burimi|foto)\s*:',p,re.I))
    lead=next((i for i,p in enumerate(paragraphs) if len(p.split())>=25 and not credit(p)),None)
    content=''.join(f'<p class="{"article-credit" if credit(p) else "article-lead" if i==lead else "article-paragraph"}">{esc(p)}</p>' for i,p in enumerate(paragraphs))
    content=editorial_content(article,esc) or content
    description = esc(article.get('permbajtja', '')[:160])
    source = safe_url(article.get('link_origjinal'))
    source_html = ''
    if source:
        source_html = f'<div class="article-source">Burimi: <a href="{esc(source)}" target="_blank" rel="noopener noreferrer">{esc(urlsplit(source).netloc)}</a><p>Artikull i përzgjedhur dhe përpunuar automatikisht nga Zani Digjital.</p></div>'
    sources = [s for s in article.get('burime', []) if safe_url(s.get('url'))]
    if len(sources) > 1:
        links = ' · '.join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(urlsplit(s["url"]).netloc)}</a>' for s in sources)
        source_html = f'<div class="article-source"><strong>Burimet e kësaj ngjarjeje</strong><p>{links}</p><p>Raportimet për të njëjtën ngjarje janë grupuar. Teksti i artikullit mbetet nga burimi fillestar.</p></div>'
    municipality_links = ' '.join(f'<a href="/?komuna={quote(name)}" class="inline-block bg-gray-100 rounded-lg px-3 py-1 text-sm mr-2 mb-2">{esc(name)}</a>' for name in article.get('komunat', []))
    schema = {
        '@context': 'https://schema.org', '@type': 'NewsArticle',
        'headline': article['titulli'], 'image': safe_url(article.get('imazhi')),
        'mainEntityOfPage': url, 'articleSection': article.get('kategoria', 'Lajme'),
        'publisher': {'@type': 'Organization', 'name': 'Zani Digjital',
                      'logo': {'@type': 'ImageObject', 'url': 'https://zanidigjital.com/zanidigjital.png'}}
    }
    if article.get('published_at'):
        schema['datePublished'] = article['published_at']
    schema_json = json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c')
    related = []
    for item in related_articles(article,suggestions):
        original, related_src, related_srcset = responsive_image(item.get('imazhi'), cached=cached_photo(item))
        related.append(f'''<a href="/lajme/{quote(item['slug'], safe='-')}/" class="related-card bg-gray-50 rounded-xl overflow-hidden border border-gray-100 hover:shadow-md transition">
            <img src="{esc(related_src)}" srcset="{esc(related_srcset)}" sizes="(max-width: 600px) 100px, 220px" data-original="{esc(original)}" alt="" loading="lazy" decoding="async" width="400" height="225" class="w-full h-40 object-cover" onerror="this.removeAttribute('srcset');imageFallback(this)">
            <div class="p-4"><span class="text-xs font-bold text-blue-700 uppercase">{esc(item.get('kategoria'))}</span><h3 class="text-base font-bold leading-snug mt-2">{esc(item.get('titulli'))}</h3></div></a>''')
    nav = '<a href="/" class="hover:text-black">Ballina</a>' + ''.join(
        f'<a href="/?kategoria={quote(cat)}" class="hover:text-black">{esc(cat)}</a>'
        for cat in ['Lajme', 'Politikë', 'Ekonomi', 'Sport', 'Teknologji'])
    page = f'''<!DOCTYPE html>
<html lang="sq"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - Zani Digjital</title>
<meta name="description" content="{description}"><link rel="canonical" href="{url}">
<meta property="og:type" content="article"><meta property="og:url" content="{url}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{description}">
<meta property="og:image" content="{image}"><meta property="og:site_name" content="Zani Digjital">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/zanidigjitalfavicon.png"><link rel="apple-touch-icon" href="/zanidigjitalfavicon.png">
<link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#ffffff">
<link rel="preload" as="font" href="/fonts/inter-latin.woff2" type="font/woff2" crossorigin>
<link rel="preconnect" href="https://wsrv.nl">
<link rel="preload" as="image" href="{esc(hero_src)}" imagesrcset="{esc(hero_srcset)}" imagesizes="(max-width: 767px) calc(100vw - 32px), 900px" fetchpriority="high">
<link rel="stylesheet" href="/fonts.css"><link rel="stylesheet" href="/utilities.css"><link rel="stylesheet" href="/site.css">
<link rel="stylesheet" href="/article.css">
<script async src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2" onload="window.dispatchEvent(new Event('supabase-ready'))" onerror="window.dispatchEvent(new Event('supabase-failed'))"></script>
<script src="/site.js"></script><script src="/site-widgets.js" defer></script>
<script src="/article.js" defer></script>
<script type="application/ld+json">{schema_json}</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-F3XJ36058R"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-F3XJ36058R');</script>
<style>body{{font-family:Inter,sans-serif;background:#F8F9FA}}.permbajtja p{{margin-bottom:1.5rem}}</style>
</head><body class="article-page text-gray-900 antialiased">
<div id="reading-progress" aria-hidden="true"></div>
<a class="skip-link" href="#main-content">Kalo te artikulli</a>
<header class="bg-white sticky top-0 z-50 shadow-sm border-b border-gray-200">
<div class="max-w-[1800px] mx-auto px-4 sm:px-6 py-4"><div class="flex flex-col md:flex-row justify-between items-center max-w-[1100px] mx-auto gap-3">
<a href="/" class="flex-shrink-0"><img src="/zanidigjital.png" alt="Zani Digjital — Ballina" class="h-16 object-contain" width="240" height="64"></a>
<div class="w-full md:w-auto overflow-x-auto"><nav class="flex gap-5 whitespace-nowrap font-semibold text-gray-600" aria-label="Kategoritë e lajmeve">{nav}</nav></div>
</div></div></header>
<div class="max-w-[1800px] mx-auto px-4 sm:px-6 flex justify-center items-start gap-6">
<aside id="sidebar-left-container" class="hidden xl:block w-[300px] shrink-0 pt-8 sticky top-28"></aside>
<main id="main-content" class="w-full max-w-[1100px] flex-1 min-w-0 py-8">
<article class="article-body bg-white p-5 sm:p-8 lg:p-12 rounded-2xl border border-gray-100 shadow-sm">
<a href="/" class="inline-block text-sm font-semibold text-gray-500 mb-6">← Kthehu te Ballina</a>
<div class="article-meta flex flex-wrap items-center gap-4 mb-4"><a href="/?kategoria={quote(article.get('kategoria', 'Lajme'))}" class="bg-blue-700 text-white text-xs uppercase font-bold px-3 py-1 rounded">{category}</a><time class="text-gray-500 text-sm"{(' datetime="' + esc(article['published_at']) + '"') if article.get('published_at') else ''}>{esc(article.get('koha'))}</time><span>{reading_minutes} min lexim</span></div>
<h1 class="text-3xl md:text-5xl font-black leading-tight mb-6">{title}</h1>
<div class="mb-4">{municipality_links}</div>
<div class="article-share"><span>Shpërndaje</span><a href="https://www.facebook.com/sharer/sharer.php?u={quote(url, safe='')}" target="_blank" rel="noopener noreferrer">Facebook</a><a href="https://api.whatsapp.com/send?text={quote(article['titulli'] + ' ' + url, safe='')}" target="_blank" rel="noopener noreferrer">WhatsApp</a><button id="copy-article-link" type="button">Kopjo lidhjen</button><button id="share-article" type="button" hidden>Ndaj</button><span id="article-share-status" role="status" aria-live="polite"></span></div>
<a class="article-image-link" href="{image}" target="_blank" rel="noopener noreferrer" aria-label="Hape fotografinë e plotë"><img src="{esc(hero_src)}" srcset="{esc(hero_srcset)}" sizes="(max-width: 767px) calc(100vw - 32px), 900px" data-original="{image}" alt="{title}" fetchpriority="high" decoding="async" width="1100" height="620" class="article-hero w-full object-cover rounded-xl mb-10" onerror="this.removeAttribute('srcset');imageFallback(this)"></a>
<div class="permbajtja text-lg text-gray-800">{content}</div>{source_html}
<div id="banner-article-top" class="mt-8"></div><div id="banner-article-bottom" class="mt-6"></div>
<section class="article-related mt-12 pt-8 border-t border-gray-100"><h2 class="text-2xl font-extrabold mb-6">Lajme të ngjashme</h2><div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">{''.join(related)}</div></section>
</article></main>
<aside id="sidebar-right-container" class="hidden xl:block w-[300px] shrink-0 pt-8"></aside></div>
<div id="mobile-popup" class="fixed bottom-4 left-0 w-full z-[100] flex justify-center px-4 pointer-events-none translate-y-[150%] opacity-0 md:hidden"><div class="relative pointer-events-auto max-w-[400px] w-full"><button type="button" onclick="mbyllMobileAd()" aria-label="Mbyll reklamën" class="absolute -top-3 right-0 bg-black text-white rounded-full w-10 h-10">×</button><a id="mobile-popup-link" target="_blank" rel="noopener noreferrer"><img id="mobile-popup-img" alt="Reklamë e sponsorizuar" class="w-full rounded-xl"></a></div></div>
<footer class="bg-white border-t border-gray-200 py-8 mt-8 text-center text-gray-500 text-sm">© 2026 Zani Digjital. Të gjitha të drejtat e rezervuara.</footer>
</body></html>'''
    folder = os.path.join('lajme', slug)
    os.makedirs(folder, exist_ok=True)
    target=Path(folder)/'index.html'
    if target.exists() and target.read_text(encoding='utf-8') == page:
        return
    fd,temporary=tempfile.mkstemp(dir=folder,prefix='.news-',suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(page)
        os.replace(temporary,target)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
