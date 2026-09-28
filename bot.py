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

def fetch_full_text(url):
    """Hyn në faqen origjinale dhe nxjerr tekstin e plotë të artikullit"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        # Nxjerrim vetëm përmbajtjen brenda paragrafëve <p>
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
        # Pastrojmë tag-et e tjera HTML brenda paragrafëve
        text = " ".join([re.sub(r'<[^>]+>', '', p).strip() for p in paragraphs])
        # Limitojmë në ~800 fjalë për të mos mbingarkuar Groq
        words = text.split()
        if len(words) < 20: 
            return ""
        return " ".join(words[:800])
    except Exception as e:
        return ""

def rewrite_with_ai(original_title, full_text, original_summary):
    # Nëse s'ka tekst të plotë, përdorim përmbledhjen e RSS
    text_to_process = full_text if len(full_text) > 100 else original_summary
    
    prompt = f"""
    Je gazetar profesionist për portalin "ZaniDigjital". Rishkruaj këtë lajm në shqip, duke u bazuar në tekstin e plotë të mëposhtëm, pa lënë gjurmë kopjimi.
    
    Titulli origjinal: {original_title}
    Teksti: {text_to_process}

    Më kthe VETËM një format JSON fiks si ky më poshtë:
    {{
      "titulli": "Titulli i ri tërheqës",
      "permbajtja": "Teksti i rishkruar profesionalisht dhe i plotë (rreth 3-4 paragrafë).",
      "kategoria": "Zgjidh VETËM njërën nga: Lajme, Kosovë, Politikë, Ekonomi, Sport, Botë, Kulturë, Teknologji, Auto, Çka ka të re sot?, Shpjegoje shkurt, Në xhepin tand, A e keni ditë?, Hulumtime"
    }}
    """
    
    # Sistemi i ri mbrojtës nga Limitimet (Provo 3 herë)
    for attempt in range(1, 4):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="openai/gpt-oss-120b",
                temperature=0.5,
            )
            text = chat_completion.choices[0].message.content.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
            return json.loads(text)
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                print(f"⚠️ Groq po kërkon pushim (429). Po pres 40 sekonda (Përpjekja {attempt}/3)...")
                time.sleep(40)
            else:
                print(f"❌ Gabim nga Groq AI: {e}")
                return None
                
    print("❌ Dështoi pas 3 përpjekjesh. Po e anashkalojmë këtë lajm.")
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

            print(f"\nDuke përpunuar: {title}")
            
            # Hyn në faqen origjinale dhe merr artikullin e plotë!
            full_text = fetch_full_text(link)
            
            ai_result = rewrite_with_ai(title, full_text, summary)
            
            # Pauzë 5 sekonda mes çdo lajmi për të qenë të sigurt nga limitet
            time.sleep(5)

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
