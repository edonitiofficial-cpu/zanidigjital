import os
import json
import feedparser
import time
import re
import urllib.request
import urllib.parse
import difflib
import trafilatura
from groq import Groq
from datetime import datetime, timedelta

# --- SISTEMI I RROTULLIMIT TË ÇELËSAVE ---
api_keys = [
    os.environ.get("GROQ_API_KEY"),
    os.environ.get("GROQ_API_KEY_2"),
    os.environ.get("GROQ_API_KEY_3")
]
valid_keys = [key for key in api_keys if key]

if not valid_keys:
    print("Gabim: Nuk u gjet asnjë GROQ_API_KEY!")
    exit()

current_key_index = 0
client = Groq(api_key=valid_keys[current_key_index])

def switch_api_key():
    global current_key_index, client
    current_key_index = (current_key_index + 1) % len(valid_keys)
    new_key = valid_keys[current_key_index]
    client = Groq(api_key=new_key)
    print(f"🔄 Kaluam te çelësi rezervë numër {current_key_index + 1}")

# --- BURIMET E LAJMEVE ---
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
    t1 = title1.lower()
    t2 = title2.lower()
    if difflib.SequenceMatcher(None, t1, t2).ratio() > 0.55: return True
    def get_stems(text):
        words = re.findall(r'\b[a-zëç]{4,}\b', text)
        return set(w[:5] if len(w) > 5 else w for w in words)
    stems1, stems2 = get_stems(t1), get_stems(t2)
    if stems1 and stems2 and len(stems1.intersection(stems2)) >= 4: return True
    return False

def krijo_slug(titulli):
    if not titulli: return ""
    slug = titulli.lower().replace('ë', 'e').replace('ç', 'c')
    slug = re.sub(r'[^a-z0-9 -]', '', slug)
    slug = re.sub(r'\s+', '-', slug).replace(r'-+', '-')
    return slug.strip('-')

def get_category_bg(cat):
    colors = { 'Sport': 'bg-green-600', 'Politikë': 'bg-red-600', 'Teknologji': 'bg-blue-600', 'Tech': 'bg-blue-600', 'Ekonomi': 'bg-yellow-600', 'Lajme': 'bg-black' }
    return colors.get(cat, 'bg-black')

def get_category_text(cat):
    colors = { 'Sport': 'text-green-600', 'Politikë': 'text-red-600', 'Teknologji': 'text-blue-600', 'Tech': 'text-blue-600', 'Ekonomi': 'text-yellow-600', 'Lajme': 'text-black' }
    return colors.get(cat, 'text-black')

