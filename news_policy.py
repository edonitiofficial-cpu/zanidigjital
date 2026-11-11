"""Explainable event matching and automated homepage selection."""
from datetime import datetime, timezone
from difflib import SequenceMatcher
from functools import lru_cache
import re
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit
from municipalities import normalize, detect_municipalities
from news_time import NEWS_TIMEZONE, news_now

STOP = set('ne te e i a nje nga per me dhe se qe ka jane eshte u si pas tek sot lajmi fundit video foto'.split())


def canonical_url(url):
    try:
        p = urlsplit(url)
        query = [(k,v) for k,v in parse_qsl(p.query) if not k.startswith('utm_') and k not in ('fbclid','gclid')]
        return urlunsplit((p.scheme.lower(), p.netloc.lower().removeprefix('www.'), p.path.rstrip('/'), urlencode(query), ''))
    except (TypeError, ValueError):
        return ''


def publication_date(article):
    try:
        if article.get('published_at'):
            parsed = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=NEWS_TIMEZONE)
        return datetime.strptime(article['koha'], '%d/%m/%Y %H:%M').replace(tzinfo=NEWS_TIMEZONE)
    except (TypeError, ValueError, KeyError):
        return None


@lru_cache(maxsize=16000)
def tokens(text):
    def stem(word):
        if word.startswith('pages') or word in ('paga','pagat','pagave','page'):
            return 'pagese'
        return word[:7]
    return frozenset(stem(w) for w in re.findall(r'[a-z0-9]+', normalize(text)) if len(w) > 2 and w not in STOP)


def same_event(left, right):
    a, b = normalize(left.get('titulli')), normalize(right.get('titulli'))
    if not a or not b:
        return False
    ta, tb = tokens(a), tokens(b)
    common = ta & tb
    lead_a = next((p.strip() for p in str(left.get('permbajtja', '')).splitlines() if p.strip()), '')[:450]
    lead_b = next((p.strip() for p in str(right.get('permbajtja', '')).splitlines() if p.strip()), '')[:450]
    la, lb = tokens(lead_a), tokens(lead_b)
    strong_lead = (len(la & lb) >= 15 and len(la & lb)/max(len(la | lb),1) >= .85
                   and SequenceMatcher(None, normalize(lead_a), normalize(lead_b)).ratio() >= .90
                   and set(re.findall(r'\b\d+\b',lead_a)) == set(re.findall(r'\b\d+\b',lead_b)))
    if a != b and len(common) < 2:
        return False
    # New numbers, a different named person, location or negation may be an update.
    if set(re.findall(r'\b\d+\b', a)) != set(re.findall(r'\b\d+\b', b)):
        return False
    if bool(re.search(r'\b(?:nuk|s\u2019|s\')', a)) != bool(re.search(r'\b(?:nuk|s\u2019|s\')', b)):
        return False
    names = lambda text: {normalize(n) for n in re.findall(r'\b[A-ZÇË][a-zçë]+\s+[A-ZÇË][a-zçë]+\b', text or '')}
    title_names_a, title_names_b = names(left.get('titulli')), names(right.get('titulli'))
    if title_names_a and title_names_b and not title_names_a.intersection(title_names_b):
        return False
    na, nb = names(str(left.get('titulli',''))+'\n'+lead_a), names(str(right.get('titulli',''))+'\n'+lead_b)
    if na and nb and not na.intersection(nb):
        return False
    places_a = set(detect_municipalities(a))
    places_b = set(detect_municipalities(b))
    if places_a and places_b and not places_a.intersection(places_b):
        return False
    if a == b:
        return True
    topic_overlap = len(common)/max(len(ta | tb),1)
    # Interview segments often share a boilerplate lead but cover different topics.
    interview = re.search(r'\b(?:intervis\w*|rrefen|flet|kujton|zbulon)\b',a+' '+b)
    sports = left.get('kategoria') == 'Sport' or right.get('kategoria') == 'Sport'
    if (interview or sports) and topic_overlap < .65:
        strong_lead = False
        allow_body_match = False
    else:
        allow_body_match = True
    if strong_lead:
        return True
    if len(common) >= 4 and len(common) / max(len(ta | tb), 1) >= .72:
        return True
    if len(common) >= 3 and SequenceMatcher(None, a, b).ratio() >= .88:
        return True
    # A copied lead is stronger evidence than a few generic headline words.
    ca, cb = tokens(left.get('permbajtja', '')[:900]), tokens(right.get('permbajtja', '')[:900])
    return allow_body_match and len(ca & cb) >= 25 and len(ca & cb) / max(len(ca | cb), 1) >= .8 and len(common) >= 2


def find_duplicate(candidate, articles, now=None):
    now = now or news_now()
    reference = publication_date(candidate) or now
    url = canonical_url(candidate.get('link_origjinal', ''))
    for article in articles:
        sources = [article.get('link_origjinal', '')] + [s.get('url', '') for s in article.get('burime', [])]
        if url and any(canonical_url(source) == url for source in sources):
            return article, 'known_url'
        date = publication_date(article)
        if date and abs((reference-date).total_seconds()) <= 12*3600 and same_event(candidate, article):
            return article, 'same_event'
    return None, None


