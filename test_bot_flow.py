"""Exercise orchestration without real feeds, model calls, Git or Facebook."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class BotFlowTests(unittest.TestCase):
    def load_offline_bot(self, feeds):
        modules={'feedparser':SimpleNamespace(parse=lambda data:SimpleNamespace(entries=feeds[int(data)])), 'trafilatura':SimpleNamespace(), 'groq':SimpleNamespace(Groq=lambda **kwargs:SimpleNamespace())}
        with patch.dict(sys.modules,modules),patch.dict(os.environ,{'GROQ_API_KEY':'offline-test'}):
            spec=importlib.util.spec_from_file_location('offline_bot',Path(__file__).with_name('bot.py'))
            bot=importlib.util.module_from_spec(spec);spec.loader.exec_module(bot)
        return bot

    def test_duplicate_is_merged_and_reported_without_model_call(self):
        from news_time import news_now
        now=news_now()
        original={'titulli':'Aksident në Pejë, dy persona të lënduar','slug':'primary','link_origjinal':'https://one.example/news','published_at':now.isoformat(),'koha':now.strftime('%d/%m/%Y %H:%M'),'kategoria':'Lajme','permbajtja':'Tekst i artikullit.'}
        bot=self.load_offline_bot([[{'title':'Dy persona të lënduar në aksident në Pejë','link':'https://two.example/news'}],[],[],[]])
        cwd=os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                with patch.object(bot,'load_news',return_value=[original]),patch.object(bot.urllib.request,'urlopen',side_effect=[io.BytesIO(str(i).encode()) for i in range(4)]),patch.object(bot,'gjenero_kategori_dhe_hashtags') as model,patch.object(bot,'save_news'),patch.object(bot,'krijo_rss'),patch.object(bot,'krijo_sitemap'),patch.object(bot,'gjenero_artikullin_html'),patch.object(bot,'gjenero_lajmet_manuale',return_value=[]),patch.object(bot,'facebook_queue_path',return_value='queue.json'):
                    bot.main()
                model.assert_not_called()
                report=json.loads(Path('bot-status.json').read_text(encoding='utf-8'))
                self.assertEqual(report['counts']['merged'],1)
                self.assertEqual(report['events'][0]['target_slug'],'primary')
                self.assertEqual(len(original['burime']),2)
                self.assertEqual(json.loads(Path('queue.json').read_text()),[])
            finally:os.chdir(cwd)

    def test_fatal_error_leaves_a_safe_report(self):
        bot=self.load_offline_bot([[],[],[],[]]);cwd=os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                with patch.object(bot,'load_news',side_effect=ValueError('PRIVATE_VALUE')):
                    with self.assertRaises(ValueError):bot.main()
                text=Path('bot-status.json').read_text(encoding='utf-8')
                self.assertNotIn('PRIVATE_VALUE',text)
                self.assertEqual(json.loads(text)['status'],'error')
            finally:os.chdir(cwd)

    def test_all_sources_are_read_and_only_five_articles_are_prepared(self):
        source = Path(__file__).with_name('bot.py')
        feeds = [[{'title': f'Source {letter} story {i}', 'link': f'https://{letter}.example/{i}',
                   'media_content': [{'url': 'https://images.example/photo.jpg'}]} for i in range(3)] for letter in 'abcd']
        stub_modules = {
            'feedparser': SimpleNamespace(parse=lambda payload: SimpleNamespace(entries=feeds[int(payload)])),
            'trafilatura': SimpleNamespace(),
            'groq': SimpleNamespace(Groq=lambda **kwargs: SimpleNamespace()),
        }
        with patch.dict(sys.modules, stub_modules), patch.dict(os.environ, {'GROQ_API_KEY': 'offline-test'}):
            spec = importlib.util.spec_from_file_location('offline_bot', source)
            bot = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bot)
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                with patch.object(bot, 'load_news', return_value=[]), \
                     patch.object(bot.urllib.request, 'urlopen', side_effect=[io.BytesIO(str(i).encode()) for i in range(4)]) as requests, \
                     patch.object(bot, 'fetch_full_text', return_value='A useful factual paragraph. ' * 20), \
                     patch.object(bot, 'gjenero_kategori_dhe_hashtags', return_value={'kategoria': 'Lajme'}), \
                     patch.object(bot, 'kontrollo_ballinen_e_burimit', return_value=True), \
                     patch.object(bot, 'is_duplicate_news', return_value=False), \
                     patch.object(bot.time, 'sleep'), \
                     patch.object(bot.time, 'time', return_value=0), \
                     patch.object(bot, 'save_news') as save, \
                     patch.object(bot, 'krijo_rss'), patch.object(bot, 'krijo_sitemap'), \
                     patch.object(bot, 'gjenero_artikullin_html') as render, \
                     patch.object(bot, 'gjenero_lajmet_manuale', return_value=[]), \
                     patch.object(bot, 'facebook_queue_path', return_value='queue.json'), \
                     patch.object(bot.os, 'system', side_effect=AssertionError('No shell publication allowed')):
                    bot.main()
                self.assertEqual(requests.call_count, 4)
                prepared = save.call_args.args[0]
                self.assertEqual(len(prepared), 5)
                self.assertEqual(render.call_count, 5)
                self.assertEqual([item['link_origjinal'] for item in prepared[:4]],
                                 [f'https://{letter}.example/0' for letter in 'abcd'])
                self.assertTrue(all('published_at' in item for item in prepared))
                report = json.loads(Path('bot-status.json').read_text(encoding='utf-8'))
                self.assertEqual(report['status'],'ok')
                self.assertEqual(report['counts']['prepared'],5)
                self.assertEqual(report['counts']['unprocessed'],7)
            finally:
                os.chdir(original)


if __name__ == '__main__':
    unittest.main()
