"""Static article pages: escape feed text and reuse the site's shared assets."""
import html
import json
import os
import re
from urllib.parse import quote, urlsplit
from news_utils import safe_url


def render_article(article, suggestions):
    slug = article['slug']
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', slug):
        raise ValueError('Slug jo i vlefshëm.')
    esc = lambda value: html.escape(str(value or ''), quote=True)
    title = esc(article['titulli'])
    category = esc(article.get('kategoria', 'Lajme'))
    image = esc(safe_url(article.get('imazhi')) or 'https://zanidigjital.com/zanidigjitalfavicon.png')
    url = f"https://zanidigjital.com/lajme/{article.get('duplicate_of') or slug}/"
    content = ''.join(f'<p>{esc(p.strip())}</p>' for p in article.get('permbajtja', '').splitlines() if p.strip())
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
    for item in suggestions:
        if not item.get('slug') or item['slug'] == slug or item.get('duplicate_of'):
            continue
        related.append(f'''<a href="/lajme/{quote(item['slug'], safe='-')}/" class="bg-gray-50 rounded-xl overflow-hidden border border-gray-100 hover:shadow-md transition">
            <img src="{esc(safe_url(item.get('imazhi')))}" alt="" loading="lazy" decoding="async" width="400" height="225" class="w-full h-40 object-cover" onerror="this.onerror=null;this.src='/zanidigjitalfavicon.png'">
            <div class="p-4"><span class="text-xs font-bold text-blue-700 uppercase">{esc(item.get('kategoria'))}</span><h3 class="text-base font-bold leading-snug mt-2">{esc(item.get('titulli'))}</h3></div></a>''')
        if len(related) == 4:
            break
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
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script><link rel="stylesheet" href="/site.css">
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script src="/site.js"></script><script src="/site-widgets.js" defer></script>
<script type="application/ld+json">{schema_json}</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-F3XJ36058R"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-F3XJ36058R');</script>
<style>body{{font-family:Inter,sans-serif;background:#F8F9FA}}.permbajtja p{{margin-bottom:1.5rem}}</style>
</head><body class="text-gray-900 antialiased">
<a class="skip-link" href="#main-content">Kalo te artikulli</a>
<header class="bg-white sticky top-0 z-50 shadow-sm border-b border-gray-200">
<div class="max-w-[1800px] mx-auto px-4 sm:px-6 py-4"><div class="flex flex-col md:flex-row justify-between items-center max-w-[1100px] mx-auto gap-3">
<a href="/" class="flex-shrink-0"><img src="/zanidigjital.png" alt="Zani Digjital — Ballina" class="h-16 object-contain" width="240" height="64"></a>
<div class="w-full md:w-auto overflow-x-auto"><nav class="flex gap-5 whitespace-nowrap font-semibold text-gray-600" aria-label="Kategoritë e lajmeve">{nav}</nav></div>
</div></div></header>
<div class="max-w-[1800px] mx-auto px-4 sm:px-6 flex justify-center items-start gap-6">
<aside id="sidebar-left-container" class="hidden xl:block w-[300px] shrink-0 pt-8 sticky top-28"></aside>
<main id="main-content" class="w-full max-w-[1100px] flex-1 min-w-0 py-8">
<article class="bg-white p-5 sm:p-8 lg:p-12 rounded-2xl border border-gray-100 shadow-sm">
<a href="/" class="inline-block text-sm font-semibold text-gray-500 mb-6">← Kthehu te Ballina</a>
<div class="flex flex-wrap items-center gap-4 mb-4"><a href="/?kategoria={quote(article.get('kategoria', 'Lajme'))}" class="bg-blue-700 text-white text-xs uppercase font-bold px-3 py-1 rounded">{category}</a><time class="text-gray-500 text-sm"{(' datetime="' + esc(article['published_at']) + '"') if article.get('published_at') else ''}>{esc(article.get('koha'))}</time></div>
<h1 class="text-3xl md:text-5xl font-black leading-tight mb-6">{title}</h1>
<div class="mb-4">{municipality_links}</div>
<div class="flex gap-3 mb-8"><a href="https://www.facebook.com/sharer/sharer.php?u={quote(url, safe='')}" target="_blank" rel="noopener noreferrer" class="bg-blue-600 text-white font-bold text-sm px-4 py-2 rounded-lg">Ndaj në Facebook</a><a href="https://api.whatsapp.com/send?text={quote(article['titulli'] + ' ' + url, safe='')}" target="_blank" rel="noopener noreferrer" class="bg-green-700 text-white font-bold text-sm px-4 py-2 rounded-lg">WhatsApp</a></div>
<img src="{image}" alt="{title}" fetchpriority="high" width="1100" height="620" class="w-full max-h-[560px] object-cover rounded-xl mb-10" onerror="this.onerror=null;this.src='/zanidigjitalfavicon.png'">
<div class="permbajtja text-lg text-gray-800">{content}</div>{source_html}
<div id="banner-article-top" class="mt-8"></div><div id="banner-article-bottom" class="mt-6"></div>
<section class="mt-12 pt-8 border-t border-gray-100"><h2 class="text-2xl font-extrabold mb-6">Lexo më shumë</h2><div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">{''.join(related)}</div></section>
</article></main>
<aside id="sidebar-right-container" class="hidden xl:block w-[300px] shrink-0 pt-8"></aside></div>
<div id="mobile-popup" class="fixed bottom-4 left-0 w-full z-[100] flex justify-center px-4 pointer-events-none translate-y-[150%] opacity-0 md:hidden"><div class="relative pointer-events-auto max-w-[400px] w-full"><button type="button" onclick="mbyllMobileAd()" aria-label="Mbyll reklamën" class="absolute -top-3 right-0 bg-black text-white rounded-full w-10 h-10">×</button><a id="mobile-popup-link" target="_blank" rel="noopener noreferrer"><img id="mobile-popup-img" alt="Reklamë e sponsorizuar" class="w-full rounded-xl"></a></div></div>
<footer class="bg-white border-t border-gray-200 py-8 mt-8 text-center text-gray-500 text-sm">© 2026 Zani Digjital. Të gjitha të drejtat e rezervuara.</footer>
<script>if(window.supabase)window.sb=window.supabase.createClient('https://qqgkhioaqsbzygwconbh.supabase.co','sb_publishable_2LH0wWF2qnbrWZjwZWBlyg_6-4sSYai');document.addEventListener('DOMContentLoaded',()=>{{loadBanners();initMobileAds();}});</script>
</body></html>'''
    folder = os.path.join('lajme', slug)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, 'index.html'), 'w', encoding='utf-8') as stream:
        stream.write(page)
