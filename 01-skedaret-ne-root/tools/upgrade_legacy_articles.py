"""Apply reading styles/local fonts to older articles without replacing their text."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import tempfile
import sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
known={n.get('slug') for n in json.loads((root/'lajmet.json').read_text(encoding='utf-8'))}


def upgrade(path):
    if path.parent.name in known:return 0
    original=path.read_text(encoding='utf-8');text=original
    text=re.sub(r'<link\b[^>]*href="https://fonts\.(?:googleapis|gstatic)\.com/[^>]*>','',text)
    text=re.sub(r"\s*@import\s+url\([^)]*fonts.googleapis.com/[^)]*\)\s*;",'',text)
    from tools.repair_font_styles import repair_style
    text=repair_style(text)
    additions=''
    if '/fonts.css' not in text:additions+='<link rel="stylesheet" href="/fonts.css">\n'
    if 'permbajtja' in text:
        text=re.sub(r'<body class="(?!article-page)', '<body class="article-page ',text,count=1)
        text=re.sub(r'<article class="(?!article-body)', '<article class="article-body ',text,count=1)
        if '/article.css' not in text:additions+='<link rel="stylesheet" href="/article.css">\n'
        if '/article.js' not in text:additions+='<script src="/article.js" defer></script>\n'
    text=text.replace('</head>',additions+'</head>',1)
    if text==original:return 0
    fd,temporary=tempfile.mkstemp(dir=path.parent,prefix='.news-',suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(text)
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
    return 1


with ThreadPoolExecutor(max_workers=8) as pool:
    count=sum(pool.map(upgrade,(root/'lajme').glob('*/index.html')))
print(f'Legacy articles upgraded without replacing their text: {count}')
