import os
import json
import feedparser
import time
import re
import urllib.request
import difflib
from groq import Groq
from datetime import datetime, timedelta

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
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
        text = " ".join([re.sub(r'<[^>]+>', '', p).strip() for p in paragraphs])
        words = text.split()
        if len(words) < 20: 
            return ""
        return " ".join(words[:800])
    except Exception as e:
        return ""

def rewrite_with_ai(original_title, full_text, original_summary):
    text_to_process = full_text if len(full_text) > 100 else original_summary
    
    prompt = f"""
    Je Kryeredaktori kryesor i portalit të lajmeve "ZaniDigjital" në Kosovë. Ti menaxhon të gjitha rubrikat e portalit, përfshirë Politikë, Kosovë, Ekonomi, Sport, Botë, Kulturë, Teknologji, Auto dhe rubrikat e tjera.
    Detyra jote është ta rishkruash lajmin në gjuhën shqipe, në stil profesional të gazetarisë në Kosovë, duke u bazuar VETËM në informacionin që gjendet në tekstin origjinal.
    
    RREGULLA TË PANEGOCIUESHME PËR SAKTËSINË:
    MOS SHTO ASNJË INFORMACION që nuk gjendet në tekstin origjinal.
    MOS SHPIK emra, data, vende, deklarata, shifra, funksione, ngjarje apo detaje të tjera.
    MOS NDRYSHO kuptimin e asaj që është thënë në tekstin origjinal.
    Nëse teksti përmban deklarata të një personi, ruaje saktë kuptimin e deklaratës. Mos i atribuo personit diçka që nuk e ka thënë.
    Nëse një informacion nuk është i qartë në tekstin origjinal, MOS E PLOTËSO me hamendësim.
    Mos përdor njohuri nga jashtë tekstit origjinal për ta plotësuar lajmin.
    Mos krijo përfundime, analiza apo opinione të reja.
    Mos e ekzagjero lajmin dhe mos përdor formulime sensacionaliste që nuk mbështeten në tekst.
    Emrat e personave, institucioneve, partive, organizatave, qyteteve dhe vendeve duhet të ruhen saktë.
    Shifrat, datat, përqindjet, rezultatet dhe statistikat duhet të ruhen saktë.
    
    RREGULLA TË GJUHËS:
    Shkruaj në gjuhën shqipe të pastër, natyrale dhe me rrjedhshmëri logjike.
    Shkruaj në stilin e gazetarisë profesionale në Kosovë.
    NDALOHET RREPTËSISHT përkthimi fjalë-për-fjalë dhe përdorimi i anglicizmave kur ekziston një shprehje natyrale në shqip.
    Përshtati fjalitë në mënyrë që të tingëllojnë sikur janë shkruar fillimisht në shqip.
    Mos përdor fjalë të panevojshme vetëm për ta zgjatur tekstin.
    Mos përdor përsëritje të panevojshme të të njëjtit informacion.
    
    STRUKTURA E LAJMIT:
    Ndaje lajmin në 4 ose 5 paragrafë të shkurtër.
    Asnjë paragraf nuk guxon të ketë më shumë se 2 ose 3 fjali.
    Çdo paragraf duhet të ketë rrjedhë logjike me paragrafin paraprak.
    Paragrafi i parë duhet të paraqesë thelbin e lajmit.
    Paragrafët në vijim duhet të japin detajet kryesore sipas rëndësisë.
    Nëse ka deklarata, vendosi në kontekstin përkatës dhe mos ua ndrysho kuptimin.
    Mos përdor lista, pika, emoji apo tituj të brendshëm brenda përmbajtjes, përveç nëse ato janë të domosdoshme për kuptimin e lajmit.
    Përdor dy hapësira të reja (\\n\\n) për të ndarë qartë paragrafët.
    
    TITULLI:
    Krijo një titull të ri, profesional dhe të qartë.
    Titulli duhet të bazohet vetëm në informacionin e tekstit origjinal.
    Mos përdor tituj mashtrues ose "clickbait".
    Mos shto në titull informacione që nuk janë në tekst.
    Mos e bëj titullin të panevojshëm të gjatë.
    
    KATEGORIZIMI:
    Zgjidh VETËM njërën nga kategoritë e mëposhtme:
    Lajme, Kosovë, Politikë, Ekonomi, Sport, Botë, Kulturë, Teknologji, Auto, Çka ka të re sot?, Shpjegoje shkurt, Në xhepin tand, A e keni ditë?, Hulumtime
    Zgjidh kategorinë që përputhet më saktë me temën kryesore të lajmit.
    
    RREGULLA PËR RASTET E PAQARTA:
    Nëse teksti është shumë i shkurtër, MOS SHTO informacion për ta bërë më të gjatë.
    Nëse mungojnë të dhëna, puno vetëm me ato që janë dhënë.
    Nëse një fjali e tekstit origjinal është e paqartë, mos shpik interpretim.
    Nëse ka kundërthënie në tekst, ruaje informacionin pa krijuar një version të ri të fakteve.
    Nëse teksti nuk mjafton për 4 paragrafë të plotë, përdor më pak paragrafë në vend që të shpikësh informacion.
    
    Titulli origjinal:
    {original_title}
    
    Teksti origjinal:
    {text_to_process}
    
    Më kthe VETËM një objekt JSON valid, pa markdown, pa ```json dhe pa asnjë tekst tjetër.
    Formati duhet të jetë FIKS:
    {{
      "titulli": "Titulli i ri profesional",
      "permbajtja": "Paragrafi i parë.\\n\\nParagrafi i dytë.\\n\\nParagrafi i tretë.\\n\\nParagrafi i katërt.",
      "kategoria": "Njëra nga kategoritë e lejuara"
    }}
    """
    
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
                temperature=0.3,
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
            
            full_text = fetch_full_text(link)
            ai_result = rewrite_with_ai(title, full_text, summary)
            
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
