import json
from pathlib import Path
import tempfile
import unittest
from article_content import extract_article,clean_article_text
from article_renderer import render_article
from tools.repair_published_articles import repair

BODY='Ky është teksti i lajmit për një ngjarje me rëndësi publike. Qytetarët mund t’i lexojnë të gjitha hollësitë në këtë paragraf, ndërsa burimi dhe fotografitë mbeten të shënuara saktë.'
FOOTER='\nNga\nTelegrafi\n5 sekonda më parë\nTop Lajme\nJobs\nReal Estate'


class ContentTests(unittest.TestCase):
    def test_telegrafi_lazy_photo_uses_real_runner_source(self):
        source=f'<div class="body-description"><p>{BODY}</p><p><img src="data:image/svg+xml,placeholder" data-runner-src="https://telegrafi.com/media-library/image.jpg?id=55&amp;width=980" width="2000" height="1532"></p></div>'
        result=extract_article(source,'https://telegrafi.com/example/')
        self.assertEqual(result['blocks'][1]['type'],'image')
        self.assertEqual(result['blocks'][1]['url'],'https://telegrafi.com/media-library/image.jpg?id=55&width=980')

    def test_scoped_body_excludes_footer_and_preserves_media_order(self):
        source=f'''<html><body><div class="body-description"><p>{BODY}</p>
          <figure><img src="/media-library/inside.jpg?id=55&amp;width=980" alt="Pamje nga vendi"><figcaption>Fotografia e ngjarjes</figcaption></figure>
          <p>Steve Jobs përmendet në këtë paragraf të vlefshëm për teknologjinë dhe nuk duhet të hiqet.</p>
          <blockquote class="twitter-tweet">Tekst i postimit që nuk duhet të shfaqet si paragraf<a href="https://x.com/example/status/123">Data e postimit</a></blockquote>
          <script>alert(1)</script></div><div><p>Nga</p><p>Telegrafi</p><p>5 sekonda më parë</p><p>Jobs</p><p>Real Estate</p></div></body></html>'''
        result=extract_article(source,'https://telegrafi.com/example/')
        self.assertNotIn('5 sekonda',result['text'])
        self.assertNotIn('Real Estate',result['text'])
        self.assertIn('Steve Jobs',result['text'])
        self.assertEqual([b['type'] for b in result['blocks']],['paragraph','image','paragraph','embed'])
        self.assertEqual(result['blocks'][1]['url'],'https://telegrafi.com/media-library/inside.jpg?id=55&width=980')
        self.assertEqual(result['blocks'][1]['caption'],'Fotografia e ngjarjes')

    def test_legacy_footer_is_removed_without_dropping_legitimate_names(self):
        body=BODY+'\nArtikulli për Steve Jobs dhe tregun Real Estate është pjesë e tekstit.'
        self.assertEqual(clean_article_text(body+FOOTER),body)
        self.assertEqual(clean_article_text(body+FOOTER.replace('5 sekonda','1 minutë')),body)
        self.assertEqual(clean_article_text(body),body)
        self.assertEqual(clean_article_text(BODY+'\nJobs\nReal Estate'),BODY+'\nJobs\nReal Estate')

    def test_renderer_uses_typed_images_and_safe_embed_links(self):
        article=dict(slug='safe',titulli='Lajmi',permbajtja=BODY+FOOTER,kategoria='Lajme',content_blocks=[
            dict(type='paragraph',text=BODY),dict(type='image',url='https://example.com/inside.jpg',alt='Foto',caption='<script>bad()</script>'),
            dict(type='embed',url='https://x.com/example/status/123',label='Shiko postimin origjinal'),
            dict(type='embed',url='javascript:alert(1)'),dict(type='image',url='javascript:alert(1)')])
        import os
        previous=os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder);render_article(article,[])
                output=Path('lajme/safe/index.html').read_text(encoding='utf-8')
                self.assertIn('article-inline-media',output)
                self.assertIn('<figcaption>&lt;script&gt;',output)
                self.assertNotIn('<script>bad()',output)
                self.assertNotIn('javascript:',output)
                self.assertNotIn('5 sekonda',output)
                self.assertIn('https://x.com/example/status/123',output)
            finally:os.chdir(previous)

    def test_repair_preserves_slugs_dates_and_other_articles(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            dirty=dict(slug='existing',titulli='Lajmi aktual',permbajtja=BODY+FOOTER,published_at='2026-11-16T12:00:00+01:00',link_origjinal='https://telegrafi.com/existing/')
            clean=dict(slug='other',titulli='Lajmi tjetër',permbajtja=BODY,published_at='2026-11-15T12:00:00+01:00')
            archive=root/'lajmet.json';archive.write_text(json.dumps([dirty,clean]),encoding='utf-8')
            original=archive.read_bytes()
            self.assertEqual(repair(root,apply=False),1)
            self.assertEqual(archive.read_bytes(),original)
            self.assertEqual(repair(root,apply=True),1)
            repaired=json.loads(archive.read_text(encoding='utf-8'))
            self.assertEqual(repaired[0]['slug'],dirty['slug'])
            self.assertEqual(repaired[0]['published_at'],dirty['published_at'])
            self.assertEqual(repaired[0]['permbajtja'],BODY)
            self.assertEqual(repaired[1],clean)
