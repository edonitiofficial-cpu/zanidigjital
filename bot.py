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