def gjenero_artikullin_html(article, te_gjitha_lajmet):
    slug = article["slug"]
    titulli = article["titulli"].replace('"', '&quot;')
    imazhi = article["imazhi"]
    permbajtja = article["permbajtja"]
    kategoria = article.get("kategoria", "Lajme")
    koha = article.get("koha", "")
    
    url_baze = f"https://zanidigjital.com/lajme/{slug}"
    permbajtja_meta = permbajtja[:150].replace('"', '&quot;') + "..."
    permbajtja_html = "".join([f"<p>{p.strip()}</p>" for p in permbajtja.split('\n') if p.strip()])
    cat_bg = get_category_bg(kategoria)

    sugjerime_html = ""
    count = 0
    for s in te_gjitha_lajmet:
        if s.get("slug") == slug: continue
        if count >= 5: break
        c_text = get_category_text(s.get("kategoria", "Lajme"))
        s_slug = s.get("slug")
        sugjerime_html += f"""
        <a href="https://zanidigjital.com/lajme/{s_slug}" class="group flex gap-4 items-center pb-4 border-b border-gray-50 last:border-0 last:pb-0">
            <img src="{s.get('imazhi')}" class="w-20 h-20 object-cover rounded-lg shadow-sm group-hover:opacity-90 transition" alt="">
            <div class="flex-1">
                <span class="text-[10px] {c_text} font-bold uppercase tracking-wider">{s.get('kategoria')}</span>
                <h4 class="text-[14px] font-bold text-gray-800 leading-snug group-hover:underline transition line-clamp-2 mt-1">{s.get('titulli')}</h4>
            </div>
        </a>"""
        count += 1

    folder_path = os.path.join("lajme", slug)
    if not os.path.exists(folder_path): os.makedirs(folder_path)

    html_content = f"""<!DOCTYPE html>
<html lang="sq">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{titulli} - Zani Digjital</title>
    
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-F3XJ36058R"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-F3XJ36058R');
    </script>
    
    <meta name="description" content="{permbajtja_meta}">
    <link rel="canonical" href="{url_baze}">
    
    <meta property="og:type" content="article">
    <meta property="og:url" content="{url_baze}">
    <meta property="og:title" content="{titulli}">
    <meta property="og:description" content="{permbajtja_meta}">
    <meta property="og:image" content="{imazhi}">
    <meta property="og:site_name" content="Zani Digjital">

    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#ffffff">
    <link rel="icon" type="image/png" href="/zanidigjitalfavicon.png">
    <link rel="apple-touch-icon" href="/zanidigjitalfavicon.png">

    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>

    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&display=swap');
        body {{ font-family: 'Inter', sans-serif; background-color: #F8F9FA; overscroll-behavior-y: contain; }}
        .permbajtja p {{ margin-bottom: 1.5rem; }}
        .line-clamp-2 {{ display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
        .no-scrollbar::-webkit-scrollbar {{ display: none; }}
        .no-scrollbar {{ -ms-overflow-style: none; scrollbar-width: none; }}
    </style>
</head>
<body class="text-gray-900 antialiased bg-[#F8F9FA] overscroll-y-auto">
  <div class="relative w-full overflow-x-hidden min-h-screen">
    <header class="bg-white sticky top-0 z-50 shadow-sm border-b border-gray-200 w-full">
        <div class="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div class="flex flex-col md:flex-row justify-between items-center max-w-[1100px] mx-auto">
                <a href="https://zanidigjital.com/" class="flex-shrink-0 mb-4 md:mb-0">
                    <img src="/zanidigjital.png" alt="ZaniDigjital Logo" class="h-16 object-contain" onerror="this.src='https://via.placeholder.com/200x50/ffffff/000000?text=ZANI+DIGJITAL+LOGO'">
                </a>
                <div class="w-full md:w-auto overflow-x-auto no-scrollbar">
                    <nav class="flex md:justify-center gap-4 sm:gap-6 font-semibold text-gray-600 whitespace-nowrap px-2 md:px-0 pb-2 md:pb-0">
                        <a href="https://zanidigjital.com/" class="hover:text-black transition">Ballina</a>
                        <a href="https://zanidigjital.com/?kategoria=Lajme" class="hover:text-black transition">Lajme</a>
                        <a href="https://zanidigjital.com/?kategoria=Politikë" class="hover:text-black transition">Politikë</a>
                        <a href="https://zanidigjital.com/?kategoria=Ekonomi" class="hover:text-black transition">Ekonomi</a>
                        <a href="https://zanidigjital.com/?kategoria=Sport" class="hover:text-black transition">Sport</a>
                        <a href="https://zanidigjital.com/?kategoria=Teknologji" class="hover:text-black transition">Teknologji</a>
                    </nav>
                </div>
            </div>
        </div>
    </header>

    <div class="max-w-[1800px] mx-auto px-4 sm:px-6 xl:px-8 flex justify-center gap-6 xl:gap-8 w-full">
        
        <aside class="hidden xl:block w-[300px] shrink-0 pt-8">
            <div class="sticky top-28">
                <a href="#" id="sidebar-left-link" class="block w-full h-[600px] rounded-2xl overflow-hidden shadow-lg border border-gray-200 relative group bg-gray-100">
                    <span class="absolute top-2 left-2 bg-yellow-400 text-black text-[10px] font-bold px-2 py-1 rounded uppercase z-10">Sponsorizuar</span>
                    <img id="sidebar-left-img" src="https://images.unsplash.com/photo-1556761175-5973dc0f32b7?q=80&w=400&auto=format&fit=crop" class="w-full h-full object-cover group-hover:scale-105 transition duration-700">
                </a>
            </div>
        </aside>

        <main class="w-full max-w-[1100px] flex-1 min-w-0 py-8 flex flex-col lg:flex-row gap-8">
            <article class="lg:w-2/3 bg-white p-6 lg:p-10 rounded-2xl shadow-sm border border-gray-100 relative">
                <a href="https://zanidigjital.com/" class="inline-flex items-center text-sm font-bold text-gray-500 hover:text-black mb-6 transition">← Kthehu te Ballina</a>
                <div class="flex items-center gap-4 mb-4 font-bold">
                    <span class="{cat_bg} text-white px-3 py-1 rounded text-xs uppercase tracking-wider">{kategoria}</span>
                    <span class="text-gray-400 text-sm font-medium">{koha}</span>
                </div>
                <h1 class="text-3xl md:text-5xl font-black text-gray-900 leading-tight mb-6">{titulli}</h1>
                <div class="flex flex-wrap gap-2 mb-8">
                    <a href="https://www.facebook.com/sharer/sharer.php?u={url_baze}" target="_blank" class="bg-[#1877F2] text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-blue-700 transition flex items-center gap-2">Ndaj</a>
                </div>

                <div id="banner-article-top" class="w-full mb-8"></div>
                <img src="{imazhi}" class="w-full h-auto max-h-[500px] rounded-xl object-cover mb-10 shadow-sm border border-gray-100" alt="{titulli}">
                
                <div class="permbajtja text-[18px] text-gray-800 leading-relaxed font-medium">
                    {permbajtja_html}
                </div>
                <div id="banner-article-bottom" class="w-full mt-8"></div>
            </article>

            <aside class="lg:w-1/3 space-y-6">
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                    <h3 class="font-extrabold text-lg mb-4 text-gray-900 border-b border-gray-100 pb-3 flex items-center gap-2">
                        <span class="bg-black text-white px-2 py-1 rounded text-xs uppercase">Të rejat</span> Lexo më shumë
                    </h3>
                    <div class="space-y-4">{sugjerime_html}</div>
                </div>
            </aside>
        </main>

        <aside class="hidden xl:block w-[300px] shrink-0 pt-8">
            <div class="sticky top-28">
                <a href="#" id="sidebar-right-link" class="block w-full h-[600px] rounded-2xl overflow-hidden shadow-lg border border-gray-200 relative group bg-gray-100">
                    <span class="absolute top-2 right-2 bg-yellow-400 text-black text-[10px] font-bold px-2 py-1 rounded uppercase z-10">Sponsorizuar</span>
                    <img id="sidebar-right-img" src="https://images.unsplash.com/photo-1542744173-8e7e53415bb0?q=80&w=400&auto=format&fit=crop" class="w-full h-full object-cover group-hover:scale-105 transition duration-700">
                </a>
            </div>
        </aside>
    </div>

    <!-- POP-UP REKLAMA -->
    <div id="mobile-popup" class="fixed bottom-4 left-0 w-full z-[100] flex justify-center px-4 pointer-events-none transition-all duration-500 transform translate-y-[150%] opacity-0 md:hidden">
        <div class="relative pointer-events-auto shadow-2xl rounded-xl overflow-hidden max-w-[400px] w-full bg-transparent">
            <button onclick="mbyllMobileAd()" class="absolute top-1 right-1 bg-black/60 text-white rounded-full w-7 h-7 flex items-center justify-center text-sm z-10 border border-white/20 shadow-md">&times;</button>
            <a id="mobile-popup-link" href="#" target="_blank" class="block">
                <img id="mobile-popup-img" src="" class="w-full h-auto max-h-[120px] object-cover" alt="Reklamë">
            </a>
        </div>
    </div>

    <footer class="bg-white border-t border-gray-200 py-8 mt-12 w-full">
        <div class="max-w-[1800px] mx-auto px-4 text-center text-gray-500 font-medium">
            <p>&copy; 2026 Zani Digjital. Të gjitha të drejtat e rezervuara.</p>
        </div>
    </footer>
  </div>

    <script>
        const supabaseUrl = 'https://qqgkhioaqsbzygwconbh.supabase.co';
        const supabaseKey = 'sb_publishable_2LH0wWF2qnbrWZjwZWBlyg_6-4sSYai';
        if (window.supabase) window.sb = window.supabase.createClient(supabaseUrl, supabaseKey);

        if ('serviceWorker' in navigator) {{ window.addEventListener('load', () => {{ navigator.serviceWorker.register('/sw.js'); }}); }}

        let userClosedAd = false;
        function mbyllMobileAd() {{ userClosedAd = true; document.getElementById('mobile-popup').style.display = 'none'; }}

        async function initMobileAds() {{
            if (window.innerWidth > 768) return;
            let mobileAds = [{{ img: "https://images.unsplash.com/photo-1611162617474-5b21e879e113?q=80&w=600&auto=format&fit=crop", link: "#" }}];
            if (window.sb) {{
                try {{
                    const {{ data }} = await window.sb.from('banners').select('*').eq('status', 'active').eq('position', 'mobile_popup').order('created_at', {{ ascending: false }});
                    if (data && data.length > 0) mobileAds = data.map(b => ({{ img: b.image_url, link: b.link_url || '#' }}));
                }} catch(e) {{}}
            }}
            let currentAdIndex = 0;
            const popup = document.getElementById('mobile-popup'), popupImg = document.getElementById('mobile-popup-img'), popupLink = document.getElementById('mobile-popup-link');
            function showAd() {{
                if (userClosedAd) return;
                if (currentAdIndex >= mobileAds.length) currentAdIndex = 0; 
                popupImg.src = mobileAds[currentAdIndex].img; popupLink.href = mobileAds[currentAdIndex].link;
                popup.classList.remove('translate-y-[150%]', 'opacity-0'); popup.classList.add('translate-y-0', 'opacity-100');
                setTimeout(() => {{ if (userClosedAd) return; hideAd(); currentAdIndex++; setTimeout(showAd, 15000); }}, 5000); 
            }}
            function hideAd() {{ popup.classList.remove('translate-y-0', 'opacity-100'); popup.classList.add('translate-y-[150%]', 'opacity-0'); }}
            setTimeout(showAd, 2000);
        }}

        async function loadBanners() {{
            if(!window.sb) return;
            try {{
                const {{ data }} = await window.sb.from('banners').select('*').eq('status', 'active').order('created_at', {{ ascending: false }});
                if(data) {{
                    const topBanner = data.find(b => b.position === 'article_top'), bottomBanner = data.find(b => b.position === 'article_bottom'), leftBanner = data.find(b => b.position === 'sidebar_left'), rightBanner = data.find(b => b.position === 'sidebar_right');
                    if(topBanner) {{ const cont = document.getElementById('banner-article-top'); if(cont) cont.innerHTML = `<a href="${{topBanner.link_url || '#'}}"" target="_blank" class="block w-full"><img src="${{topBanner.image_url}}"" class="w-full h-auto rounded-xl shadow-sm border border-gray-100 hover:opacity-90 transition object-cover" loading="lazy"></a>`; }}
                    if(bottomBanner) {{ const cont = document.getElementById('banner-article-bottom'); if(cont) cont.innerHTML = `<a href="${{bottomBanner.link_url || '#'}}"" target="_blank" class="block w-full"><img src="${{bottomBanner.image_url}}"" class="w-full h-auto rounded-xl shadow-sm border border-gray-100 hover:opacity-90 transition object-cover" loading="lazy"></a>`; }}
                    if(leftBanner) {{ const img = document.getElementById('sidebar-left-img'), link = document.getElementById('sidebar-left-link'); if(img && link) {{ img.src = leftBanner.image_url; link.href = leftBanner.link_url || '#'; }} }}
                    if(rightBanner) {{ const img = document.getElementById('sidebar-right-img'), link = document.getElementById('sidebar-right-link'); if(img && link) {{ img.src = rightBanner.image_url; link.href = rightBanner.link_url || '#'; }} }}
                }}
            }} catch(e) {{}}
        }}

        document.addEventListener('DOMContentLoaded', () => {{ setTimeout(() => {{ loadBanners(); initMobileAds(); }}, 800); }});
    </script>
</body>
</html>"""
    
    file_path = os.path.join(folder_path, "index.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

def gjenero_lajmet_manuale(te_gjitha_lajmet):
    print("Duke kontrolluar për lajme manuale nga Admini...")
    supabase_url = "https://qqgkhioaqsbzygwconbh.supabase.co/rest/v1/manual_news"
    supabase_key = "sb_publishable_2LH0wWF2qnbrWZjwZWBlyg_6-4sSYai"
    req = urllib.request.Request(f"{supabase_url}?select=*", headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"})
    try:
        response = urllib.request.urlopen(req)
        manual_news_data = json.loads(response.read().decode('utf-8'))
        for m in manual_news_data:
            date_str = m.get('created_at', '')[:16]
            if not date_str: continue
            try: koha_format = datetime.strptime(date_str, "%Y-%m-%dT%H:%M").strftime("%d/%m/%Y %H:%M")
            except: koha_format = (datetime.now() + timedelta(hours=2)).strftime("%d/%m/%Y %H:%M")
            article = { "titulli": m['title'], "permbajtja": m['content'], "kategoria": m['category'], "imazhi": m['image_url'], "koha": koha_format, "slug": krijo_slug(m['title']), "eshte_balline": True }
            gjenero_artikullin_html(article, te_gjitha_lajmet)
    except: pass

def krijo_rss(lajmet):
    rss_content = """<?xml version="1.0" encoding="UTF-8" ?>\n<rss version="2.0">\n<channel>\n  <title>Zani Digjital</title>\n  <link>https://zanidigjital.com/</link>\n  <description>Lajmet e fundit nga Zani Digjital</description>\n"""
    for lajm in lajmet[:15]:
        slug = lajm.get("slug", "")
        titulli = lajm.get("titulli", "").replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        linku = f"https://zanidigjital.com/lajme/{slug}"
        pershkrimi = lajm.get("permbajtja", "")[:150].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') + "..."
        rss_content += f"  <item>\n    <title>{titulli}</title>\n    <link>{linku}</link>\n    <description>{pershkrimi}</description>\n  </item>\n"
    rss_content += "</channel>\n</rss>"
    with open("rss.xml", "w", encoding="utf-8") as f: f.write(rss_content)

def krijo_sitemap(lajmet):
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    koha_tani = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d")
    for faqe in ["https://zanidigjital.com/", "https://zanidigjital.com/?kategoria=Lajme", "https://zanidigjital.com/?kategoria=Politikë", "https://zanidigjital.com/?kategoria=Ekonomi", "https://zanidigjital.com/?kategoria=Sport", "https://zanidigjital.com/?kategoria=Teknologji"]:
        sitemap_content += f"  <url>\n    <loc>{faqe}</loc>\n    <lastmod>{koha_tani}</lastmod>\n    <changefreq>always</changefreq>\n    <priority>1.0</priority>\n  </url>\n"
    for lajm in lajmet[:1000]:
        slug = lajm.get("slug", krijo_slug(lajm.get("titulli", "")))
        linku = f"https://zanidigjital.com/lajme/{slug}"
        data_lajmit = koha_tani
        if "koha" in lajm:
            try: data_lajmit = datetime.strptime(lajm["koha"], "%d/%m/%Y %H:%M").strftime("%Y-%m-%d")
            except: pass
        sitemap_content += f"  <url>\n    <loc>{linku}</loc>\n    <lastmod>{data_lajmit}</lastmod>\n    <changefreq>never</changefreq>\n    <priority>0.8</priority>\n  </url>\n"
    sitemap_content += "</urlset>"
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(sitemap_content)

def posto_ne_facebook(mesazhi, linku):
    fb_token = os.environ.get("FACEBOOK_PAGE_TOKEN")
    if not fb_token: return
    url = "https://graph.facebook.com/v19.0/me/feed"
    data = urllib.parse.urlencode({"message": mesazhi, "link": linku, "access_token": fb_token}).encode('utf-8')
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=data))
        print(f"✅ FB POST SUCCESS: {linku}")
    except: pass

