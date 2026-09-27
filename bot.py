import os
import json
import feedparser
import time
import re
import urllib.request
from google import genai
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Portalet nga ku do marrim lajmet
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
    # Kapaciteti i rritur në 100 lajme
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(news_list[:100], f, ensure_ascii=False, indent=2)

def rewrite_with_ai(original_title, original_summary):
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
    
    modelet = ['gemini-3.8-flash']
    
    for emri_modelit in modelet:
        try:
            response = client.models.generate_content(
                model=emri_modelit,
                contents=prompt
            )
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
            return json.loads(text)
        except Exception as e:
            print(f"Modeli {emri_modelit} nuk punoi. Arsyeja nga Google: {e}")
            continue
            
    print("Asnjë model nuk u gjet i vlefshëm.")
    return None

def main():
    existing_news = load_news()
    existing_links = {item.get("link_origjinal") for item in existing_news}
    new_entries = []

    for feed_url in RSS_FEEDS:
        parsed = feedparser.parse(feed_url)
        # Rritja e sasisë: Provon të marrë 15 lajme të fundit nga çdo portal
        for entry in parsed.entries[:15]: 
            link = entry.get("link", "")
            if link in existing_links:
                continue

            title = entry.get("title", "")
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
            
            # Anashkalon vetëm lajmet pa fotografi origjinale
            if not image_url:
                print(f"Lajmi u anashkalua sepse nuk kishte foto origjinale: {title}")
                continue

            print(f"\nDuke përpunuar: {title}")
            ai_result = rewrite_with_ai(title, summary)
            
            # PAUZA E ARTË (15 Sekonda) - Kjo i jep kohë robotit dhe nuk na bllokon kurrë nga Google
            time.sleep(15)

            if ai_result:
                article = {
                    "titulli": ai_result.get("titulli"),
                    "permbajtja": ai_result.get("permbajtja"),
                    "kategoria": ai_result.get("kategoria", "Lajme"),
                    "imazhi": image_url,
                    "koha": datetime.now().strftime("%d/%m/%Y %H:%M"),
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
