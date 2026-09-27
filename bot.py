import os
import json
import feedparser
import google.generativeai as genai
from datetime import datetime

# Lidhja me Google Gemini (Çelësi merret në mënyrë të sigurt nga GitHub)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

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
    # Ruajmë maksimumi 60 lajmet më të fundit që portali të jetë i shpejtë
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(news_list[:60], f, ensure_ascii=False, indent=2)

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
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gabim: {e}")
        return None

def main():
    existing_news = load_news()
    existing_links = {item.get("link_origjinal") for item in existing_news}
    new_entries = []

    for feed_url in RSS_FEEDS:
        parsed = feedparser.parse(feed_url)
        # Skanon 4 lajmet e fundit për çdo portal (në total 12 lajme në çdo kontroll)
        for entry in parsed.entries[:4]: 
            link = entry.get("link", "")
            if link in existing_links:
                continue

            title = entry.get("title", "")
            summary = entry.get("summary", "")

            image_url = ""
            if "media_content" in entry and len(entry.media_content) > 0:
                image_url = entry.media_content[0].get("url", "")
            elif "links" in entry:
                for l in entry.links:
                    if l.get("type", "").startswith("image"):
                        image_url = l.get("href", "")
                        break

            print(f"Duke përpunuar: {title}")
            ai_result = rewrite_with_ai(title, summary)

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
        print(f"Sukses! U shtuan {len(new_entries)} lajme të reja në Zani Digjital.")
    else:
        print("S'ka lajme të reja për momentin.")

if __name__ == "__main__":
    main()
