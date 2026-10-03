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

# --- SISTEMI I RROTULLIMIT TË ÇELËSAVE (API ROTATION) ---
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

RSS_FEEDS = [
    "https://telegrafi.com/feed/",
    "https://indeksonline.net/feed/",
    "https://www.gazetaexpress.com/feed/"
]

DB_FILE = "lajmet.json"

# --- FUNKSIONI PËR URL SLUG ---
def krijo_slug(titulli):
    if not titulli:
        return ""
    slug = titulli.lower()
    slug = slug.replace('ë', 'e').replace('ç', 'c')
    slug = re.sub(r'[^a-z0-9 -]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

# --- FUNKSIONET PËR DIZAJNIN E NGJYRAVE ---
def get_category_bg(cat):
    colors = { 'Sport': 'bg-green-600', 'Politikë': 'bg-red-600', 'Teknologji': 'bg-blue-600', 'Tech': 'bg-blue-600', 'Ekonomi': 'bg-yellow-600', 'Lajme': 'bg-black' }
    return colors.get(cat, 'bg-black')

def get_category_text(cat):
    colors = { 'Sport': 'text-green-600', 'Politikë': 'text-red-600', 'Teknologji': 'text-blue-600', 'Tech': 'text-blue-600', 'Ekonomi': 'text-yellow-600', 'Lajme': 'text-black' }
    return colors.get(cat, 'text-black')

# --- GJENERATORI STATIC I LAJMIT (MAGJIA E RE) ---
def gjenero_artikullin_html(article, te_gjitha_lajmet):
    slug = article["slug"]
    titulli = article["titulli"].replace('"', '&quot;')
    imazhi = article["imazhi"]
    permbajtja = article["permbajtja"]
    kategoria = article.get("kategoria", "Lajme")
    koha = article.get("koha", "")
    
    # ADRESA E PASTËR!
    url_baze = f"https://zanidigjital.com/lajme/{slug}"
    
    permbajtja_meta = permbajtja[:150].replace('"', '&quot;') + "..."
    permbajtja_html = "".join([f"<p>{p.strip()}</p>" for p in permbajtja.split('\n') if p.strip()])
    cat_bg = get_category_bg(kategoria)

    # Ndërtojmë sugjerimet anësore ("Lexo më shumë")
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
                <h4 class="text-[14px] font-bold text-gray-800 leading-snug group-hover:underline transition line-clamp-2 mt-1">
                    {s.get('titulli')}
                </h4>
            </div>
        </a>"""
        count += 1

    folder_path = "lajme"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # FUSIM TË GJITHË KODIN NGA ARTIKULLI.HTML KËTU:
    html_content = f"""<!DOCTYPE html>
<html lang="sq">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulli} - Zani Digjital</title>
    
    <meta name="description" content="{permbajtja_meta}">
    <link rel="canonical" href="{url_baze}">
    
    <!-- FACEBOOK / OPEN GRAPH -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="{url_baze}">
    <meta property="og:title" content="{titulli}">
    <meta property="og:description" content="{permbajtja_meta}">
    <meta property="og:image" content="{imazhi}">
    <meta property="og:site_name" content="Zani Digjital">

    <!-- TWITTER -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="{url_baze}">
    <meta name="twitter:title" content="{titulli}">
    <meta name="twitter:description" content="{permbajtja_meta}">
    <meta name="twitter:image" content="{imazhi}">

    <link rel="icon" type="image/png" href="../zanidigjitalfavicon.png">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&display=swap');
        body {{ font-family: 'Inter', sans-serif; background-color: #F8F9FA; }}
        .permbajtja p {{ margin-bottom: 1.5rem; }}
        .line-clamp-2 {{ display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
    </style>
</head>
<body class="text-gray-900 antialiased">

    <!-- HEADER -->
    <header class="bg-white sticky top-0 z-50 shadow-sm border-b border-gray-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div class="flex flex-col md:flex-row justify-between items-center">
                <a href="https://zanidigjital.com/" class="flex-shrink-0 mb-4 md:mb-0">
                    <img src="../zanidigjital.png" alt="ZaniDigjital Logo" class="h-16 object-contain" onerror="this.src='https://via.placeholder.com/200x50/ffffff/000000?text=ZANI+DIGJITAL+LOGO'">
                </a>
                
                <nav class="flex flex-wrap justify-center gap-4 sm:gap-6 font-semibold text-gray-600">
                    <a href="https://zanidigjital.com/" class="hover:text-black transition">Ballina</a>
                    <a href="https://zanidigjital.com/index.html?kategoria=Lajme" class="hover:text-black transition">Lajme</a>
                    <a href="https://zanidigjital.com/index.html?kategoria=Politikë" class="hover:text-black transition">Politikë</a>
                    <a href="https://zanidigjital.com/index.html?kategoria=Ekonomi" class="hover:text-black transition">Ekonomi</a>
                    <a href="https://zanidigjital.com/index.html?kategoria=Sport" class="hover:text-black transition">Sport</a>
                    <a href="https://zanidigjital.com/index.html?kategoria=Teknologji" class="hover:text-black transition">Teknologji</a>
                </nav>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8 flex flex-col lg:flex-row gap-8">
        <article class="lg:w-2/3 bg-white p-6 lg:p-10 rounded-2xl shadow-sm border border-gray-100 relative">
            <a href="https://zanidigjital.com/" class="inline-flex items-center text-sm font-bold text-gray-500 hover:text-black mb-6 transition">
                ← Kthehu te Ballina
            </a>
            
            <div class="flex items-center gap-4 mb-4 font-bold">
                <span class="{cat_bg} text-white px-3 py-1 rounded text-xs uppercase tracking-wider">{kategoria}</span>
                <span class="text-gray-400 text-sm font-medium">{koha}</span>
            </div>
            
            <h1 class="text-3xl md:text-5xl font-black text-gray-900 leading-tight mb-6">{titulli}</h1>
            
            <!-- SHARE BUTONAT -->
            <div class="flex flex-wrap gap-2 mb-8">
                <a href="https://www.facebook.com/sharer/sharer.php?u={url_baze}" target="_blank" class="bg-[#1877F2] text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-blue-700 transition flex items-center gap-2">
                    <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.469h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.469h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                    Ndaj
                </a>
                <a href="https://twitter.com/intent/tweet?url={url_baze}&text={urllib.parse.quote(titulli)}" target="_blank" class="bg-black text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-gray-800 transition flex items-center gap-2">
                    <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                    Posto
                </a>
                <a href="https://api.whatsapp.com/send?text={urllib.parse.quote(titulli)}%20{url_baze}" target="_blank" class="bg-[#25D366] text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-green-600 transition flex items-center gap-2">
                    <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M12.031 0C5.385 0 0 5.385 0 12.031c0 2.126.549 4.156 1.594 5.969L.25 24l6.188-1.594A11.966 11.966 0 0012.031 24c6.646 0 12.031-5.385 12.031-12.031S18.677 0 12.031 0zm3.625 17.156c-.156.469-.938.875-1.344.938-.375.063-.844.094-2.281-.469-1.75-.688-2.875-2.5-3.25-3C8.406 14.156 7.5 12.688 7.5 11.156c0-1.563.813-2.313 1.094-2.625.281-.313.625-.375.844-.375.219 0 .438 0 .625.031.188.031.438-.063.688.531.25.625.875 2.125.938 2.25.063.156.125.344.031.531-.094.188-.156.281-.313.469-.156.188-.344.344-.469.531-.156.156-.313.344-.125.656.188.344.813 1.375 1.75 2.188 1.219 1.031 2.25 1.375 2.563 1.531.313.156.5.125.688-.094.188-.25.813-.969 1.031-1.313.219-.344.438-.281.719-.188.281.094 1.781.844 2.094 1 .313.156.5.219.594.344.094.156.094.656-.063 1.125z"/></svg>
                    Dërgo
                </a>
            </div>

            <img src="{imazhi}" class="w-full h-auto max-h-[500px] rounded-xl object-cover mb-10 shadow-sm border border-gray-100" alt="{titulli}">
            
            <div class="permbajtja text-[18px] text-gray-800 leading-relaxed font-medium">
                {permbajtja_html}
            </div>
        </article>

        <aside class="lg:w-1/3 space-y-6">
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                <h3 class="font-extrabold text-lg mb-4 text-gray-900 border-b border-gray-100 pb-3 flex items-center gap-2">
                    <span class="bg-black text-white px-2 py-1 rounded text-xs uppercase">Të rejat</span> Lexo më shumë
                </h3>
                <div class="space-y-4">
                    {sugjerime_html}
                </div>
            </div>

            <!-- Hapësira Reklamuese -->
            <a href="#" target="_blank" class="block rounded-2xl overflow-hidden shadow-sm border border-gray-100 hover:opacity-90 hover:shadow-md transition duration-300 relative">
                <span class="absolute top-2 right-2 bg-yellow-400 text-black text-[10px] font-bold px-2 py-1 rounded uppercase z-10">Sponsorizuar</span>
                <img src="../burger.png" class="w-full h-auto object-cover" onerror="this.src='https://images.unsplash.com/photo-1568901346375-23c9450c58cd?q=80&w=400&auto=format&fit=crop'">
            </a>
            <a href="#" target="_blank" class="block rounded-2xl overflow-hidden shadow-sm border border-gray-100 hover:opacity-90 hover:shadow-md transition duration-300 relative">
                <span class="absolute top-2 right-2 bg-yellow-400 text-black text-[10px] font-bold px-2 py-1 rounded uppercase z-10">Sponsorizuar</span>
                <img src="../chair.png" class="w-full h-auto object-cover" onerror="this.src='https://images.unsplash.com/photo-1505843490538-5133c6c7d0e1?q=80&w=400&auto=format&fit=crop'">
            </a>
        </aside>
    </main>

    <footer class="bg-white border-t border-gray-200 py-8 mt-8">
        <div class="max-w-7xl mx-auto px-4 text-center">
            <p class="text-gray-500 text-sm font-medium">&copy; 2026 Zani Digjital. Të gjitha të drejtat e rezervuara.</p>
        </div>
    </footer>
</body>
</html>"""

    file_path = os.path.join(folder_path, f"{slug}.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

def krijo_rss(lajmet):
    rss_content = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Zani Digjital</title>
  <link>https://zanidigjital.com/</link>
  <description>Lajmet e fundit nga Zani Digjital</description>
"""
    for lajm in lajmet[:15]:
        slug = lajm.get("slug", "")
        titulli = lajm.get("titulli", "").replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        linku = f"https://zanidigjital.com/lajme/{slug}"
        pershkrimi = lajm.get("permbajtja", "")[:150].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') + "..."
        
        rss_content += f"""
  <item>
    <title>{titulli}</title>
    <link>{linku}</link>
    <description>{pershkrimi}</description>
  </item>
"""
    rss_content += "</channel>\n</rss>"
    
    with open("rss.xml", "w", encoding="utf-8") as f:
        f.write(rss_content)

def posto_ne_facebook(mesazhi, linku):
    fb_token = os.environ.get("FACEBOOK_PAGE_TOKEN")
    if not fb_token:
        print("⚠ FACEBOOK_PAGE_TOKEN nuk është vendosur te GitHub Secrets. Postimi u anashkalua.")
        return
    
    url = "https://graph.facebook.com/v19.0/me/feed"
    data = urllib.parse.urlencode({
        "message": mesazhi,
        "link": linku,
        "access_token": fb_token
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data)
        response = urllib.request.urlopen(req)
        print(f"✅ Lajmi u postua me sukses në Facebook! ({linku})")
    except Exception as e:
        print(f"❌ Gabim gjatë postimit në Facebook: {e}")

# ----------------------------------------

def load_news():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_news(news_list):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(news_list[:2000], f, ensure_ascii=False, indent=2)

def fetch_full_text(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False, no_fallback=True)
            if text:
                words = text.split()
                return " ".join(words[:600])
        return ""
    except Exception as e:
        return ""

def rewrite_with_ai(original_title, full_text):
    prompt_faza_1 = f"""
    Je Kryeredaktori kryesor i portalit të lajmeve "ZaniDigjital".
    Detyra: Rishkruaj lajmin në shqip bazuar VETËM në burim.
    
    RREGULLA FAKTIKE (CRITICAL):
    - MOS shto informacione, emra, data, apo ngjarje.
    - Ruaj 100% saktësinë e deklaratave.
    
    STRUKTURA:
    - 3-5 paragrafë të shkurtër (max 3 fjali secili).
    - Përdor dy hapësira (\\n\\n) për të ndarë paragrafët.
    
    TITULLI: Krijo një titull të qartë, faktik, pa clickbait.
    
    KATEGORIA: Zgjidh VETËM njërën: Lajme, Kosovë, Politikë, Ekonomi, Sport, Botë, Kulturë, Teknologji, Auto.
    
    Titulli origjinal: {original_title}
    Teksti origjinal: {full_text}
    
    KTHE VETËM një JSON valid fiks kështu:
    {{
      "titulli": "...",
      "permbajtja": "...",
      "kategoria": "..."
    }}
    """
    
    lajmi_baze = None
    
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_faza_1}],
                model="openai/gpt-oss-120b",
                temperature=0.1,
            )
            text = response.choices[0].message.content.strip()
            
            if text.startswith("```json"): text = text[7:-3].strip()
            elif text.startswith("```"): text = text[3:-3].strip()
            
            lajmi_baze = json.loads(text)
            break 
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                if len(valid_keys) > 1:
                    switch_api_key()
                    time.sleep(2)
                else:
                    time.sleep(40)
            elif "413" in error_msg:
                return None
            else:
                return None
                
    if not lajmi_baze:
        return None

    permbajtja_e_pare = lajmi_baze.get("permbajtja", "")
    
    prompt_faza_2 = f"""
    Ti je një Redaktor Gjuhësor Shqiptar profesionist me shumë përvojë në gazetari.
    Detyra jote: KORRIGJO këtë tekst që aktualisht tingëllon si përkthim i dobët i Google Translate.
    
    RREGULLAT E KRYESORE:
    1. KORRIGJO GJINITË DHE RASAT: Emrat duhet të përshtaten saktë. (P.sh., gjej dhe ndreq gabime si "lajm e mirë" -> "lajm i mirë", ose "parashikoi Barcelona" -> "parashikoi Barcelonën").
    2. SHMANG PËRKTHIMET FOTOGRAFIKE NGA ANGLISHTJA: Fjalitë duhet të rrjedhin natyrshëm në shqip. Ndrysho strukturën e fjalisë nëse tingëllon "robotike".
    3. LAKIMI I EMRAVE: Sigurohu që emrat e përveçëm të jenë të lakuar saktë (p.sh., "vendimi i Ramës", jo "vendimi i Rama").
    4. MOS shto asnjë informacion, fakt apo emër të ri. Vetëm rregullo gramatikën dhe logjikën e atyre që janë.
    
    KTHE VETËM TEKSTIN E KORRIGJUAR, pa asnjë shpjegim tjetër, pa markdown, pa "Ja teksti".
    Teksti:
    {permbajtja_e_pare}
    """
    
    permbajtja_finale = permbajtja_e_pare 
    
    try:
        response_2 = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_faza_2}],
            model="openai/gpt-oss-120b",
            temperature=0.1, 
        )
        rezultati_korrigjuar = response_2.choices[0].message.content.strip()
        
        if len(rezultati_korrigjuar) > 50 and "Nuk ka gabime" not in rezultati_korrigjuar:
            permbajtja_finale = rezultati_korrigjuar
            
    except Exception as e:
        pass
        
    lajmi_baze["permbajtja"] = permbajtja_finale
    return lajmi_baze

