import os
import json
import feedparser
import time
import re
import urllib.request
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

# --- FUNKSIONI I RI PËR URL SLUG ---
def krijo_slug(titulli):
    if not titulli:
        return ""
    slug = titulli.lower()
    slug = slug.replace('ë', 'e').replace('ç', 'c')
    slug = re.sub(r'[^a-z0-9 -]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

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
        print(f"Gabim gjatë nxjerrjes së tekstit: {e}")
        return ""

def rewrite_with_ai(original_title, full_text):
    # ==========================================
    # FAZA 1: GJENERIMI BAZË (Përkthimi faktik)
    # ==========================================
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
                print(f"⚠️ Limit i arritur (Faza 1).")
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

    # ==========================================
    # FAZA 2: PROOFREADING GRAMATIKOR
    # ==========================================
    permbajtja_e_pare = lajmi_baze.get("permbajtja", "")
    
    prompt_faza_2 = f"""
    Ti je një Profesor i Gjuhës Shqipe dhe Redaktor Gjuhësor strikt.
    KORRIGJO vetëm gabimet gramatikore dhe logjike në këtë tekst, PA NDRYSHUAR FAKTET apo KUPTIMIN.
    
    RREGULLAT E KORRIGJIMIT:
    1. RASAT: Ndreq lakimin e emrave (psh. "uron Edon Zhegrovës" JO "uron Zhegrovan").
    2. KOHËT E FOLJEVE:
       - Ngjarje e mbaruar = e kaluara ("fitoi", jo "fiton").
       - Ngjarje në zhvillim = e tashmja.
       - Mos ndërro kohët e foljeve pa arsye!
    3. NUMRI DHE VETA: Folja duhet të përshtatet ("tre lojtarët shënuan" JO "shënoi").
    4. SINTAKSA: Zëvendëso fjalitë që duken si "Google Translate" me shqipe natyrale gazetareske.
    
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
        print(f"⚠️ Faza e Proofreading dështoi. Po përdorim tekstin nga Faza 1. Gabimi: {e}")
        
    lajmi_baze["permbajtja"] = permbajtja_finale
    return lajmi_baze

def main():
    existing_news = load_news()
    existing_links = {item.get("link_origjinal") for item in existing_news}
    new_entries = []
    
    lajme_te_perpunuara = 0
    MAX_LAJME = 5

    for feed_url in RSS_FEEDS:
        if lajme_te_perpunuara >= MAX_LAJME:
            break
            
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries[:10]: 
            if lajme_te_perpunuara >= MAX_LAJME:
                print(f"\n🛑 U arrit limiti prej {MAX_LAJME} lajmesh për këtë ekzekutim.")
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
                print(f"Anashkalohet (Lajm i ngjashëm): {title}")
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
                print(f"Anashkalohet (Nuk ka foto): {title}")
                continue

            print(f"\nDuke përpunuar: {title}")
            
            full_text = fetch_full_text(link)
            
            if len(full_text) < 300:
                print("Anashkalohet: Teksti është shumë i shkurtër.")
                continue

            ai_result = rewrite_with_ai(title, full_text)
            
            time.sleep(3)

            if ai_result:
                titulli_final = ai_result.get("titulli")
                
                # --- SHTESA E RE: Ruajtja e SLUG në JSON ---
                slug_final = krijo_slug(titulli_final)
                
                article = {
                    "titulli": titulli_final,
                    "permbajtja": ai_result.get("permbajtja"),
                    "kategoria": ai_result.get("kategoria", "Lajme"),
                    "imazhi": image_url,
                    "koha": (datetime.now() + timedelta(hours=2)).strftime("%d/%m/%Y %H:%M"),
                    "link_origjinal": link,
                    "slug": slug_final # Linku profesional ruhet këtu!
                }
                new_entries.append(article)
                existing_links.add(link)
                lajme_te_perpunuara += 1

    if new_entries:
        updated_news = new_entries + existing_news
        save_news(updated_news)
        print(f"\nSukses! U shtuan {len(new_entries)} lajme të reja.")
    else:
        print("\nS'ka lajme të reja për momentin.")

if __name__ == "__main__":
    main()
