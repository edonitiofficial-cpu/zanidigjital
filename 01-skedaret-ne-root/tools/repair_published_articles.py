"""Repair this repository's existing stories, keeping URLs and publication dates."""
import argparse
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
from urllib.request import Request,urlopen

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from news_utils import load_news_file,write_json_atomic
from article_content import clean_article_text,has_imported_footer,extract_article
from article_renderer import render_article
from news_policy import publication_date


def repair(root,limit=50,refetch=False,apply=False,fetch=None):
    root=Path(root)
    if not 1<=limit<=100:raise ValueError('Kufiri duhet të jetë 1–100.')
    items=load_news_file(root/'lajmet.json')
    candidates=[]
    for article in items:
        source=article.get('link_origjinal','')
        scoped=(urlsplit(source).hostname or '') in ('telegrafi.com','www.telegrafi.com')
        if article.get('slug') and not article.get('duplicate_of') and (has_imported_footer(article.get('permbajtja','')) or (refetch and scoped and not article.get('content_blocks'))):
            candidates.append(article)
    candidates.sort(key=lambda n:publication_date(n).timestamp() if publication_date(n) else 0,reverse=True)
    changed=[];failures=0
    for article in candidates[:limit]:
        original=article.get('permbajtja','');clean=clean_article_text(original)
        blocks=article.get('content_blocks',[])
        source=article.get('link_origjinal','')
        if refetch and (urlsplit(source).hostname or '') in ('telegrafi.com','www.telegrafi.com'):
            try:
                if fetch:page=fetch(source)
                else:
                    with urlopen(Request(source,headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as response:
                        raw=response.read(8*1024*1024+1)
                        if len(raw)>8*1024*1024:raise ValueError('Burimi është më i madh se kufiri i lejuar.')
                        page=raw.decode('utf-8',errors='replace')
                extracted=extract_article(page,source)
                if extracted and len(extracted['text'])>=max(100,int(len(clean)*.55)):
                    clean,blocks=extracted['text'],extracted['blocks']
                else:failures+=1
            except Exception:
                failures+=1
        if len(clean)<80:continue
        if clean!=original or blocks!=article.get('content_blocks',[]):
            article['permbajtja']=clean
            if blocks:article['content_blocks']=blocks
            changed.append(article)
    if apply and changed:
        previous=os.getcwd()
        try:
            os.chdir(root)
            for article in changed:render_article(article,items)
            write_json_atomic(root/'lajmet.json',items,indent=2)
        finally:os.chdir(previous)
    print(f'{"U rregulluan" if apply else "Për rregullim"}: {len(changed)}; u kontrolluan: {min(limit,len(candidates))}; burime që nuk u pranuan: {failures}. URL-të dhe datat ruhen.')
    return len(changed)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit',type=int,default=50)
    parser.add_argument('--refetch',action='store_true')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    repair(root,limit=args.limit,refetch=args.refetch,apply=args.apply)
