"""Grounded municipality tagging; no model-generated places or inferred villages.

Canonical list: https://mapl.rks-gov.net/komunat/
"""
import re
import unicodedata


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value or '').lower()) if unicodedata.category(c) != 'Mn')


MUNICIPALITIES = {
    'Deçan': ['decan', 'decani', 'decanit'],
    'Dragash': ['dragash', 'dragashi', 'dragashit'],
    'Drenas': ['drenas', 'drenasi', 'drenasit', 'gllogoc', 'gllogocit', 'gllogovc', 'gllogovcit'],
    'Ferizaj': ['ferizaj', 'ferizaji', 'ferizajt'],
    'Fushë Kosovë': ['fushe kosove', 'fushe kosova', 'fushe kosoves'],
    'Gjakovë': ['gjakove', 'gjakova', 'gjakoves'],
    'Gjilan': ['gjilan', 'gjilani', 'gjilanit'],
    'Graçanicë': ['gracanice', 'gracanica', 'gracanices'],
    'Hani i Elezit': ['hani i elezit', 'han te elezit', 'hanin e elezit', 'hanit te elezit'],
    'Istog': ['istog', 'istogu', 'istogut'],
    'Junik': ['junik', 'juniku', 'junikut'],
    'Kamenicë': ['kamenice', 'kamenica', 'kamenices', 'dardane', 'dardanes'],
    'Kaçanik': ['kacanik', 'kacaniku', 'kacanikut'],
    'Klinë': ['kline', 'klina', 'klines'],
    'Kllokot': ['kllokot', 'kllokoti', 'kllokotit'],
    'Leposaviq': ['leposaviq', 'leposaviqi', 'leposaviqit'],
    'Lipjan': ['lipjan', 'lipjani', 'lipjanit'],
    'Malishevë': ['malisheve', 'malisheva', 'malisheves'],
    'Mamushë': ['mamushe', 'mamusha', 'mamushes'],
    'Mitrovicë e Jugut': ['mitrovice e jugut', 'mitrovica e jugut', 'mitrovices se jugut', 'mitrovicen e jugut', 'mitrovice jugore', 'mitrovica jugore'],
    'Mitrovicë e Veriut': ['mitrovice e veriut', 'mitrovica e veriut', 'mitrovices se veriut', 'mitrovicen e veriut', 'mitrovice veriore', 'mitrovica veriore', 'mitrovices veriore'],
    'Novobërdë': ['novoberde', 'novoberda', 'novoberdes', 'novo berde', 'artane', 'artanes'],
    'Obiliq': ['obiliq', 'obiliqi', 'obiliqit', 'kastriot', 'kastriotit'],
    'Partesh': ['partesh', 'parteshi', 'parteshit'],
    'Pejë': ['peje', 'peja', 'pejes'],
    'Podujevë': ['podujeve', 'podujeva', 'podujeves', 'besiane', 'besianes'],
    'Prishtinë': ['prishtine', 'prishtina', 'prishtines'],
    'Prizren': ['prizren', 'prizreni', 'prizrenit'],
    'Rahovec': ['rahovec', 'rahoveci', 'rahovecit'],
    'Ranillug': ['ranillug', 'ranillugu', 'ranillugut'],
    'Shtime': ['shtime', 'shtimja', 'shtimes'],
    'Shtërpcë': ['shterpce', 'shterpca', 'shterpces'],
    'Skenderaj': ['skenderaj', 'skenderaji', 'skenderajt'],
    'Suharekë': ['suhareke', 'suhareka', 'suharekes', 'therande', 'therandes'],
    'Viti': ['viti', 'vitise', 'vitia'],
    'Vushtrri': ['vushtrri', 'vushtrria', 'vushtrrise', 'vushtrrine'],
    'Zubin Potok': ['zubin potok', 'zubin potoku', 'zubin potokut'],
    'Zveçan': ['zvecan', 'zvecani', 'zvecanit'],
}

# These are also names of people/ordinary words: require a location preposition.
AMBIGUOUS = {'viti', 'vitia', 'kastriot', 'kastriotit', 'besiane', 'artane', 'dardane'}
PATTERNS = {}
for municipality, aliases in MUNICIPALITIES.items():
    patterns = []
    for alias in aliases:
        prefix = r'\b(?:ne|nga|prej|komuna e|komunes se|qyteti i|qytetin e)\s+' if alias in AMBIGUOUS else r'\b'
        suffix = r'\b(?!\s+(?:\d{4}\b|i\b|e\b))' if alias == 'viti' else r'\b'
        patterns.append(re.compile(prefix + re.escape(alias) + suffix))
    PATTERNS[municipality] = patterns


def detect_municipalities(title, content=''):
    # Do not classify a whole article using a passing mention deep in its body.
    title = normalize(title)
    lead = normalize(' '.join(str(content or '').splitlines()[:2])[:700])
    text = title + '\n' + lead
    return [name for name, patterns in PATTERNS.items() if any(p.search(text) for p in patterns)]


def enrich_municipalities(article):
    article['komunat'] = detect_municipalities(article.get('titulli'), article.get('permbajtja'))
    return article