def load_news():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def save_news(news_list):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(news_list[:3000], f, ensure_ascii=False, indent=2)
    lajmet_ballina = []
    for lajm in news_list[:150]:
        lajmet_ballina.append({
            "titulli": lajm.get("titulli"), "kategoria": lajm.get("kategoria"),
            "imazhi": lajm.get("imazhi"), "koha": lajm.get("koha"), "slug": lajm.get("slug"), "eshte_balline": lajm.get("eshte_balline", True)
        })
    with open("ballina.json", "w", encoding="utf-8") as f:
        json.dump(lajmet_ballina, f, ensure_ascii=False)

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
            return json.loads(text)
        except Exception as e:
            if "429" in str(e):
                if len(valid_keys) > 1: switch_api_key()
                time.sleep(2)
            else: return None
    return None

def main():
    existing_news = load_news()
    existing_links = {item.get("link_origjinal") for item in existing_news}
    new_entries = []
    fb_posts_queue = []
    lajme_te_perpunuara = 0
    MAX_LAJME = 5

    for feed_url in RSS_FEEDS:
        if lajme_te_perpunuara >= MAX_LAJME: break
        parsed = feedparser.parse(feed_url)
        
        for entry in parsed.entries[:100]: 
            if lajme_te_perpunuara >= MAX_LAJME: break
                
            link = entry.get("link", "")
            title = entry.get("title", "")
            
            if link in existing_links: continue

            # Kontrolli Anti-Maqedoni direkt nga Titulli
            titulli_lower = title.lower()
            if any(k in titulli_lower for k in ["maqedoni", "maqedonisë", "maqedoninë", "maqedonia", "shkup", "shkupi", "shkupin", "RMV"]):
                print(f"🚫 U bllokua lajmi për Maqedoninë: {title}")
                continue

            is_duplicate = False
            for existing_item in (new_entries + existing_news)[:150]:
                if is_duplicate_news(title, existing_item.get("titulli", "")):
                    is_duplicate = True; break
            if is_duplicate: continue

            image_url = ""
            summary = entry.get("summary", "")
            if "media_content" in entry and entry.media_content: image_url = entry.media_content[0].get("url", "")
            if not image_url and "links" in entry:
                for l in entry.links:
                    if l.get("type", "").startswith("image") or l.get("rel", "") == "enclosure": image_url = l.get("href", ""); break
            if not image_url:
                match = re.search(r'<img[^>]+src="([^">]+)"', summary)
                if match: image_url = match.group(1)
            if not image_url and link:
                try:
                    html = urllib.request.urlopen(urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'}), timeout=5).read().decode('utf-8', errors='ignore')
                    match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    if match: image_url = match.group(1)
                except: pass
            if not image_url: continue

            full_text = fetch_full_text(link)
            if len(full_text) < 200: continue

            eshte_balline = kontrollo_ballinen_e_burimit(link)

            ai_result = gjenero_kategori_dhe_hashtags(title, full_text)
            time.sleep(3)

            if ai_result:
                kategoria = ai_result.get("kategoria", "Lajme")
                if kategoria == "Kalo": continue

                hashtags = ai_result.get("hashtags", "")
                titulli_final = title
                teksti_i_pastruar = full_text
                
                paragrafet_temp = [p.strip() for p in teksti_i_pastruar.split('\n') if p.strip()]
                
                if paragrafet_temp:
                    ngjasia = difflib.SequenceMatcher(None, paragrafet_temp[0].lower(), titulli_final.lower()).ratio()
                    if ngjasia > 0.8 or paragrafet_temp[0].lower() in titulli_final.lower() or titulli_final.lower() in paragrafet_temp[0].lower():
                        paragrafet_temp.pop(0) 
                
                junk_keywords_start = ["advertisement", "reklamë", "reklama", "lexo edhe", "lexo po ashtu"]
                while paragrafet_temp and (len(paragrafet_temp[0]) < 25 or any(j in paragrafet_temp[0].lower() for j in junk_keywords_start)):
                    paragrafet_temp.pop(0)
                    
                junk_keywords_end = ["minuta më parë", "orë më parë", "ditë më parë", "top lajme", "reklamo", "promo", "jobs", "real estate", "kampionati", "na ndiqni", "facebook", "twitter", "instagram", "tiktok"]
                
                # Fshi nga fundi te gjithe paragrafet koti
                while paragrafet_temp:
                    last_p = paragrafet_temp[-1].strip()
                    lower_last = last_p.lower()
                    is_junk = False
                    
                    if any(kw in lower_last for kw in junk_keywords_end): is_junk = True
                    elif len(last_p) < 40 and not last_p.endswith(('.', '!', '?', '"', "'", '”', '“')): is_junk = True
                    elif re.fullmatch(r'[/\\]?\s*(telegrafi|indeksonline|gazeta express|gazetaexpress|express|klan kosova|klankosova|rtsh|rtk)\s*[/\\]?\.?', lower_last): is_junk = True
                        
                    if is_junk: paragrafet_temp.pop()
                    else: break
                        
                # Fshirja brutale e etiketave kudo qe mund te jene ngjitur ne fund te fjalisë (psh "/GazetaExpress/")
                regex_pattern = r'[/\\]?\s*(Telegrafi|Indeksonline|Gazeta Express|GazetaExpress|Express|Klan Kosova|KlanKosova|RTSH|RTK|RTSh)\s*[/\\]?\.?$'
                for i in range(len(paragrafet_temp)):
                    paragrafet_temp[i] = re.sub(regex_pattern, '', paragrafet_temp[i], flags=re.IGNORECASE).strip()

                teksti_i_pastruar = "\n".join(paragrafet_temp)
                slug_final = krijo_slug(titulli_final)
                
                article = {
                    "titulli": titulli_final,
                    "permbajtja": teksti_i_pastruar,
                    "kategoria": kategoria,
                    "imazhi": image_url,
                    "koha": (datetime.now() + timedelta(hours=2)).strftime("%d/%m/%Y %H:%M"),
                    "link_origjinal": link,
                    "slug": slug_final,
                    "eshte_balline": eshte_balline
                }
                
                linku_fb = f"https://zanidigjital.com/lajme/{slug_final}"
                
                if paragrafet_temp: paragrafi_pare = paragrafet_temp[0]
                else: paragrafi_pare = titulli_final
                    
                mesazhi_fb = f"{paragrafi_pare}\n\n{hashtags}".strip() if hashtags else paragrafi_pare
                
                fb_posts_queue.append({"mesazhi": mesazhi_fb, "linku": linku_fb, "eshte_balline": eshte_balline})
                new_entries.append(article)
                existing_links.add(link)
                
                lajme_te_perpunuara += 1

    updated_news = new_entries + existing_news
    
    if new_entries:
        save_news(updated_news)
        krijo_rss(updated_news)
        krijo_sitemap(updated_news)
        for article in new_entries: 
            gjenero_artikullin_html(article, updated_news)

    gjenero_lajmet_manuale(updated_news)

    os.system('git config user.email "action@github.com"')
    os.system('git config user.name "GitHub Actions"')
    os.system('git add .')
    
    status = os.system('git diff-index --quiet HEAD')
    if status != 0:
        os.system('git commit -m "Rregullimi i Llama-3.1 dhe Slasheve"')
        os.system('git pull --rebase')
        os.system('git push')
        
    if new_entries:
        fb_posts_queue.sort(key=lambda x: x["eshte_balline"], reverse=True)
        time.sleep(150) 
        for post in fb_posts_queue[:2]:
            posto_ne_facebook(post["mesazhi"], post["linku"])
            time.sleep(5)

if __name__ == "__main__":
    main()