def merge_source(article, candidate):
    sources = article.setdefault('burime', [])
    original = article.get('link_origjinal')
    if original and not sources:
        sources.append({'url': original, 'titulli': article.get('titulli', '')})
    incoming = [{'url': candidate.get('link_origjinal'), 'titulli': candidate.get('titulli', '')}] + list(candidate.get('burime', []))
    added = False
    for item in incoming:
        url = item.get('url')
        if url and canonical_url(url) not in {canonical_url(s['url']) for s in sources}:
            sources.append({'url': url, 'titulli': item.get('titulli', '')})
            added = True
    if added:
        article['last_seen_at'] = news_now().isoformat()
        return True
    return False


def source_host(article):
    return urlsplit(article.get('link_origjinal', '')).netloc.removeprefix('www.') or 'manual'


def rank_article(article, now):
    date = publication_date({'published_at': article.get('source_published_at')}) or publication_date(article)
    age = max(0, (now-date).total_seconds()/3600) if date else 9999
    freshness = round(max(0, 40 - age * 40/24), 2)
    score, reasons = freshness, [f'Freskia: {freshness:g}/40']
    if article.get('eshte_balline'):
        score += 12; reasons.append('Në ballinën e burimit: +12')
    hosts = {urlsplit(s.get('url', '')).netloc.removeprefix('www.') for s in article.get('burime', [])}
    hosts.discard('')
    coverage = min(24, max(0, len(hosts)-1)*8)
    if coverage:
        score += coverage; reasons.append(f'Burime të ndryshme: +{coverage}')
    public_interest = re.search(r'\b(?:termet|evaku\w*|viktim\w*|aksident\w*|uji\w*|rryme\w*|energj\w*|shendet\w*|shkoll\w*|buxhet\w*|zgjedhj\w*|ligj\w*|pension\w*|paga\w*)\b', normalize(article.get('titulli')))
    if public_interest:
        score += 10; reasons.append('Temë me interes publik: +10')
    return score, reasons, age


def select_featured(articles, now=None):
    now = now or news_now()
    for article in articles:
        article.pop('featured_rank', None)
        article.pop('selection_reasons', None)
    ranked = [(n, *rank_article(n, now)) for n in articles[:150] if n.get('slug') and n.get('titulli') and not n.get('duplicate_of')]
    recent = [row for row in ranked if row[3] <= 24]
    pool = sorted(recent if len(recent) >= 5 else ranked, key=lambda row: (row[1], -row[3]), reverse=True)
    chosen, hosts, categories = [], {}, {}
    for strict in (True, False):
        for article, score, reasons, age in pool:
            if article in chosen:
                continue
            host, category = source_host(article), article.get('kategoria')
            if strict and (hosts.get(host, 0) >= 2 or categories.get(category, 0) >= 2):
                continue
            if any(same_event(article, existing) for existing in chosen):
                continue
            article['featured_rank'] = len(chosen)+1
            article['selection_reasons'] = reasons + ['Larmi burimesh dhe temash' if strict else 'Plotësim me kandidatët e mbetur']
            chosen.append(article)
            hosts[host] = hosts.get(host, 0)+1; categories[category] = categories.get(category, 0)+1
            if len(chosen) == 5:
                return chosen
    return chosen


def group_archive(articles):
    """Keep every URL, marking repeats for lists and aggregating their sources."""
    from collections import Counter, defaultdict
    index, by_url = defaultdict(list), {}
    groups = 0
    ordered = sorted((n for n in articles if n.get('slug') and n.get('titulli')), key=lambda n: publication_date(n).timestamp() if publication_date(n) else 0, reverse=True)
    for article in ordered:
        if article.get('duplicate_of'):
            continue
        words = tokens(article.get('titulli', ''))
        counts = Counter(id(n) for word in words for n in index[word])
        candidates = {id(n): n for word in words for n in index[word] if counts[id(n)] >= 2}
        url = canonical_url(article.get('link_origjinal', ''))
        if url and url in by_url:
            candidates[id(by_url[url])] = by_url[url]
        primary, reason = find_duplicate(article, list(candidates.values()))
        if primary:
            article['duplicate_of'] = primary['slug']
            merge_source(primary, article)
            primary['source_count'] = len({urlsplit(s['url']).netloc.removeprefix('www.') for s in primary.get('burime', [])})
            groups += 1
        else:
            for word in words: index[word].append(article)
            if url: by_url[url] = article
    by_slug = {n.get('slug'): n for n in articles}
    for article in articles:
        target = article.get('duplicate_of')
        visited = {article.get('slug')}
        while target and target not in visited and by_slug.get(target, {}).get('duplicate_of'):
            visited.add(target)
            target = by_slug[target]['duplicate_of']
        if target and target not in visited:
            article['duplicate_of'] = target
            primary = by_slug.get(target)
            if primary:
                merge_source(primary, article)
                primary['source_count'] = len({urlsplit(s['url']).netloc.removeprefix('www.') for s in primary.get('burime', [])})
    return groups
