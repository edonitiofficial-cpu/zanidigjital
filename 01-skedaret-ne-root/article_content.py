"""Extract scoped editorial blocks; never copy source navigation or executable embeds."""
from html import unescape
import re
from urllib.parse import urljoin,urlsplit
from lxml import html
from news_utils import safe_url


def normalized(value):
    return ' '.join(str(value or '').replace('\u200b','').split())


def clean_article_text(value):
    lines=[line.strip() for line in str(value or '').splitlines() if line.strip()]
    nav={'top lajme','jobs','real estate','të fundit','te fundit'}
    relative=lambda line:bool(re.fullmatch(r'\d+\s+(?:sekond(?:a|[eë])?|minut(?:a|[eë])?|or[eë]|dit[eë]|jav[eë]|muaj|vit(?:e|esh)?)\s+m[eë]\s+par[eë]',line,re.I))
    for index in range(max(0,len(lines)-18),len(lines)):
        suffix=[normalized(line).casefold() for line in lines[index:]]
        marker='top lajme' in suffix or any(relative(normalized(line)) for line in lines[max(0,index-3):index])
        if marker and suffix[0] in nav and sum(line in nav for line in suffix)>=2:
            start=index
            while start>0 and (normalized(lines[start-1]).casefold() in {'nga','telegrafi'} or relative(normalized(lines[start-1]))):
                start-=1
            lines=lines[:start]
            break
    return '\n'.join(lines)


def has_imported_footer(value):
    normalized_lines='\n'.join(line.strip() for line in str(value or '').splitlines() if line.strip())
    return clean_article_text(value)!=normalized_lines


def extract_article(markup,url):
    """Return None when a verified editorial container cannot be identified."""
    doc=html.fromstring(markup,base_url=url)
    host=urlsplit(url).hostname or ''
    if host in ('telegrafi.com','www.telegrafi.com'):
        roots=doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," body-description ")]')
    else:
        roots=doc.xpath('//*[@itemprop="articleBody"] | //*[contains(concat(" ",normalize-space(@class)," ")," entry-content ")]')
    if not roots:return None
    root=html.fromstring(html.tostring(roots[0],encoding='unicode'))
    for item in root.xpath('.//script | .//style | .//nav | .//aside | .//form | .//noscript'):
        item.drop_tree()
    blocks=[];seen_images=set()

    def text_block(text,kind='paragraph'):
        text=normalized(text)
        if text and not re.match(r'^(?:lexo (?:edhe|më shumë)|advertisement|reklam[eë])\b',text,re.I):
            blocks.append(dict(type=kind,text=text))

    def image_block(image,caption=''):
        for field in ('data-runner-src','data-rm-src','data-src','data-original','data-lazy-src','src'):
            source=unescape(image.get(field,'')).strip()
            if source and not source.startswith(('data:','javascript:')):break
        else:return
        source=safe_url(urljoin(url,source))
        if not source or source in seen_images or urlsplit(source).path.lower().endswith('.svg'):return
        try:
            if (image.get('width') and int(image.get('width'))<80) or (image.get('height') and int(image.get('height'))<50):return
        except ValueError:pass
        seen_images.add(source)
        blocks.append(dict(type='image',url=source,alt=normalized(image.get('alt','')),caption=normalized(caption)))

    def walk(element):
        tag=element.tag.lower() if isinstance(element.tag,str) else ''
        classes=set(element.get('class','').split())
        if classes & {'related','related-posts','advertisement','ad-container','all-related-sections'}:return
        if tag=='blockquote' and ('twitter-tweet' in classes or 'instagram-media' in classes):
            links=[safe_url(urljoin(url,a.get('href',''))) for a in element.xpath('.//a[@href]')]
            link=next((link for link in links if (urlsplit(link).hostname or '').removeprefix('www.') in ('x.com','twitter.com','instagram.com')),None)
            if link:blocks.append(dict(type='embed',url=link,label='Shiko postimin origjinal'))
            return
        if tag=='iframe':
            link=safe_url(urljoin(url,element.get('src','')))
            if (urlsplit(link).hostname or '').removeprefix('www.') in ('youtube.com','youtu.be','facebook.com'):
                blocks.append(dict(type='embed',url=link,label='Shiko videon te burimi'))
            return
        if tag=='figure':
            caption=' '.join(e.text_content() for e in element.xpath('.//figcaption'))
            for image in element.xpath('.//img'):image_block(image,caption)
            if not element.xpath('.//img'):
                for child in element:walk(child)
            return
        if tag=='img':image_block(element);return
        if tag in ('p','h2','h3','li'):
            text_block(element.text_content(),'heading' if tag in ('h2','h3') else 'paragraph')
            for image in element.xpath('.//img'):image_block(image)
            return
        for child in element:walk(child)

    walk(root)
    text=clean_article_text('\n'.join(b['text'] for b in blocks if b['type'] in ('paragraph','heading')))
    if len(text)<80:return None
    remaining=len(text.splitlines());cleaned=[]
    for block in blocks:
        if block['type'] in ('paragraph','heading'):
            if remaining<=0:break
            remaining-=1
        cleaned.append(block)
    return dict(text=text,blocks=cleaned)
