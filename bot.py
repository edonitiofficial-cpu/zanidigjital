import os
import json
import feedparser
import time
import re
import urllib.request
import difflib # Moduli i ri për të gjetur lajmet e ngjashme
from google import genai
from datetime import datetime, timedelta

api_keys = [
    os.environ.get("GEMINI_API_KEY"),
    os.environ.get("GEMINI_API_KEY_2"),
    os.environ.get("GEMINI_API_KEY_3"),
    os.environ.get("GEMINI_API_KEY_4"),
    os.environ.get("GEMINI_API_KEY_5")
]
api_keys = [k for k in api_keys if k]

current_key_index = 0
if not api_keys:
    print("Gabim: Nuk u gjet asnjë API Key!")
    exit()

client = genai.Client(api_key=api_keys[current_key_index])

RSS_FEEDS = [
    "https://telegrafi.com/feed/",
    "https://indeksonline.net/feed/",
    "https://www.gazetaexpress.com/feed/"
]

DB_FILE = "lajmet.json"

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
        json.dump(news_list[:100], f, ensure_ascii=False, indent=2)

def rewrite_with_ai(original_title, original_summary):
    global current_key_index, client
    
    prompt = f"""
    Je gazetar për portalin "ZaniDigjital". Rishkruaj këtë lajm në shqip, pa lënë gjurmë kopjimi.
    Titulli: {original_title}
    Përmbledhja: {original_summary}

    Më kthe VETËM një format JSON fiks si ky më poshtë:
    {{
      "titulli": "Titulli i ri tërheqës",
      "permbajtja": "Teksti i rishkruar profesionalisht (rreth 2-3 paragrafë).",
      "kategoria": "Zgjidh VETËM njërën nga këto sipas kontekstit: Lajme, Kosovë, Politikë, Ekonomi, Sport, Botë, Kulturë, Teknologji, Auto, Çka ka të re sot?, Shpjegoje shkurt, Në xhepin tand, A e keni ditë?, ose Hulumtime"
    }}
    """
    
    while current_key_index < len(api_keys):
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt
            )
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
            return json.loads(text)
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                print(f"⚠️ Çelësi {current_key_index + 1} u harxhua për sot. Po kaloj te çelësi tjetër...")
                current_key_index += 1
                if current_key_index < len(api_keys):
                    client = genai.Client(api_key=api_keys[current_key_index])
                    continue
                else:
                    print("❌ Të gjithë 5 çelësat u harxhuan për sot!")
                    return None
            else:
                print(f"Modeli dështoi nga një gabim tjetër: {e}")
                return None
                
    return None

def main():
    existing_news = load_news()
    existing_links = {item.get("link_origjinal") for item in existing_news}
    new_entries = []

    for feed_url in RSS_FEEDS:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries[:15]: 
            link = entry.get("link", "")
            title = entry.get("title", "")
            
            # Filtri 1: Bllokimi bazuar në Link
            if link in existing_links:
                continue

            # Filtri 2: Bllokimi bazuar në ngjashmërinë e Titujve (Zgjidhja jote)
            is_duplicate = False
            for existing_item in existing_news + new_entries:
                existing_title = existing_item.get("titulli", "")
                # Krahason titullin e ri me titujt në portal, nëse ngjashmëria është mbi 55% e bllokon
                similarity = difflib.SequenceMatcher(None, title.lower(), existing_title.lower()).ratio()
                if similarity > 0.55:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                print(f"Anashkalohet (Lajm i ngjashëm nga portal tjetër): {title}")
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
                print(f"Anashkalohet (Nuk ka foto origjinale): {title}")
                continue

            print(f"\nDuke përpunuar: {title}")
            ai_result = rewrite_with_ai(title, summary)
            
            time.sleep(15)

            if ai_result:
                article = {
                    "titulli": ai_result.get("titulli"),
                    "permbajtja": ai_result.get("permbajtja"),
                    "kategoria": ai_result.get("kategoria", "Lajme"),
                    "imazhi": image_url,
                    "koha": (datetime.now() + timedelta(hours=2)).strftime("%d/%m/%Y %H:%M"),
                    "link_origjinal": link
                }
                new_entries.append(article)
                existing_links.add(link)

    if new_entries:
        updated_news = new_entries + existing_news
        save_news(updated_news)
        print(f"\nSukses! U shtuan {len(new_entries)} lajme të reja në Zani Digjital.")
    else:
        print("\nS'ka lajme të reja për momentin.")

if __name__ == "__main__":
    main()
