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

# --- SHTESAT E REJA PËR FACEBOOK & RSS ---
def krijo_html_per_facebook(article):
    slug = article["slug"]
    titulli = article["titulli"].replace('"', '&quot;')
    imazhi = article["imazhi"]
    permbajtja = article["permbajtja"][:150].replace('"', '&quot;') + "..."
    
    folder_path = "lajme"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    url_baze = f"https://edonitiofficial-cpu.github.io/zanidigjital/lajme/{slug}.html"
    
    html_content = f"""<!DOCTYPE html>
<html lang="sq">
<head>
    <meta charset="UTF-8">
    <meta property="og:title" content="{titulli}" />
    <meta property="og:image" content="{imazhi}" />
    <meta property="og:description" content="{permbajtja}" />
    <meta property="og:type" content="article" />
    <meta property="og:url" content="{url_baze}" />
    <meta http-equiv="refresh" content="0; url=../artikulli.html?lajmi={slug}">
    <title>{titulli}</title>
    <script>window.location.replace("../artikulli.html?lajmi={slug}");</script>
</head>
<body>
    <p>Duke hapur lajmin... <a href="../artikulli.html?lajmi={slug}">Kliko këtu nëse nuk hapet automatikisht</a>.</p>
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
  <link>https://edonitiofficial-cpu.github.io/zanidigjital/</link>
  <description>Lajmet e fundit nga Zani Digjital</description>
"""
    for lajm in lajmet[:15]:
        slug = lajm.get("slug", "")
        titulli = lajm.get("titulli", "").replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        linku = f"https://edonitiofficial-cpu.github.io/zanidigjital/lajme/{slug}.html"
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
        print("⚠️️ FACEBOOK_PAGE_TOKEN nuk është vendosur te GitHub Secrets. Postimi u anashkalua.")
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
    Ti je një Profesor i Gjuhës Shqipe dhe Redaktor Gjuhësor strikt.
    KORRIGJO vetëm gabimet gramatikore dhe logjike në këtë tekst.
    Nëse teksti është perfekt, ktheje ekzakt siç është.
    KTHE VETËM TEKSTIN E KORRIGJUAR, pa markdown, pa JSON, pa "Ja teksti".
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
    
    # LISTA E PRITJES PËR FACEBOOK
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
            
            if len(full_text) < 300:
                continue

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
                
                krijo_html_per_facebook(article)
                
                linku_fb = f"https://edonitiofficial-cpu.github.io/zanidigjital/lajme/{slug_final}.html"
                
                permbajtja_plote = ai_result.get("permbajtja", "")
                paragrafet = [p.strip() for p in permbajtja_plote.split('\n') if p.strip()]
                paragrafi_pare = paragrafet[0] if paragrafet else ""
                
                mesazhi_per_fb = f"{titulli_final}\n\n{paragrafi_pare}"
                
                # Ruajmë në listë për t'i postuar më vonë
                fb_posts_queue.append({
                    "mesazhi": mesazhi_per_fb,
                    "linku": linku_fb
                })
                
                new_entries.append(article)
                existing_links.add(link)
                lajme_te_perpunuara += 1

    if new_entries:
        updated_news = new_entries + existing_news
        save_news(updated_news)
        krijo_rss(updated_news)
        
        print(f"\nSukses! U shtuan {len(new_entries)} lajme të reja.")
        
        # SHTESA KRYESORE KËTU: E publikojmë faqen në GitHub
        print("\nDuke e dërguar kodin në GitHub...")
        os.system('git config user.email "action@github.com"')
        os.system('git config user.name "GitHub Actions"')
        os.system('git add .')
        os.system('git commit -m "U shtuan lajme te reja automatikisht"')
        os.system('git push')
        
        # Presim që GitHub Pages të rifreskohet
        print("\n⏳ Presim 80 sekonda që faqja të bëhet live në internet (për të shmangur Error 404 në Facebook)...")
        time.sleep(80)
        
        # Vetëm pasi ka dalë online, e postojmë
        print("\nDuke i postuar në Facebook tani...")
        for post in fb_posts_queue:
            posto_ne_facebook(post["mesazhi"], post["linku"])
            time.sleep(3)
            
        print("\nProcesi përfundoi me sukses të plotë!")
    else:
        print("\nS'ka lajme të reja për momentin.")

if __name__ == "__main__":
    main()
