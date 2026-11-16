from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from featured_image import cache_lead_photo,cached_photo
from photo_utils import photo_variant


class FeaturedImageTests(unittest.TestCase):
    def test_verified_source_resize_preserves_image_identity(self):
        self.assertEqual(photo_variant('https://telegrafi.com/media-library/image.jpg?id=123&width=980',480),'https://telegrafi.com/media-library/image.jpg?id=123&width=480')
        self.assertTrue(photo_variant('https://telegrafi.com.evil.example/media-library/image.jpg?id=123&width=980',480).startswith('https://wsrv.nl/'))
        self.assertEqual(photo_variant('javascript:bad',480),'/zanidigjitalfavicon.png')
    def test_valid_variants_are_local_reusable_and_tied_to_original(self):
        article={'imazhi':'https://example.com/image.jpg'}
        fetch=Mock(return_value=b'RIFF0000WEBPdata')
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(cache_lead_photo(article,folder,fetch))
            self.assertEqual(fetch.call_count,2)
            self.assertIsNotNone(cached_photo(article))
            self.assertTrue((Path(folder)/article['hero_image']['large'].lstrip('/')).exists())
            self.assertTrue(cache_lead_photo(article,folder,fetch))
            self.assertEqual(fetch.call_count,2)
            article['imazhi']='https://example.com/changed.jpg'
            self.assertIsNone(cached_photo(article))

    def test_invalid_remote_content_does_not_become_a_photo(self):
        article={'imazhi':'https://example.com/image.jpg'}
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(cache_lead_photo(article,folder,lambda url:b'<html>error</html>'))
            self.assertNotIn('hero_image',article)
            self.assertEqual(list((Path(folder)/'news-images').iterdir()),[])

    def test_unsafe_url_is_never_fetched(self):
        fetch=Mock()
        self.assertFalse(cache_lead_photo({'imazhi':'javascript:alert(1)'},fetch=fetch))
        fetch.assert_not_called()
