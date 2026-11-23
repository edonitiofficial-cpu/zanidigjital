"""Keep real news links in initial HTML, including when JavaScript is unavailable."""
import html
from pathlib import Path
import re
import json
from urllib.parse import quote
from news_utils import safe_url
from featured_image import cached_photo
from news_policy import publication_date
from photo_utils import photo_variant


def render_homepage(news, path='index.html'):
    path = Path(path)
    items = sorted([n for n in news if n.get('slug') and n.get('titulli') and not n.get('duplicate_of')],key=lambda n:publication_date(n).timestamp() if publication_date(n) else 0,reverse=True)
    ranked = sorted([n for n in items if isinstance(n.get('featured_rank'), int)], key=lambda n:n['featured_rank'])
    featured = (ranked if ranked else items)[:5]
    selected = {n['slug'] for n in featured}
    latest = [n for n in items if n['slug'] not in selected][:16]
    esc = lambda v: html.escape(str(v or ''), quote=True)
    def card(n, position=None):
        main = position == 0
        photo = safe_url(n.get('imazhi')) or '/zanidigjitalfavicon.png'
        optimized = photo_variant(photo,1000 if main else 480)
        widths = [480,1000] if main else [240,480]
        srcset = ', '.join(esc(photo_variant(photo,width)) + f' {width}w' for width in widths)
        cached = cached_photo(n)
        if cached:
            optimized = cached['large' if main else 'small']
            srcset = esc(cached['small'])+' 480w'+(', '+esc(cached['large'])+' 1000w' if main else '')
        sizes = '(max-width: 767px) calc(100vw - 32px), 550px' if main else '(max-width: 767px) 112px, 280px'
        image = f'<img src="{esc(optimized)}" srcset="{srcset}" sizes="{sizes}" data-original="{esc(photo)}" onerror="this.removeAttribute(\'srcset\');imageFallback(this)" alt="" width="{800 if main else 400}" height="{500 if main else 250}" {"fetchpriority=high" if main else "loading=lazy"} decoding="async" class="w-full {"h-full" if main else "h-40"} object-cover">'
        href = '/lajme/' + quote(n['slug'],safe='-') + '/'
        version=esc(json.dumps([n.get('slug') or '',n.get('titulli') or '',n.get('kategoria') or '',safe_url(n.get('imazhi')),n.get('koha') or '',int(n.get('source_count') or 0),cached,position],ensure_ascii=False,separators=(',',':')))
        bg,color={'Sport':('bg-green-600','text-green-600'),'Politikë':('bg-red-600','text-red-600'),'Teknologji':('bg-blue-600','text-blue-600'),'Tech':('bg-blue-600','text-blue-600'),'Ekonomi':('bg-yellow-600','text-yellow-600')}.get(n.get('kategoria'),('bg-black','text-black'))
        if position is not None:
            cls = 'featured-main md:col-span-2 md:row-span-2' if main else 'featured-small h-48 md:h-auto'
            source_count = f'<p class="text-xs mt-2 text-gray-200 source-count">Nga {int(n["source_count"])} burime</p>' if int(n.get('source_count') or 0)>1 else ''
            time = f'<p class="text-gray-200 text-xs mt-3">{esc(n.get("koha"))}</p>' if main else ''
            return f'<a href="{href}" data-news-version="{version}" class="{cls} group relative rounded-xl overflow-hidden shadow-sm bg-white">{image}<div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent"></div><div class="absolute bottom-0 {"p-6" if main else "p-4"}"><span class="{bg} text-white text-[10px] font-bold px-2 py-1 rounded uppercase">{esc(n.get("kategoria"))}</span><h3 class="text-white {"text-2xl md:text-3xl" if main else "text-base"} font-bold mt-2">{esc(n["titulli"])}</h3>{source_count}{time}</div></a>'
        return f'<a href="{href}" data-news-version="{version}" class="news-card bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition flex flex-col">{image}<div class="p-4 flex-grow flex flex-col"><span class="{color} font-bold text-xs uppercase mb-2">{esc(n.get("kategoria"))}</span><h3 class="font-bold text-lg leading-snug mb-3">{esc(n["titulli"])}</h3><p class="text-gray-500 text-xs mt-auto">{esc(n.get("koha"))}</p></div></a>'
    content = path.read_text(encoding='utf-8')
    for name, cards, pattern in [
        ('featured', ''.join(card(n,i) for i,n in enumerate(featured)), r'(<div id="bento-grid"[^>]*>).*?(\n                </div>\n            </section>)'),
        ('latest', ''.join(card(n) for n in latest), r'(<div id="te-fundit-grid"[^>]*>).*?(\n                </div>\n                <div class="mt-10)')]:
        start, end = f'<!-- {name}:start -->', f'<!-- {name}:end -->'
        if start in content:
            content = re.sub(re.escape(start) + r'.*?' + re.escape(end), lambda _: start + cards + end, content, flags=re.S)
        else:
            content, count = re.subn(pattern, lambda m:m[1] + start + cards + end + m[2], content, count=1, flags=re.S)
            if count != 1: raise ValueError(f'Homepage slot missing: {name}')
    if content != path.read_text(encoding='utf-8'):
        path.write_text(content, encoding='utf-8')


if __name__ == '__main__':
    from news_utils import load_news_file
    render_homepage(load_news_file('lajmet.json'))
