import os
import json
import feedparser
import time
import re
import urllib.request
import difflib
from groq import Groq
from datetime import datetime, timedelta

# Marrim çelësin e vetëm të Groq
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("Gabim: Nuk u gjet GROQ_API_KEY!")
    exit()

client = Groq(api_key=api_key)

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
        json.dump(news_list[:2000], f, ensure_ascii=False, indent=2)

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
    
    try:
        # Përdorim modelin e ri Llama 3.3 që është plotësisht aktiv
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
        )
        text = chat_completion.choices[0].message.content.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
        return json.loads(text)
        
    except Exception as e:
        print(f"❌ Gabim nga Groq AI: {e}")
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

            print(f"\nDuke përpunuar me Groq: {title}")
            ai_result = rewrite_with_ai(title, summary)
            
            # Kemi vendosur vetëm 2 sekonda pritje, Groq është rrufe!
            time.sleep(2)

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
        print(f"\nSukses! U shtuan {len(new_entries)} lajme të reja.")
    else:
        print("\nS'ka lajme të reja.")

if __name__ == "__main__":
    main()
