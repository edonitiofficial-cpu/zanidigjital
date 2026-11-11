import json
import os
from pathlib import Path
import tempfile
import unittest
from article_renderer import render_article
from news_utils import interleave_feeds, load_news_file, news_metadata, safe_url, slugify, write_json_atomic


class NewsSafetyTests(unittest.TestCase):
    def test_corrupt_archive_stops_instead_of_erasing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'lajmet.json'
            path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(json.JSONDecodeError):
                load_news_file(path)
            self.assertEqual(path.read_text(), '{broken')

    def test_atomic_save_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'lajmet.json'
            news = [{'slug': 'lajm', 'titulli': 'Lajm', 'permbajtja': 'Tekst i gjatë'}, {'slug': '', 'titulli': ''}]
            write_json_atomic(path, news)
            self.assertEqual(load_news_file(path), news)
            self.assertEqual(news_metadata(news), [{'titulli': 'Lajm', 'slug': 'lajm'}])
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_sources_interleave_and_do_not_starve(self):
        sources = [[{'title': f'{letter}{i}'} for i in range(3)] for letter in 'abcd']
        first = list(interleave_feeds(sources))[:5]
        self.assertEqual([n['title'] for n in first], ['a0', 'b0', 'c0', 'd0', 'a1'])
        self.assertEqual(list(interleave_feeds([[], [{'title': 'only'}]])), [{'title': 'only'}])

    def test_slug_and_url_safety(self):
        self.assertEqual(slugify('Çështje -- e re!'), 'ceshtje-e-re')
        for value in ['javascript:alert(1)', 'data:text/html,test', 'https://[bad']:
            self.assertEqual(safe_url(value), '')
        self.assertEqual(safe_url('https://example.com/lajmi'), 'https://example.com/lajmi')

    def test_generated_article_escapes_untrusted_text(self):
        article = {'slug': 'test', 'titulli': '<script>alert(1)</script>',
                   'permbajtja': '<img src=x onerror=alert(1)>\nTekst & citim',
                   'imazhi': 'javascript:alert(1)', 'kategoria': 'Lajme', 'koha': '10/11/2026 13:00',
                   'published_at': '2026-11-10T13:00:00+01:00', 'link_origjinal': 'https://example.com/lajmi'}
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                render_article(article, [])
                output = Path('lajme/test/index.html').read_text(encoding='utf-8')
                self.assertNotIn('<script>alert(1)</script>', output)
                self.assertNotIn('<img src=x onerror=alert(1)>', output)
                self.assertNotIn('src="javascript:', output)
                self.assertIn('&lt;img src=x', output)
                self.assertIn('article-source', output)
                self.assertIn('datePublished', output)
            finally:
                os.chdir(original)


if __name__ == '__main__':
    unittest.main()
