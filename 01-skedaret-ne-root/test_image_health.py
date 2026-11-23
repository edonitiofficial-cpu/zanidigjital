"""No live services: verify decoded images, retries, caching and bounded work."""
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from PIL import Image
from image_health import audit_photos, inspect_photo, probe
from tools.repair_font_styles import repair_style


class ImageHealthTests(unittest.TestCase):
    def test_checks_real_image_bytes_not_http_success(self):
        image = BytesIO()
        Image.new('RGB', (320, 180)).save(image, format='PNG')
        self.assertEqual(probe('https://example.test/photo', lambda *a, **k: BytesIO(image.getvalue()))[0], 'ok')
        self.assertEqual(probe('https://example.test/html', lambda *a, **k: BytesIO(b'<html>not an image</html>'))[0], 'broken')

    def test_blocked_source_is_not_reported_as_a_missing_photo(self):
        def fail(code):
            def request(*args, **kwargs): raise HTTPError('https://example.test', code, 'ignored', {}, None)
            return request
        self.assertEqual(probe('https://example.test', fail(403))[0], 'unverified')
        self.assertEqual(probe('https://example.test', fail(404))[0], 'broken')

    def test_usable_original_is_a_fallback_not_broken(self):
        item = {'url':'https://example.test/photo.jpg'}
        result = inspect_photo(item, lambda url: ('ok','decoded') if url == item['url'] else ('broken','not_found'))
        self.assertEqual(result['status'], 'fallback')

    def test_rotates_through_pending_photos_and_reuses_cached_result(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'report.json'
            articles = [{'slug':str(i),'titulli':str(i),'imazhi':f'https://example.test/{i}.jpg'} for i in range(8)]
            calls=[]
            def check(url):calls.append(url);return 'ok','decoded'
            now=datetime(2026,11,16,12,tzinfo=timezone.utc)
            first=audit_photos(articles,path,limit=5,check=check,now=now)
            self.assertEqual((first['checked_this_run'],first['pending']),(5,3))
            second=audit_photos(articles,path,limit=5,check=check,now=now)
            self.assertEqual((second['checked_this_run'],second['pending']),(3,0))
            self.assertEqual(len(calls),8)
            self.assertEqual(len(json.loads(path.read_text())['images']),8)

    def test_inline_image_is_checked_and_original_article_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            article={'slug':'one','titulli':'One','content_blocks':[{'type':'image','url':'https://example.test/inline.jpg'}]}
            before=json.dumps(article)
            audit_photos([article],Path(folder)/'report.json',check=lambda u:('broken','not_found'))
            self.assertEqual(json.dumps(article),before)
            self.assertEqual(json.loads((Path(folder)/'report.json').read_text())['images'][0]['role'],'inline')

    def test_repairs_only_the_exact_font_remainder(self):
        source="<style>500;700;800;900&display=swap');\nbody{color:red}</style><p>Original news text.</p>"
        fixed=repair_style(source)
        self.assertEqual(fixed,'<style>\nbody{color:red}</style><p>Original news text.</p>')
        self.assertEqual(repair_style(fixed),fixed)
        self.assertEqual(repair_style('<style>body{font-weight:500}</style>'),'<style>body{font-weight:500}</style>')