def main():
    existing_news = load_news()
    existing_links = {item.get("link_origjinal") for item in existing_news}
    new_entries = []
    
    fb_posts_queue = []
    lajme_te_perpunuara = 0
    MAX_LAJME = 5

    for feed_url in RSS_FEEDS:
        if lajme_te_perpunuara >= MAX_LAJME:
            break
            
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries[:10]: 
            if lajme_te_perpunuara >= MAX_LAJME:
                break
                
            link = entry.get("link", "")
            title = entry.get("title", "")
            
            if link in existing_links:
                continue

            is_duplicate = False
            for existing_item in existing_news + new_entries:
                existing_title = existing_item.get("titulli", "")
                similarity = difflib.SequenceMatcher(None, title.lower(), existing_title.lower()).ratio()
                if similarity > 0.55:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue

            summary = entry.get("summary", "")
            image_url = ""
            
            if "media_content" in entry and len(entry.media_content) > 0:
                image_url = entry.media_content[0].get("url", "")
            
            if not image_url and "links" in entry:
                for l in entry.links:
                    if l.get("type", "").startswith("image") or l.get("rel", "") == "enclosure":
                        image_url = l.get("href", "")
                        break
                        
            if not image_url:
                match = re.search(r'<img[^>]+src="([^">]+)"', summary)
                if match:
                    image_url = match.group(1)
            
            if not image_url and "content" in entry and len(entry.content) > 0:
                match = re.search(r'<img[^>]+src="([^">]+)"', entry.content[0].value)
                if match:
                    image_url = match.group(1)
                    
            if not image_url and link:
                try:
                    req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
                    html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8', errors='ignore')
                    match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    if match:
                        image_url = match.group(1)
                except Exception as e:
                    pass
            
            if not image_url:
                continue

            print(f"\nDuke përpunuar: {title}")
            full_text = fetch_full_text(link)
            if len(full_text) < 300: continue

            ai_result = rewrite_with_ai(title, full_text)
            time.sleep(3)

            if ai_result:
                titulli_final = ai_result.get("titulli")
                slug_final = krijo_slug(titulli_final)
                
                article = {
                    "titulli": titulli_final,
                    "permbajtja": ai_result.get("permbajtja"),
                    "kategoria": ai_result.get("kategoria", "Lajme"),
                    "imazhi": image_url,
                    "koha": (datetime.now() + timedelta(hours=2)).strftime("%d/%m/%Y %H:%M"),
                    "link_origjinal": link,
                    "slug": slug_final
                }
                
                # ADRESA E PASTËR E FACEBOOK-UT
                linku_fb = f"https://zanidigjital.com/lajme/{slug_final}"
                
                permbajtja_plote = ai_result.get("permbajtja", "")
                paragrafet = [p.strip() for p in permbajtja_plote.split('\n') if p.strip()]
                paragrafi_pare = paragrafet[0] if paragrafet else ""
                
                fb_posts_queue.append({
                    "mesazhi": paragrafi_pare,
                    "linku": linku_fb
                })
                
                new_entries.append(article)
                existing_links.add(link)
                lajme_te_perpunuara += 1

    if new_entries:
        updated_news = new_entries + existing_news
        save_news(updated_news)
        krijo_rss(updated_news)
        
        # TANI GJENEROJMË KODIN HTML (ME SUGJERIMET E LAJMEVE TË TJERA)
        print("\nDuke gjeneruar faqet statike të lajmeve (HTML)...")
        for article in new_entries:
            gjenero_artikullin_html(article, updated_news)
        
        print(f"\nSukses! U shtuan dhe u gjeneruan {len(new_entries)} lajme të reja.")
        
        # E publikojmë faqen në GitHub
        print("\nDuke e dërguar kodin në GitHub...")
        os.system('git config user.email "action@github.com"')
        os.system('git config user.name "GitHub Actions"')
        os.system('git add .')
        os.system('git commit -m "U shtuan lajme te reja statike automatikisht"')
        os.system('git push')
        
        # Presim që GitHub Pages të rifreskohet (80 sekonda)
        print("\n⏳ Presim 80 sekonda që faqja të bëhet live në internet (për të shmangur Error 404 në Facebook)...")
        time.sleep(80)
        
        # Postojmë në Facebook
        print("\nDuke i postuar në Facebook tani...")
        for post in fb_posts_queue:
            posto_ne_facebook(post["mesazhi"], post["linku"])
            time.sleep(3)
            
        print("\nProcesi përfundoi me sukses të plotë!")
    else:
        print("\nS'ka lajme të reja për momentin.")

if __name__ == "__main__":
    main()
